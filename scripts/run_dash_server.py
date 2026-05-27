#!/usr/bin/env python3
"""
Run interactive Dash server for live dashboard.
Access at: http://localhost:8050

Companion to ``scripts/build_dashboard.py`` (static HTML emitter).
This server reads the same ``results/*.json`` files plus their sibling
``.equity.csv`` files, so a single backtest run feeds both views.

Usage
-----
    python scripts/run_dash_server.py
    python scripts/run_dash_server.py --port 8080 --debug
    python scripts/run_dash_server.py --host 0.0.0.0     # expose on LAN

Security note
-------------
By default the server binds to ``127.0.0.1`` (loopback only). Pass
``--host 0.0.0.0`` only on a trusted network -- the dashboard has no
authentication and exposes raw KPI data + equity curves.

Troubleshooting
---------------
Port already in use ("Address already in use" / OSError 48 or 98)?
    # Find what's holding it
    lsof -i :8050                       # Linux / macOS
    netstat -ano | findstr :8050        # Windows

    # Or just pick a different one
    python scripts/run_dash_server.py --port 8051
"""
from __future__ import annotations

import argparse
import errno
import json
import socket
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _list_results(results_dir: Path) -> list[dict]:
    """Available backtest result JSONs as Dropdown options, newest first."""
    files = sorted(
        results_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [{"label": f.stem, "value": f.stem} for f in files]


def _load_result(results_dir: Path, stem: str) -> tuple[dict, pd.DataFrame | None]:
    """Load the result JSON and its sibling .equity.csv (if present)."""
    json_path = results_dir / f"{stem}.json"
    payload = json.loads(json_path.read_text())

    equity_csv = json_path.with_suffix(".equity.csv")
    equity_df: pd.DataFrame | None = None
    if equity_csv.exists():
        equity_df = pd.read_csv(equity_csv, parse_dates=["timestamp"], index_col="timestamp")
    return payload, equity_df


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app(results_dir: str) -> Dash:
    results_path = Path(results_dir)
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1(
            "🎯 NQ Backtest Dashboard - Live",
            style={"textAlign": "center", "color": "#667eea"},
        ),

        dcc.Dropdown(
            id="strategy-dropdown",
            options=_list_results(results_path),
            value=None,
            placeholder="Select a strategy...",
            style={"width": "50%", "margin": "20px auto"},
        ),

        dcc.Graph(id="equity-curve"),
        dcc.Graph(id="metrics-chart"),

        html.Div(
            id="metrics-summary",
            style={
                "margin": "20px",
                "padding": "20px",
                "backgroundColor": "#f5f5f5",
                "borderRadius": "10px",
            },
        ),
    ])

    @app.callback(
        [Output("equity-curve", "figure"),
         Output("metrics-chart", "figure"),
         Output("metrics-summary", "children")],
        Input("strategy-dropdown", "value"),
    )
    def update_dashboard(selected: str | None):
        if not selected:
            return go.Figure(), go.Figure(), "Select a strategy to view results"

        try:
            payload, equity_df = _load_result(results_path, selected)
        except FileNotFoundError as exc:
            return go.Figure(), go.Figure(), f"Result not found: {exc}"

        # KPIs are under data["kpis"] in this engine's convention. Fall back to
        # data["results"] (Michael Automates' format) or top-level so foreign
        # result files still render.
        kpis = payload.get("kpis") or payload.get("results") or payload

        # ---- Equity curve ----
        equity_fig = go.Figure()
        if equity_df is not None and "value" in equity_df.columns:
            equity_fig.add_trace(go.Scatter(
                x=equity_df.index, y=equity_df["value"], mode="lines",
                line=dict(color="#3fb950", width=2), name="Equity",
            ))
            equity_fig.update_layout(
                title=f"Equity Curve: {selected}",
                template="plotly_dark", height=400,
                margin=dict(l=20, r=20, t=50, b=20),
            )
        else:
            equity_fig.update_layout(
                title=(f"No equity curve for {selected} "
                       "(re-run scripts/run_backtest.py to generate .equity.csv)"),
                template="plotly_dark", height=400,
            )

        # ---- Metrics bar chart ----
        # `total_return_pct` is already a percentage. `max_drawdown` from
        # vectorbt is a *fraction* (e.g. -0.0002 for -0.02%) so multiply by 100
        # for display unless someone passed a foreign result with `_pct` keys.
        net_profit_pct = float(kpis.get("total_return_pct", kpis.get("net_profit_pct", 0)))
        raw_dd = float(kpis.get("max_drawdown", kpis.get("max_drawdown_pct", 0)))
        max_dd_pct = raw_dd * (100.0 if abs(raw_dd) <= 1.0 else 1.0)
        win_rate_pct = float(kpis.get("percent_profitable", kpis.get("win_rate", 0))) * 100.0
        sharpe = float(kpis.get("sharpe_ratio", 0))

        metrics_fig = go.Figure(data=[go.Bar(
            x=["Net Profit %", "Max DD %", "Win Rate %", "Sharpe x50"],
            y=[net_profit_pct, -abs(max_dd_pct), win_rate_pct, sharpe * 50],
            marker_color=["#3fb950", "#f85149", "#58a6ff", "#d2a8ff"],
        )])
        metrics_fig.update_layout(
            template="plotly_dark", height=380,
            margin=dict(l=20, r=20, t=20, b=20),
        )

        # ---- Summary card ----
        pf = float(kpis.get("profit_factor", 0))
        total_trades = int(kpis.get("total_trades", 0))
        summary_html = html.Div([
            html.H3("Key Metrics"),
            html.P(f"Net Profit: {net_profit_pct:.2f}%"),
            html.P(f"Max Drawdown: {max_dd_pct:.2f}%"),
            html.P(f"Win Rate: {win_rate_pct:.1f}%"),
            html.P(f"Profit Factor: {pf:.2f}"),
            html.P(f"Total Trades: {total_trades}"),
        ])

        return equity_fig, metrics_fig, summary_html

    return app


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Run interactive Dash backtest dashboard.")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Bind address. Default loopback only; pass 0.0.0.0 to expose on LAN.",
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app = create_app(args.results_dir)

    print(f"🚀 Starting Dash server at http://{args.host}:{args.port}")
    print(f"📊 Results directory: {args.results_dir}")
    print("Press CTRL+C to stop")

    # Dash >= 2.16 deprecated `app.run_server` in favor of `app.run`, and
    # Dash 3.x removed it. Prefer the new method, fall back if absent.
    runner = getattr(app, "run", None) or app.run_server

    # Pre-flight: confirm the bind address is free, so we can print a
    # friendlier message than Werkzeug's terse "Address already in use".
    # There is a TOCTOU race between this check and the actual bind below,
    # but in practice it covers the 99% case (something else holding the port).
    _preflight_check_port(args.host, args.port)

    runner(host=args.host, port=args.port, debug=args.debug)


def _preflight_check_port(host: str, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE or getattr(exc, "winerror", None) == 10048:
            print(f"\nERROR: port {port} is already in use on {host}.", file=sys.stderr)
            print("\nFind what's holding the port:", file=sys.stderr)
            print(f"  lsof -i :{port}                       # Linux / macOS", file=sys.stderr)
            print(f"  netstat -ano | findstr :{port}        # Windows", file=sys.stderr)
            print("\nOr just pick a different one:", file=sys.stderr)
            print(f"  python {sys.argv[0]} --port {port + 1}", file=sys.stderr)
            sys.exit(1)
        raise
    finally:
        sock.close()


if __name__ == "__main__":
    main()

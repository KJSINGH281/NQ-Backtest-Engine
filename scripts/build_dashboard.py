"""
Build a single-file static HTML dashboard from a backtest result.

Reads the most recent `results/*.json` (and its sibling `*.equity.csv`)
and writes `dashboard/index.html`. The output is fully self-contained
except for plotly.js, which is loaded from CDN -- so it opens directly
in any browser without a server.

Usage
-----
    python scripts/build_dashboard.py
    python scripts/build_dashboard.py --result results/auto_2026.json
    python scripts/build_dashboard.py --output dashboard/run42.html
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import click
import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html

ROOT = Path(__file__).resolve().parent.parent

PAGE_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0e1117; color: #fafafa; margin: 0; padding: 24px 32px; line-height: 1.4;
}
h1 { font-weight: 300; margin: 0 0 4px; font-size: 28px; letter-spacing: -0.5px; }
h2 { font-weight: 400; margin: 0 0 24px; color: #8a8e98; font-size: 16px; }
section { margin-bottom: 32px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.kpi { background: #161b22; border: 1px solid #2a2e39; border-radius: 6px; padding: 14px 16px; }
.kpi .label { font-size: 12px; color: #8a8e98; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi .value { font-size: 22px; margin-top: 6px; font-variant-numeric: tabular-nums; }
.kpi.pos .value { color: #3fb950; }
.kpi.neg .value { color: #f85149; }
.meta { font-size: 13px; color: #8a8e98; }
.meta code { background: #161b22; padding: 2px 6px; border-radius: 3px; }
"""

# KPIs that are "positive when above zero" (used for green/red coloring).
POS_KPIS = {"total_net_profit", "gross_profit", "profit_factor",
            "percent_profitable", "avg_trade", "sharpe_ratio", "total_return_pct"}
NEG_KPIS = {"gross_loss", "max_drawdown"}


def find_latest_result(results_dir: Path) -> Path:
    candidates = sorted(results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise click.ClickException(f"No backtest results found in {results_dir}")
    return candidates[0]


def render_kpis(kpis: dict) -> str:
    cards = []
    for key, val in kpis.items():
        css_class = "kpi"
        if key in POS_KPIS and isinstance(val, (int, float)) and val > 0:
            css_class += " pos"
        elif key in NEG_KPIS and isinstance(val, (int, float)) and val < 0:
            css_class += " neg"

        if isinstance(val, float):
            display = f"{val:,.4f}".rstrip("0").rstrip(".") if abs(val) < 1 else f"{val:,.2f}"
        else:
            display = str(val)

        cards.append(
            f'<div class="{css_class}">'
            f'<div class="label">{escape(key.replace("_", " "))}</div>'
            f'<div class="value">{escape(display)}</div>'
            f'</div>'
        )
    return f'<div class="kpi-grid">{"".join(cards)}</div>'


def render_equity_chart(equity: pd.Series) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity.index, y=equity.values, mode="lines",
        line=dict(color="#3fb950", width=2), name="Equity",
    ))
    fig.update_layout(
        title=dict(text="Equity Curve", x=0, font=dict(size=18, color="#fafafa")),
        template="plotly_dark", height=380,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        showlegend=False,
    )
    return fig


def render_drawdown_chart(equity: pd.Series) -> go.Figure:
    peak = equity.cummax()
    dd_pct = (equity / peak - 1.0) * 100.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd_pct.index, y=dd_pct.values, mode="lines",
        line=dict(color="#f85149", width=1), fill="tozeroy",
        fillcolor="rgba(248, 81, 73, 0.25)", name="Drawdown",
    ))
    fig.update_layout(
        title=dict(text="Drawdown (%)", x=0, font=dict(size=18, color="#fafafa")),
        template="plotly_dark", height=260,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        showlegend=False,
    )
    return fig


@click.command()
@click.option("--result", "result_path", type=click.Path(exists=True, dir_okay=False),
              help="Specific result JSON file. Defaults to newest in --results-dir.")
@click.option("--results-dir", default=str(ROOT / "results"),
              type=click.Path(file_okay=False),
              show_default=True)
@click.option("--output", "output_path",
              default=str(ROOT / "dashboard" / "index.html"),
              type=click.Path(dir_okay=False), show_default=True)
def main(result_path: str | None, results_dir: str, output_path: str) -> None:
    json_path = Path(result_path) if result_path else find_latest_result(Path(results_dir))
    payload = json.loads(json_path.read_text())
    strategy = payload.get("strategy", {})
    kpis = payload.get("kpis", {})

    # Sibling equity-curve CSV produced by run_backtest.py
    equity_csv = json_path.with_suffix(".equity.csv")
    plots_html_parts: list[str] = []
    if equity_csv.exists():
        equity_df = pd.read_csv(equity_csv, parse_dates=["timestamp"], index_col="timestamp")
        equity = equity_df["value"]
        plots_html_parts.append(to_html(render_equity_chart(equity),
                                        full_html=False, include_plotlyjs="cdn"))
        plots_html_parts.append(to_html(render_drawdown_chart(equity),
                                        full_html=False, include_plotlyjs=False))
    else:
        plots_html_parts.append(
            f'<p class="meta">No equity curve found at <code>{escape(str(equity_csv))}</code>. '
            f'Re-run <code>scripts/run_backtest.py</code> to generate it.</p>'
        )

    title = f"NQ Backtest Dashboard - {strategy.get('name', '?')}"
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<h1>{escape(title)}</h1>
<h2>Params: <code>{escape(json.dumps(strategy.get('params', {})))}</code> &middot; Source: <code>{escape(json_path.name)}</code></h2>
<section>{render_kpis(kpis)}</section>
<section>{''.join(plots_html_parts)}</section>
</body></html>
"""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    click.echo(f"Wrote {out}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()

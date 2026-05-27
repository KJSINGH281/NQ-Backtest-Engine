"""
CLI: run a single backtest against a CSV and dump KPIs as JSON.

Example
-------
    python scripts/run_backtest.py \
        --strategy orb_retrace \
        --data data/sample_nq_1m.csv \
        --output results/orb.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data import load_nq_1m              # noqa: E402
from src.engine import run_backtest          # noqa: E402
from src.strategies import STRATEGY_REGISTRY # noqa: E402


@click.command()
@click.option("--strategy", required=True, type=click.Choice(sorted(STRATEGY_REGISTRY.keys())))
@click.option("--data", "data_path", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--output", "output_path", required=True, type=click.Path(dir_okay=False))
@click.option("--init-cash", default=50_000.0, type=float, show_default=True)
@click.option("--rth-only/--all-hours", default=True, show_default=True)
@click.option("--params", default="{}", help="JSON dict of strategy params, e.g. '{\"fast\":9,\"slow\":21}'")
def main(strategy: str, data_path: str, output_path: str, init_cash: float, rth_only: bool, params: str) -> None:
    df = load_nq_1m(data_path, rth_only=rth_only)
    strat = STRATEGY_REGISTRY[strategy](**json.loads(params))
    sig = strat.generate_signals(df)

    result = run_backtest(
        price=df["close"],
        entries=sig.entries,
        exits=sig.exits,
        init_cash=init_cash,
    )

    out = {
        "strategy": strat.describe(),
        "kpis": result.kpis,
        "config": result.config,
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(out, indent=2, default=str))
    click.echo(json.dumps(result.kpis, indent=2))


if __name__ == "__main__":
    main()

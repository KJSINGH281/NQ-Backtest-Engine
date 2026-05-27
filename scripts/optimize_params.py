"""
CLI: grid-search a strategy's parameters and dump the ranked results.

Example
-------
    python scripts/optimize_params.py \
        --strategy ema_cross \
        --param-grid '{"fast":[9,12,15],"slow":[21,26,30]}' \
        --data data/sample_nq_1m.csv \
        --output results/opt.json
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import click

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data import load_nq_1m              # noqa: E402
from src.engine import run_backtest          # noqa: E402
from src.strategies import STRATEGY_REGISTRY # noqa: E402


def _grid(grid: dict[str, list]) -> list[dict]:
    keys = list(grid.keys())
    return [dict(zip(keys, vals)) for vals in itertools.product(*[grid[k] for k in keys])]


@click.command()
@click.option("--strategy", required=True, type=click.Choice(sorted(STRATEGY_REGISTRY.keys())))
@click.option("--param-grid", required=True, help="JSON dict of lists.")
@click.option("--data", "data_path", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--output", "output_path", required=True, type=click.Path(dir_okay=False))
@click.option("--rank-by", default="profit_factor", show_default=True)
def main(strategy: str, param_grid: str, data_path: str, output_path: str, rank_by: str) -> None:
    df = load_nq_1m(data_path, rth_only=True)
    grid = json.loads(param_grid)
    cls = STRATEGY_REGISTRY[strategy]

    runs: list[dict] = []
    for combo in _grid(grid):
        try:
            strat = cls(**combo)
            sig = strat.generate_signals(df)
            result = run_backtest(price=df["close"], entries=sig.entries, exits=sig.exits)
            runs.append({"params": combo, "kpis": result.kpis})
        except Exception as e:  # don't let one bad combo kill the sweep
            runs.append({"params": combo, "error": str(e)})

    runs.sort(key=lambda r: r.get("kpis", {}).get(rank_by, float("-inf")), reverse=True)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(
        {"strategy": strategy, "rank_by": rank_by, "runs": runs}, indent=2, default=str,
    ))
    click.echo(f"Top result by {rank_by}: {runs[0] if runs else 'none'}")


if __name__ == "__main__":
    main()

"""Smoke test for run_backtest -> KPIs round-trip on the sample CSV."""
from __future__ import annotations

from pathlib import Path

import pytest

vbt = pytest.importorskip("vectorbt")

from src.data import load_nq_1m
from src.engine import run_backtest
from src.strategies import EmaCross

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_nq_1m.csv"


def test_run_backtest_produces_kpis():
    df = load_nq_1m(SAMPLE)
    sig = EmaCross(fast=2, slow=4).generate_signals(df)

    result = run_backtest(price=df["close"], entries=sig.entries, exits=sig.exits)

    assert result.kpis["total_trades"] >= 0
    for key in ("total_net_profit", "profit_factor", "max_drawdown", "sharpe_ratio"):
        assert key in result.kpis
    assert result.config["n_bars"] == len(df)

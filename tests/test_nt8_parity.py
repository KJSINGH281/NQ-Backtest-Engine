"""Tests for the NT8 parity check."""
from __future__ import annotations

from src.validation import check_nt8_parity


VBT_KPIS = {
    "total_net_profit": 1000.0,
    "gross_profit": 1500.0,
    "gross_loss": -500.0,
    "profit_factor": 3.0,
    "total_trades": 50,
    "percent_profitable": 0.55,
    "max_drawdown": 0.12,
}


def test_parity_passes_within_tolerance():
    nt8 = {**VBT_KPIS, "total_net_profit": 1015.0}  # ~1.5% diff
    report = check_nt8_parity(VBT_KPIS, nt8, tolerance_pct=2.0)
    assert report.is_parity is True
    assert report.failed_kpis == []


def test_parity_fails_when_kpi_diverges():
    nt8 = {**VBT_KPIS, "total_net_profit": 1100.0}  # 10% diff
    report = check_nt8_parity(VBT_KPIS, nt8, tolerance_pct=2.0)
    assert report.is_parity is False
    assert "total_net_profit" in report.failed_kpis


def test_parity_ignores_unknown_keys():
    report = check_nt8_parity({"foo": 1.0}, {"foo": 2.0})
    # No COMPARED_KPIS in input -> nothing failed, parity True by default
    assert report.is_parity is True
    assert report.diffs == {}

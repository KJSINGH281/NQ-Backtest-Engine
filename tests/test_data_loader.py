"""Tests for the NQ 1-minute CSV loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.data import load_nq_1m, filter_rth

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_nq_1m.csv"


def test_load_nq_1m_returns_tz_aware_ohlcv():
    df = load_nq_1m(SAMPLE)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.tz is not None
    assert df.index.is_monotonic_increasing
    assert len(df) > 0


def test_load_nq_1m_rth_filter_keeps_session_bars():
    df = load_nq_1m(SAMPLE, rth_only=True)
    et = df.index.tz_convert("America/New_York")
    assert (et.hour >= 9).all()
    assert ((et.hour < 16) | ((et.hour == 16) & (et.minute == 0) & False)).all()


def test_filter_rth_requires_tz():
    df = load_nq_1m(SAMPLE)
    naive = df.tz_localize(None) if df.index.tz else df
    with pytest.raises(ValueError):
        filter_rth(naive)

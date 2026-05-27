"""Tests for the NQ fee/slippage model."""
from __future__ import annotations

import pytest

from src.engine.fees import (
    DEFAULT_NQ_FEES,
    NQFeeModel,
    NQ_POINT_VALUE,
    NQ_TICK_SIZE,
    NQ_TICK_VALUE,
)


def test_contract_constants():
    assert NQ_TICK_SIZE == 0.25
    assert NQ_TICK_VALUE == 5.0
    assert NQ_POINT_VALUE == 20.0
    # 4 ticks per point, $5/tick -> $20/point
    assert NQ_TICK_SIZE * NQ_POINT_VALUE / NQ_TICK_VALUE == pytest.approx(1.0)


def test_default_fees_round_turn_total():
    f = DEFAULT_NQ_FEES
    # commission + exchange = 2.50 + 0.52
    assert f.total_commission_per_rt == pytest.approx(3.02)
    # 1 tick/side * 2 sides * $5/tick = $10 slippage round-turn
    assert f.slippage_dollars_per_rt == pytest.approx(10.0)
    assert f.total_cost_per_rt == pytest.approx(13.02)


def test_vbt_fees_fraction_scales_with_price():
    f = NQFeeModel(commission_per_rt=2.0, exchange_fees_per_rt=0.0, slippage_ticks_per_side=0)
    # 1 contract @ price 18000 -> notional $360,000 per side; fee/side = $1
    frac = f.vbt_fees_fraction(price=18000.0, contracts=1)
    assert frac == pytest.approx(1.0 / 360_000.0)


def test_vbt_fees_fraction_rejects_zero_price():
    with pytest.raises(ValueError):
        DEFAULT_NQ_FEES.vbt_fees_fraction(price=0.0)

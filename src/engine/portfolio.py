"""Helpers that translate our fee model into kwargs for vbt.Portfolio.from_signals()."""
from __future__ import annotations

from typing import Any

from .fees import DEFAULT_NQ_FEES, NQFeeModel, NQ_POINT_VALUE, NQ_TICK_SIZE


def build_portfolio_kwargs(
    init_cash: float = 50_000.0,
    contracts_per_trade: int = 1,
    fee_model: NQFeeModel | None = None,
    reference_price: float | None = None,
) -> dict[str, Any]:
    """
    Build a kwargs dict for vbt.Portfolio.from_signals() that bakes in
    realistic NQ commissions + slippage.

    Notes
    -----
    * vectorbt models position size in *units of the asset*. For NQ, "1 unit"
      is 1 contract worth $20 per index point. We approximate this by using
      `size=contracts_per_trade` and letting commission/slippage be expressed
      as fractions of notional.
    """
    fees = fee_model or DEFAULT_NQ_FEES
    px = reference_price if reference_price and reference_price > 0 else 18_000.0

    fees_frac = fees.vbt_fees_fraction(price=px, contracts=contracts_per_trade)
    slip_frac = (fees.slippage_ticks_per_side * NQ_TICK_SIZE) / px

    return {
        "init_cash": init_cash,
        "size": contracts_per_trade,
        "size_type": "amount",
        "fees": fees_frac,
        "slippage": slip_frac,
        "freq": "1min",
    }


def contracts_for_risk(
    account_equity: float,
    risk_pct: float,
    stop_distance_points: float,
) -> int:
    """
    Fixed-fractional position sizing for NQ.

    contracts = floor( (equity * risk_pct) / (stop_distance_points * point_value) )
    """
    if stop_distance_points <= 0:
        return 0
    risk_dollars = account_equity * risk_pct
    per_contract_risk = stop_distance_points * NQ_POINT_VALUE
    return max(int(risk_dollars // per_contract_risk), 0)

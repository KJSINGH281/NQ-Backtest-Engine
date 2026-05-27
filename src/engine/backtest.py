"""
Core backtest runner. Thin wrapper around vbt.Portfolio.from_signals() that:
  * applies the NQ fee/slippage model
  * enforces the 1-min frequency
  * returns a dict of standardized KPIs alongside the raw Portfolio object
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .fees import DEFAULT_NQ_FEES, NQFeeModel
from .portfolio import build_portfolio_kwargs


@dataclass
class BacktestResult:
    portfolio: Any                 # vbt.Portfolio  (kept loose to avoid import at module load)
    kpis: dict[str, float]
    config: dict[str, Any]


def run_backtest(
    price: pd.Series,
    entries: pd.Series,
    exits: pd.Series,
    *,
    init_cash: float = 50_000.0,
    contracts_per_trade: int = 1,
    fee_model: NQFeeModel | None = None,
) -> BacktestResult:
    """
    Run a long/short NQ backtest with realistic fees & slippage.

    Parameters
    ----------
    price   : 1-min close prices (pd.Series, tz-aware index recommended).
    entries : boolean Series, True on entry-long bars.
    exits   : boolean Series, True on exit bars.

    Returns
    -------
    BacktestResult with .portfolio, .kpis, .config
    """
    import vectorbt as vbt  # imported lazily so unit tests can mock

    fees = fee_model or DEFAULT_NQ_FEES
    ref_price = float(price.dropna().iloc[-1]) if len(price.dropna()) else 18_000.0

    kwargs = build_portfolio_kwargs(
        init_cash=init_cash,
        contracts_per_trade=contracts_per_trade,
        fee_model=fees,
        reference_price=ref_price,
    )

    pf = vbt.Portfolio.from_signals(price, entries=entries, exits=exits, **kwargs)

    # Lazy-import to avoid a circular dep with validation/kpis.py
    from src.validation.kpis import compute_kpis
    kpis = compute_kpis(pf)

    return BacktestResult(
        portfolio=pf,
        kpis=kpis,
        config={
            "init_cash": init_cash,
            "contracts_per_trade": contracts_per_trade,
            "fee_model": fees.__dict__,
            "reference_price": ref_price,
            "n_bars": int(len(price)),
        },
    )

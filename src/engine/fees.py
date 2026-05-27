"""
NQ futures cost model.

Contract spec (E-mini Nasdaq-100 / NQ):
    - Tick size:  0.25 index points
    - Tick value: $5.00
    - Point value: $20.00 ( = 4 ticks x $5 )

Default cost assumptions (override per broker):
    - Commission: $2.50 per round-turn (~$1.25 per side) - typical retail futures rate
    - Exchange/NFA fees: $0.52 per round-turn
    - Slippage: 1 tick per side on market orders during RTH (more on news/illiquid bars)
"""
from __future__ import annotations

from dataclasses import dataclass

NQ_TICK_SIZE: float = 0.25
NQ_TICK_VALUE: float = 5.0
NQ_POINT_VALUE: float = 20.0  # $ per 1.00 index point


@dataclass(frozen=True)
class NQFeeModel:
    """Fee/slippage model for NQ futures, expressed in dollars and ticks."""

    commission_per_rt: float = 2.50      # broker commission per round-turn
    exchange_fees_per_rt: float = 0.52   # CME + NFA fees per round-turn
    slippage_ticks_per_side: float = 1.0 # market-order slippage in ticks, per side

    # ---------- dollar-space accessors (used in reporting) ----------
    @property
    def total_commission_per_rt(self) -> float:
        return self.commission_per_rt + self.exchange_fees_per_rt

    @property
    def slippage_dollars_per_rt(self) -> float:
        return self.slippage_ticks_per_side * 2 * NQ_TICK_VALUE

    @property
    def total_cost_per_rt(self) -> float:
        return self.total_commission_per_rt + self.slippage_dollars_per_rt

    # ---------- VectorBT-space accessors ----------
    def vbt_fees_fraction(self, price: float, contracts: int = 1) -> float:
        """
        Convert per-round-turn $ commission into the *fraction-of-notional*
        that vectorbt expects via Portfolio(fees=...).

        notional_per_side = price * NQ_POINT_VALUE * contracts
        fee_per_side      = total_commission_per_rt / 2
        """
        if price <= 0:
            raise ValueError("price must be positive")
        notional_per_side = price * NQ_POINT_VALUE * max(contracts, 1)
        fee_per_side = self.total_commission_per_rt / 2.0
        return fee_per_side / notional_per_side

    def vbt_slippage_fraction(self) -> float:
        """
        Slippage as a fraction of price (vectorbt's `slippage` arg).

        slippage_price = slippage_ticks_per_side * NQ_TICK_SIZE
        fraction       = slippage_price / price  -> approximated at typical NQ price
        For NQ around 18000 a 1-tick slip = 0.25 / 18000 ~= 1.4e-5 (negligible vs commission).
        Callers may pass a reference price; we use a conservative midpoint default.
        """
        # Use a conservative reference price; recomputed dynamically inside run_backtest
        ref_price = 18000.0
        return (self.slippage_ticks_per_side * NQ_TICK_SIZE) / ref_price


DEFAULT_NQ_FEES = NQFeeModel()

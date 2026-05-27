"""EMA(fast) / EMA(slow) crossover - reference strategy used by tests and the optimize_params script."""
from __future__ import annotations

import pandas as pd

from .template import BaseStrategy, StrategySignals


class EmaCross(BaseStrategy):
    name = "ema_cross"

    def __init__(self, fast: int = 9, slow: int = 21) -> None:
        if fast >= slow:
            raise ValueError("fast must be strictly less than slow")
        super().__init__(fast=fast, slow=slow)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        fast = df["close"].ewm(span=self.params["fast"], adjust=False).mean()
        slow = df["close"].ewm(span=self.params["slow"], adjust=False).mean()

        # No look-ahead: shift the cross signal by 1 bar so we trade on next open.
        cross_up = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        cross_dn = (fast < slow) & (fast.shift(1) >= slow.shift(1))

        entries = cross_up.shift(1, fill_value=False).astype(bool)
        exits = cross_dn.shift(1, fill_value=False).astype(bool)

        return StrategySignals(
            entries=entries,
            exits=exits,
            metadata={"fast_ema_last": float(fast.iloc[-1]) if len(fast) else None},
        )

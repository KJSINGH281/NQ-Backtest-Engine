"""
Opening Range Breakout with retrace entry.

Logic
-----
1. Compute the [09:30, 09:30 + opening_minutes) high/low per session ("opening range").
2. After the opening range closes, look for a breakout above OR.high.
3. Enter long on the *first retrace* back into OR.high (touch from above).
4. Exit at session close (16:00 ET) or on a stop below OR.low.
"""
from __future__ import annotations

from datetime import time

import numpy as np
import pandas as pd

from .template import BaseStrategy, StrategySignals


class OrbRetrace(BaseStrategy):
    name = "orb_retrace"

    def __init__(self, opening_minutes: int = 15) -> None:
        super().__init__(opening_minutes=opening_minutes)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        if df.index.tz is None:
            raise ValueError("OrbRetrace requires a tz-aware index")

        et = df.index.tz_convert("America/New_York")
        session = pd.Series(et.normalize(), index=df.index)
        minutes_into_day = et.hour * 60 + et.minute - (9 * 60 + 30)

        opening_mask = (minutes_into_day >= 0) & (minutes_into_day < self.params["opening_minutes"])

        # Per-session opening range (forward-filled after the opening window closes).
        or_high = (
            df["high"].where(opening_mask).groupby(session).cummax().groupby(session).ffill()
        )
        or_low = (
            df["low"].where(opening_mask).groupby(session).cummin().groupby(session).ffill()
        )

        breakout_armed = (df["high"] > or_high) & (~opening_mask)
        # Retrace entry: price touches OR high from above on a later bar.
        prior_breakout = breakout_armed.groupby(session).cummax().astype(bool)
        retrace_touch = (df["low"] <= or_high) & prior_breakout & (~opening_mask)

        # No look-ahead: trade next bar.
        entries = retrace_touch.shift(1, fill_value=False).astype(bool)

        # Exits: end-of-session OR stop below OR.low.
        end_of_session = pd.Series(
            (et.time >= time(15, 59)),
            index=df.index,
        )
        stop_hit = (df["low"] < or_low) & prior_breakout
        exits = (end_of_session | stop_hit).shift(1, fill_value=False).astype(bool)

        return StrategySignals(
            entries=entries.fillna(False).astype(bool),
            exits=exits.fillna(False).astype(bool),
            metadata={
                "opening_minutes": self.params["opening_minutes"],
                "or_high_last": float(or_high.iloc[-1]) if len(or_high) and not np.isnan(or_high.iloc[-1]) else None,
                "or_low_last": float(or_low.iloc[-1]) if len(or_low) and not np.isnan(or_low.iloc[-1]) else None,
            },
        )

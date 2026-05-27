"""Regular Trading Hours filter for NQ (09:30-16:00 ET, Mon-Fri)."""
from __future__ import annotations

from datetime import time

import pandas as pd

RTH_OPEN: time = time(9, 30)
RTH_CLOSE: time = time(16, 0)


def filter_rth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only bars whose timestamp falls within 09:30-16:00 America/New_York,
    Monday-Friday. Index must be tz-aware.
    """
    if df.index.tz is None:
        raise ValueError("filter_rth requires a tz-aware DatetimeIndex")

    et = df.index.tz_convert("America/New_York")
    in_session = (et.time >= RTH_OPEN) & (et.time < RTH_CLOSE)
    weekday = et.weekday < 5  # 0=Mon ... 4=Fri
    return df[in_session & weekday]

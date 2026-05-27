"""
NQ 1-minute OHLCV CSV loader.

Expected schema (case-insensitive):
    timestamp, open, high, low, close, volume

`timestamp` may be:
  * ISO 8601 string (preferred), e.g. "2024-01-02 09:30:00-05:00"
  * naive datetime; we then localize it to America/New_York
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ET = "America/New_York"
REQUIRED_COLS = {"open", "high", "low", "close", "volume"}


def load_nq_1m(
    path: str | Path,
    *,
    tz: str = ET,
    rth_only: bool = False,
) -> pd.DataFrame:
    """
    Load an NQ 1-minute OHLCV CSV into a tz-aware DataFrame indexed by timestamp.

    Parameters
    ----------
    path     : path to CSV file
    tz       : timezone to localize naive timestamps into. Default "America/New_York".
    rth_only : if True, drop bars outside 09:30-16:00 ET.

    Returns
    -------
    DataFrame with columns [open, high, low, close, volume], DatetimeIndex (tz-aware).
    """
    path = Path(path)
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    if "timestamp" not in df.columns:
        raise ValueError(f"{path}: CSV must contain a 'timestamp' column")
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing required columns {sorted(missing)}")

    ts = pd.to_datetime(df["timestamp"], utc=False, errors="raise")
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(tz, nonexistent="shift_forward", ambiguous="infer")
    else:
        ts = ts.dt.tz_convert(tz)

    df = (
        df.assign(timestamp=ts)
          .set_index("timestamp")
          .sort_index()
          [["open", "high", "low", "close", "volume"]]
          .astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    )

    # Drop duplicate bars (common with vendor exports that overlap days)
    df = df[~df.index.duplicated(keep="first")]

    if rth_only:
        from .rth_filter import filter_rth
        df = filter_rth(df)

    return df

"""The data seam. One CSV per instrument in `data/`, 1-minute bars, New York local time:

    timestamp,open,high,low,close,volume
    2018-01-02 09:30:00,6534.1,6535.8,6533.9,6535.2,412

No data is included in this repository; it is not ours to redistribute. `data/HOWTO.md` has the
export recipe and the two mistakes that will otherwise break your reproduction.

`volume` is whatever your feed calls volume. On a retail CFD or spot feed it is a TICK COUNT, not
contracts traded. That is the input this study ran on, and `real_vs_tick.py` is the check that it
is a usable proxy for the real thing.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
CAP = pd.Timestamp("2026-05-21 23:59")      # the programme's sealed period begins after this bar
COLS = ["open", "high", "low", "close", "volume"]


def load(inst: str, start: str = "2018-01-01", end: str | None = None) -> pd.DataFrame:
    """1m bars for one instrument, New York local time, capped before the sealed period."""
    p = DATA / f"{inst}.csv"
    if not p.exists():
        raise FileNotFoundError(f"{p} not found - see data/HOWTO.md")
    d = pd.read_csv(p, parse_dates=["timestamp"]).set_index("timestamp")
    d = d[~d.index.duplicated(keep="first")].sort_index()
    cap = min(pd.Timestamp(end), CAP) if end else CAP
    d = d.loc[start:str(cap), COLS].astype(float)
    assert d.index.max() <= CAP, "reached the sealed out-of-sample period"
    return d

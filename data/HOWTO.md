# Getting data in

One CSV per instrument in this folder, 1-minute bars, named `<INSTRUMENT>.csv`:

```
timestamp,open,high,low,close,volume
2018-01-02 09:30:00,6534.1,6535.8,6533.9,6535.2,412
```

The instrument name is whatever you pass on the command line: `python src/stage_a.py NAS` reads
`data/NAS.csv`. The study used `XAU`, `NAS`, `SPX` and `DAX` — gold, Nasdaq 100, S&P 500 and the
German 30 — on 2018-01-01 → 2026-05-21.

`src/real_vs_tick.py` additionally wants `data/MNQ.csv`, the same format, with **real traded
volume** (Micro Nasdaq futures). Any venue that gives you exchange volume will do; only the overlap
of the two files is compared.

## The two things that will silently break your reproduction

**1. Timezone.** Every window in the code is New York local time: the index session is 08:00–16:00,
the DAX session 03:00–11:30, and the regular-hours window in `real_vs_tick.py` is 09:30–15:59. The
loader does not convert anything — it trusts your timestamps. If your export is UTC or your broker's
server time (commonly UTC+2/+3), convert on export. A silently shifted session is the most common
way to fail to reproduce this, and it fails quietly: you still get touches, just the wrong ones.

**2. Your "volume" column is probably a tick count.** On a CFD or spot feed it is the number of
price updates in the bar, not contracts traded. That is fine — it is what the study ran on, and
`real_vs_tick.py` exists to measure how good a proxy it is — but you should know which one you have
before quoting a result. If your feed has both a tick-count and a real-volume column, a real-volume
column that is zero or constant for long stretches is not real volume.

The `volume` column must be positive. A feed with zero-volume bars will put rows of zero weight in
the profile and the value area will drift toward wherever the non-zero bars were.

## From MetaTrader 5

1. Tools → Options → Charts → "Max bars in chart": Unlimited, then restart the terminal.
2. Open the symbol on M1 and hold Home until the history has actually downloaded back to your start
   date. The export only contains what the terminal has.
3. Tools → History Center (F2) → pick the symbol and M1 → Export.
4. The export is tab-separated as `<DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>`.
   Join `<DATE>` and `<TIME>` into one `timestamp` column, rename `<TICKVOL>` to `volume`, and
   convert the timestamps to New York time. `<VOL>` is usually all zeros on a CFD feed, which is the
   point made above.

## Bar size

1-minute bars. The profile is built from them and the engine resamples up to hourly internally for
the swing anchors, so do not feed it 5-minute bars and expect the same levels: the profile would be
built from a fifth as many allocations.

## Sanity check before you trust anything

```python
from data import load
d = load("NAS", "2018-01-01", "2018-01-31")
print(len(d), d.index.min(), d.index.max(), d.volume.min(), d.volume.median())
```

If the first and last timestamps are not inside your intended session hours in New York time, fix
that before running the test.

"""Stage A — does a DR-1 profile LEVEL carry information about what price does after touching it?

Pre-registered (PREREG.md §5 + Amendment 1). Development period 2018-2022 only.
Event: the first 1m bar whose range enters a level's zone (level ± 0.1 x VA width) after the previous bar CLOSED
outside it. Rejection direction = back toward the side price came from (+1 if it came down into the zone).
Primary statistic: 30m forward return of the touch bar's close, signed by rejection direction, / 1m ATR(60).
Control: the identical event on the level shifted ±0.3-0.7 VA widths (random sign and size, fixed seed per hour).
Test: per-day mean of (real − placebo), paired over days with both. Bar |t| >= 3.0 (20 tests, Sidak).
"""
from __future__ import annotations

import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from data import load
from vpengine import dr1_levels

WINDOWS = {"XAU": None, "NAS": (8 * 60, 16 * 60), "SPX": (8 * 60, 16 * 60), "DAX": (3 * 60, 11 * 60 + 30)}
LEVELS = ["poc", "vah", "val", "phi", "plo"]
H = [5, 15, 30, 60]
BAR = 3.0
DEV = ("2018-01-01", "2022-12-31")
RESULTS = Path(__file__).resolve().parent.parent / "results"


def events(d, lv, level_col, shift=None, seed=0):
    """Touch events for one level series. Returns DataFrame with day and signed outcomes."""
    hour = d.index.floor("h") - pd.Timedelta("1h")              # levels stamped at the previous hour
    L = lv.reindex(hour)
    lvl = L[level_col].to_numpy()
    w = (L.vah - L.val).to_numpy()
    if shift is not None:
        rng = np.random.default_rng(seed)
        hrs = lv.index
        u = rng.uniform(0.3, 0.7, len(hrs)) * rng.choice([-1.0, 1.0], len(hrs))
        sh = pd.Series(u, index=hrs).reindex(hour).to_numpy()
        lvl = lvl + sh * w
    z = 0.10 * w
    hi, lo, cl = d.high.to_numpy(), d.low.to_numpy(), d.close.to_numpy()
    inz = (hi >= lvl - z) & (lo <= lvl + z)
    prev_c = np.r_[np.nan, cl[:-1]]
    prev_out = (prev_c > lvl + z) | (prev_c < lvl - z)
    prev_lvl_same = np.r_[False, lvl[1:] == lvl[:-1]]               # level unchanged since the previous bar
    ev = inz & prev_out & prev_lvl_same & np.isfinite(lvl)
    side = np.where(prev_c > lvl, 1.0, -1.0)                        # +1: came down from above -> reject up
    tr = np.maximum(hi, np.r_[cl[0], cl[:-1]]) - np.minimum(lo, np.r_[cl[0], cl[:-1]])
    atr = pd.Series(tr).rolling(60, min_periods=60).mean().shift(1).to_numpy()
    mins = d.index.hour * 60 + d.index.minute
    idx = np.flatnonzero(ev & np.isfinite(atr) & (atr > 0))
    t = d.index.values
    rows = {f"r{h}": [] for h in H}
    keep = []
    for i in idx:
        if i + 60 >= len(cl):
            continue
        if (t[i + 60] - t[i]) > np.timedelta64(90, "m"):            # forward window crosses a gap
            continue
        keep.append(i)
        for h in H:
            rows[f"r{h}"].append(side[i] * (cl[i + h] - cl[i]) / atr[i])
    keep = np.array(keep, dtype=int)
    out = pd.DataFrame(rows)
    out["day"] = d.index[keep].normalize()
    out["side"] = side[keep]
    out["min"] = mins[keep]
    return out


def tstat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else np.nan


def main(insts):
    res = []
    for inst in insts:
        t0 = time.time()
        d = load(inst, *DEV)
        lv = dr1_levels(d)
        win = WINDOWS[inst]
        for col in LEVELS:
            R = events(d, lv, col)
            P = events(d, lv, col, shift=True, seed=zlib.crc32(f"{inst}{col}".encode()))
            if win:
                R = R[(R["min"] >= win[0]) & (R["min"] < win[1])]
                P = P[(P["min"] >= win[0]) & (P["min"] < win[1])]
            rd = R.groupby("day").r30.mean(); pdm = P.groupby("day").r30.mean()
            both = rd.index.intersection(pdm.index)
            diff = (rd.loc[both] - pdm.loc[both]).to_numpy()
            row = dict(inst=inst, level=col, n_real=len(R), n_plac=len(P), days=len(both),
                       real_r30=R.r30.mean(), plac_r30=P.r30.mean(), diff=diff.mean(), t=tstat(diff),
                       real_r5=R.r5.mean(), real_r60=R.r60.mean(), real_t_days=tstat(rd.to_numpy()))
            row["pass"] = bool(np.isfinite(row["t"]) and abs(row["t"]) >= BAR)
            res.append(row)
            print(f"{inst} {col:<4} touches {len(R):>6} (placebo {len(P):>6}) days {len(both):>4} | "
                  f"real r30 {row['real_r30']:+.3f} ATR  placebo {row['plac_r30']:+.3f}  diff {row['diff']:+.3f}  "
                  f"t {row['t']:+.2f}  {'PASS' if row['pass'] else ''}", flush=True)
        print(f"  {inst} done in {time.time()-t0:.0f}s\n", flush=True)
        del d
    out = pd.DataFrame(res)
    out.to_csv(RESULTS / "stage_a_dev.csv", index=False)
    print(f"Stage A (development 2018-2022): {int(out['pass'].sum())} of {len(out)} level x instrument tests "
          f"clear |t| >= {BAR} on real-minus-placebo.")


if __name__ == "__main__":
    main(sys.argv[1:] or ["XAU", "NAS", "SPX", "DAX"])

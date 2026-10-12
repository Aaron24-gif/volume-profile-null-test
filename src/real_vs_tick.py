"""Gatekeeper: does a TICK-volume profile put POC / VAH / VAL where a REAL-volume profile does?

Every retail volume profile you have ever looked at on a CFD or spot feed was built from tick
count - the number of price updates in the bar - because the broker does not have, and could not
have, the traded volume of an exchange it is not part of. Before testing what those levels
predict, this checks that they land in the same place as levels built from real contracts.

The comparison: the same instrument, the same sessions, one profile from a tick-volume feed and
one from exchange volume (Nasdaq futures). A profile built from TIME alone - every bar weighted
equally - is the control: if the tick proxy were worthless, it would do no better than the clock.

    python src/real_vs_tick.py

Needs two files (see data/HOWTO.md): `data/NAS.csv` with tick volume and `data/MNQ.csv` with real
volume, both 1m bars in New York local time. Only the overlap of the two is compared, RTH only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from data import load
from vp import levels, profile

TICK, REAL = "NAS", "MNQ"
RTH = ("9h30min", "15h59min")
MIN_BARS = 350

tick = load(TICK)
real = load(REAL)

rows = []
for day in sorted(set(tick.index.normalize()) & set(real.index.normalize())):
    a, b = day + pd.Timedelta(RTH[0]), day + pd.Timedelta(RTH[1])
    ft, fr = tick.loc[a:b], real.loc[a:b]
    if len(ft) < MIN_BARS or len(fr) < MIN_BARS:
        continue
    out = {"day": day}
    for lab, f, weighted in (("real", fr, True), ("tick", ft, True), ("time", ft, False)):
        lo, hi = f.low.min(), f.high.max()
        vol = f.volume.to_numpy(float) if weighted else np.ones(len(f))
        h, e = profile(f.high.to_numpy(), f.low.to_numpy(), vol, lo, hi)
        poc, vah, val = levels(h, e)
        rng = hi - lo
        out[lab] = dict(poc=(poc - lo) / rng, vah=(vah - lo) / rng, val=(val - lo) / rng,
                        h=h / h.sum(), rng=rng)
    rows.append(out)

print(f"{len(rows)} RTH sessions compared (positions are fractions of the session range; NQ range median "
      f"{np.median([r['real']['rng'] for r in rows]):.0f} pts)\n")
print(f"{'vs REAL volume':<22}{'POC |diff|':>12}{'POC within 5%':>15}{'VAH |diff|':>12}{'VAL |diff|':>12}{'shape corr':>12}")
for lab in ("tick", "time"):
    d = {k: np.array([abs(r[lab][k] - r["real"][k]) for r in rows]) for k in ("poc", "vah", "val")}
    corr = np.array([stats.pearsonr(r[lab]["h"], r["real"]["h"])[0] for r in rows])
    print(f"{lab + ' profile':<22}{100*np.median(d['poc']):>10.1f}%{100*(d['poc']<=0.05).mean():>14.0f}%"
          f"{100*np.median(d['vah']):>10.1f}%{100*np.median(d['val']):>10.1f}%{np.median(corr):>12.3f}")
d_tt = np.array([abs(r["tick"]["poc"] - r["time"]["poc"]) for r in rows])
print(f"\ntick vs time-only POC: median |diff| {100*np.median(d_tt):.1f}% of range, within 5%: {100*(d_tt<=0.05).mean():.0f}%")
pts = np.array([abs(r["tick"]["poc"] - r["real"]["poc"]) * r["real"]["rng"] for r in rows])
print(f"tick vs real POC in NQ points: median {np.median(pts):.1f}, 75th pct {np.percentile(pts,75):.1f}, "
      f"90th {np.percentile(pts,90):.1f}")

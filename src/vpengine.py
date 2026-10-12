"""Volume Profile engine: causal 1H swing anchors, DR-1 developing profiles, level snapshots per hour.

Everything here is knowable at the timestamp it is stamped with:
  - a 1H fractal pivot at hour j (k lower highs / higher lows on each side) is usable from the CLOSE of hour j+k;
  - the DR-1 profile stamped at the close of hour t covers 1m bars from the anchor pivot's hour to t, inclusive,
    and nothing after t;
  - levels stamped at hour t are applied only to 1m bars inside hour t+1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def hourly(d: pd.DataFrame) -> pd.DataFrame:
    return d.resample("1h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def pivots(h: pd.DataFrame, k: int = 6):
    """Fractal pivots on 1H bars. Returns arrays (pivot_pos, kind +1 high / -1 low, usable_from_pos)."""
    H, L = h.high.to_numpy(), h.low.to_numpy()
    n = len(h)
    out = []
    for i in range(k, n - k):
        win_h = H[i - k:i + k + 1]
        win_l = L[i - k:i + k + 1]
        if H[i] == win_h.max() and (win_h == H[i]).sum() == 1:
            out.append((i, +1, i + k))
        if L[i] == win_l.min() and (win_l == L[i]).sum() == 1:
            out.append((i, -1, i + k))
    out.sort(key=lambda z: z[2])
    return out


def profile_vec(lo_b, hi_b, vol, lo, hi, nbins=100):
    """Vectorised OHLC-range allocation: each bar's volume spread evenly over the rows its range covers."""
    w = (hi - lo) / nbins
    if w <= 0:
        return None
    i0 = np.clip(((lo_b - lo) / w).astype(int), 0, nbins - 1)
    i1 = np.clip(((hi_b - lo) / w).astype(int), 0, nbins - 1)
    per = vol / (i1 - i0 + 1)
    diff = np.zeros(nbins + 1)
    np.add.at(diff, i0, per)
    np.add.at(diff, i1 + 1, -per)
    return np.cumsum(diff)[:nbins]


def value_area(h, lo, hi, va=0.70):
    nb = len(h); w = (hi - lo) / nb
    poc = int(np.argmax(h)); tot = h.sum(); a = b = poc; acc = h[poc]
    while acc < va * tot and (a > 0 or b < nb - 1):
        up = h[b + 1] if b < nb - 1 else -1.0
        dn = h[a - 1] if a > 0 else -1.0
        if up >= dn:
            b += 1; acc += h[b]
        else:
            a -= 1; acc += h[a]
    return lo + (poc + 0.5) * w, lo + (b + 1) * w, lo + a * w     # POC, VAH, VAL


def shape(h):
    p = h / h.sum()
    top = np.sort(p)[::-1][: max(1, len(p) // 10)].sum()          # share of volume in the top 10% of rows
    ent = -(p[p > 0] * np.log(p[p > 0])).sum() / np.log(len(p))    # normalised entropy, 1 = flat
    sm = np.convolve(p, np.ones(3) / 3, mode="same")
    pk = [i for i in range(1, len(sm) - 1) if sm[i] > sm[i - 1] and sm[i] >= sm[i + 1] and sm[i] >= 0.25 * sm.max()]
    return top, ent, len(pk)


def dr1_levels(d: pd.DataFrame, k: int = 6, va: float = 0.70, nbins: int = 100) -> pd.DataFrame:
    """One row per closed 1H bar: the DR-1 profile (anchored at the most recent CONFIRMED pivot, running to this
    bar) and its levels. Row timestamp = the hour's open; the levels are valid for the NEXT hour."""
    h = hourly(d)
    pv = pivots(h, k)
    hidx = h.index
    # 1m positions of each hour's first bar, for slicing
    m_t = d.index.values
    start_pos = np.searchsorted(m_t, hidx.values)
    end_pos = np.searchsorted(m_t, (hidx + pd.Timedelta("1h")).values)
    LO, HI, V = d.low.to_numpy(), d.high.to_numpy(), d.volume.to_numpy()
    rows = []
    pi = 0; anchor = None
    for t in range(len(h)):
        while pi < len(pv) and pv[pi][2] <= t:                    # pivot usable from the close of hour t
            anchor = pv[pi]; pi += 1
        if anchor is None:
            continue
        a_pos = start_pos[anchor[0]]; b_pos = end_pos[t]
        if b_pos - a_pos < 30:
            continue
        lo_b, hi_b, vol = LO[a_pos:b_pos], HI[a_pos:b_pos], V[a_pos:b_pos]
        lo, hi = lo_b.min(), hi_b.max()
        prof = profile_vec(lo_b, hi_b, vol, lo, hi, nbins)
        if prof is None or prof.sum() <= 0:
            continue
        poc, vah, val = value_area(prof, lo, hi, va)
        top, ent, nodes = shape(prof)
        rows.append((hidx[t], anchor[1], hidx[anchor[0]], lo, hi, poc, vah, val, top, ent, nodes,
                     h.close.iat[t], b_pos - a_pos))
    return pd.DataFrame(rows, columns=["hour", "anchor_kind", "anchor_time", "plo", "phi", "poc", "vah", "val",
                                       "top10", "entropy", "nodes", "close", "bars"]).set_index("hour")


def _bars(d, rule):
    return d.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def dr_levels(d: pd.DataFrame, anchor: str = "1h", k: int = 6, va: float = 0.70, nbins: int = 100) -> pd.DataFrame:
    """DR-1 generalised: anchor pivots found on `anchor` bars (1h, 4h); profile still built from 1m bars and stamped
    every closed hour. A pivot on bar j is usable once bar j+k has CLOSED. anchor='1h', k=6 reproduces dr1_levels."""
    h = hourly(d)
    pb = h if anchor == "1h" else _bars(d, anchor)
    tf = pd.Timedelta(anchor)
    pv = sorted((pb.index[u] + tf, pb.index[p], kind) for p, kind, u in pivots(pb, k))
    m_t = d.index.values
    LO, HI, V = d.low.to_numpy(), d.high.to_numpy(), d.volume.to_numpy()
    rows, pi, anc = [], 0, None
    for t in h.index:
        end = t + pd.Timedelta("1h")
        while pi < len(pv) and pv[pi][0] <= end:
            anc = pv[pi]; pi += 1
        if anc is None:
            continue
        a_pos = np.searchsorted(m_t, np.datetime64(anc[1])); b_pos = np.searchsorted(m_t, np.datetime64(end))
        if b_pos - a_pos < 30:
            continue
        lo_b, hi_b, vol = LO[a_pos:b_pos], HI[a_pos:b_pos], V[a_pos:b_pos]
        lo, hi = lo_b.min(), hi_b.max()
        prof = profile_vec(lo_b, hi_b, vol, lo, hi, nbins)
        if prof is None or prof.sum() <= 0:
            continue
        poc, vah, val = value_area(prof, lo, hi, va)
        rows.append((t, lo, hi, poc, vah, val, b_pos - a_pos))
    return pd.DataFrame(rows, columns=["hour", "plo", "phi", "poc", "vah", "val", "bars"]).set_index("hour")


def session_levels(d: pd.DataFrame, va: float = 0.70, nbins: int = 100) -> pd.DataFrame:
    """DR-5: the PREVIOUS NY session's profile (18:00-17:00), stamped on every hour of the current session."""
    sid = (d.index + pd.Timedelta("6h")).normalize()                # 18:00 -> next calendar day
    prof = {}
    for s, g in d.groupby(sid):
        if len(g) < 60:
            continue
        lo, hi = g.low.min(), g.high.max()
        p = profile_vec(g.low.to_numpy(), g.high.to_numpy(), g.volume.to_numpy(), lo, hi, nbins)
        if p is None or p.sum() <= 0:
            continue
        prof[s] = (lo, hi) + value_area(p, lo, hi, va)
    keys = sorted(prof)
    prev = {keys[i]: prof[keys[i - 1]] for i in range(1, len(keys))}
    h = hourly(d)
    hs = (h.index + pd.Timedelta("6h")).normalize()
    rows = [(t,) + prev[s] for t, s in zip(h.index, hs) if s in prev]
    return pd.DataFrame(rows, columns=["hour", "plo", "phi", "poc", "vah", "val"]).set_index("hour")

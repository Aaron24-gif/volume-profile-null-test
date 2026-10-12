"""Volume-profile primitives. Volume of each 1m bar is spread evenly across its high-low range (OHLC-range
allocation); other allocations are tested later."""
from __future__ import annotations
import numpy as np


def profile(high, low, vol, lo, hi, nbins=100):
    """Histogram of volume over [lo, hi] in nbins rows."""
    edges = np.linspace(lo, hi, nbins + 1)
    h = np.zeros(nbins)
    w = (hi - lo) / nbins
    for a, b, v in zip(low, high, vol):
        i0 = int(np.clip((a - lo) // w, 0, nbins - 1)); i1 = int(np.clip((b - lo) // w, 0, nbins - 1))
        h[i0:i1 + 1] += v / (i1 - i0 + 1)
    return h, edges


def levels(h, edges, va=0.70):
    """POC, VAH, VAL by the standard expansion from the POC row."""
    poc = int(np.argmax(h)); tot = h.sum(); a = b = poc; acc = h[poc]
    while acc < va * tot and (a > 0 or b < len(h) - 1):
        up = h[b + 1] if b < len(h) - 1 else -1
        dn = h[a - 1] if a > 0 else -1
        if up >= dn:
            b += 1; acc += h[b]
        else:
            a -= 1; acc += h[a]
    mid = (edges[:-1] + edges[1:]) / 2
    return mid[poc], edges[b + 1], edges[a]          # POC, VAH, VAL

# Volume profile levels, tested against random levels

Every level a volume profile gives you — the point of control, the edges of the value area, the
extremes of the range — tested as support and resistance against a **randomly placed level that
gets touched about as often**. Four markets, five levels each, five years of 1-minute data.

**0 of 20 tests cleared the pre-registered bar.** Not one of those levels moved price differently
from a line drawn at a price where no volume node exists.

Published so you can check that instead of taking it. `PREREG.md` fixed the levels, the control,
the statistic and the pass mark before any of it was run.

---

## What was tested

A profile is built on the **DR-1 range**: anchored at the most recent *confirmed* 1-hour swing and
running to the last closed bar. Confirmed matters — a fractal swing needs k bars on its right side
before you can know it is a swing, and a backtest that anchors the moment the swing prints is
reading the future. k = 6, so the anchor arrives about 3 to 4 hours after the extreme printed. That
lag is in the engine, not papered over.

Levels stamped at the close of hour *t* are applied only to bars inside hour *t+1*.

**The event**: the first 1-minute bar whose range enters a level's zone (level ± 0.1 × value-area
width) after the previous bar closed outside it.

**The measurement**: the 30-minute forward return of that bar's close, signed toward the side price
approached from — so a "rejection" scores positive — divided by 1-minute ATR(60). Inference is on
the **per-day mean**, so twelve touches in one afternoon count once and not as twelve independent
observations.

**The control**: the same level, moved 0.3 to 0.7 value-area widths at random with a fixed seed. Same
hours, same instrument, same measurement, same zone width — sitting at a price where nothing
happened. The statistic tested is **real minus placebo**, paired by day.

Four instruments (gold, Nasdaq, S&P, DAX) × five levels (POC zone, VAH, VAL, profile high, profile
low) = 20 tests, so the bar is Sidak-corrected: **|t| ≥ 3.0**.

## The result

Development period 2018-01-01 → 2022-12-31. 328,803 real touches, 268,098 placebo touches.

| | POC | VAH | VAL | profile high | profile low |
|---|---|---|---|---|---|
| **gold** | +0.44 | +0.40 | +2.66 | +0.07 | +1.15 |
| **Nasdaq** | +2.12 | +0.46 | +0.42 | +1.30 | +1.40 |
| **S&P** | −1.71 | +0.08 | +1.20 | +1.47 | −0.50 |
| **DAX** | −0.45 | +1.09 | +2.69 | +0.90 | +0.33 |

t of (real − placebo), per-day paired. **Bar: |t| ≥ 3.0. Cells clearing it: 0 of 20.**

The largest is 2.69. Across 20 independent tests of pure noise the *largest* |t| averages **2.17**,
with a 95th percentile of **3.01** — which is both why the bar was set at 3.0 and why 2.69 is not a
finding. Full numbers, including the 5 / 15 / 60-minute horizons: `results/stage_a_dev.csv`.

Because no cell cleared, the validation and holdout periods were never opened. They are still clean.

## Three things that argue against our own result

Publishing the verdict without these would be dishonest, because each one is a way we could be
wrong.

**1. The control is touched less often than the real level — 268,098 against 328,803.** The shifted
level sits further from price on average, so it gets reached about 23% less. The control is matched
on construction, not perfectly on touch frequency, and the gap is a real imperfection. A better
control would resample shifts to equalise touch counts per instrument-hour.

**2. 17 of the 20 differences are positive.** Taken at face value that is a lean toward real levels,
and a naive sign test on it would return p = 0.003. We do not read it as evidence, for two reasons.
The 20 cells are **not independent**: five levels on one instrument share the same days, often the
same touches, and the same placebo draw, so the sign pattern has nowhere near 20 degrees of freedom.
And point 1 gives a mechanism for a shared bias in exactly this direction, since real and shifted
levels are not reached under identical conditions. It is a flag for a better-matched control, not a
result. If you build that control and the lean survives, we would want to know.

**3. The point of control is the weakest level here and the one most people trade.** On the proxy
check below, the POC's *location* is unstable between feeds. We tested it as a zone, which is the
generous reading. Tested as an exact price it would do worse, not better.

## Before any of that: is the volume real?

Your charts almost certainly do not show traded volume. A broker streaming a CFD or spot feed cannot
know the volume of an exchange it is not part of, so the "volume" on the chart is a **tick count**:
how many times the price updated. Strategies have been built on that proxy for years without anyone
checking how good a proxy it is.

`src/real_vs_tick.py` checks it — 60 Nasdaq regular-hours sessions, profiles from tick counts against
profiles from real futures volume, with a profile built from **time alone** as the control:

| vs real volume | POC \|diff\| | POC within 5% | VAH \|diff\| | VAL \|diff\| | shape corr |
|---|---|---|---|---|---|
| **tick profile** | 1.0% | 73% | **2.0%** | **2.5%** | **0.970** |
| time-only profile | 2.0% | 60% | 6.5% | 12.5% | 0.903 |

Differences as a fraction of the session range; median NQ session range 386 points.
Output: `results/real_vs_tick.txt`.

**The value area survives. The point of control does not.** VAH and VAL land within 2.0% and 2.5% of
the session range and the whole shape correlates at 0.970, while the time-only control is out by
6.5% and 12.5% — so the tick count is carrying volume information and not just the clock. But the
POC, the single busiest price, matches to about 4 points in the median session and **jumps to a
different node in roughly 27% of them** (90th percentile gap: 112 points). A level that moves 112
points depending on whose feed you are looking at is not a price. It is a region, at best.

That is the transferable habit, and it cost one afternoon: **validate the input before you test what
it predicts.** Had the proxy failed, every result above would have been a statement about
one broker's tick feed rather than about markets.

## Running it

```bash
pip install -r requirements.txt
# put your own CSVs in data/ - see data/HOWTO.md
python src/stage_a.py                  # all four instruments, writes results/stage_a_dev.csv
python src/stage_a.py NAS              # one instrument
python src/real_vs_tick.py             # the tick-volume proxy check
```

Stage A takes about 30 seconds for gold and under 10 for each index on 2018–2022. `src/stage_a.py` runs on the development
window only; that is deliberate and the dates are at the top of the file.

No data is included — it is not ours to redistribute. `data/HOWTO.md` has the export recipe and the
two mistakes that will otherwise silently break your reproduction (timezone, and a volume column
that is not what it says).

## Files

| file | what it is |
|---|---|
| `PREREG.md` | the rules, the control, the pass mark and the kill condition, dated before the run |
| `src/vp.py` | profile and value-area primitives |
| `src/vpengine.py` | causal swing anchors, developing profiles, hourly level snapshots |
| `src/stage_a.py` | the test: touch events, the shifted-level placebo, the paired statistic |
| `src/real_vs_tick.py` | the proxy check: tick volume vs real futures volume |
| `src/data.py` | the CSV seam |
| `results/stage_a_dev.csv` | every cell, every horizon |
| `results/stage_a_dev.txt` | the run's own output |
| `results/real_vs_tick.txt` | the proxy check's output |

`vpengine.py` also carries `dr_levels` (the same construction with a configurable anchor timeframe)
and `session_levels` (the previous session's profile). Stage A uses neither; they are there because
the later stages do.

## What is not here

- **The break-and-retest split and the shape-to-volatility test** (Amendment 2). Both ran on
  development data with their own pre-set bars. The retest result is the interesting one and is not
  written up yet.
- **A stage comparing these levels against our own live trading record.** That is our trade file, so
  it is not published. It has no bearing on anything above.

## Honesty notes

- The bar and the kill condition in `PREREG.md` were written **before** the tests ran. That is the
  only reason "0 of 20" means anything. A bar chosen afterwards is a decoration.
- The programme's sealed out-of-sample period is capped in the loader with an assertion. It was never
  loaded for this study, and it is not spent on a hypothesis that fails in development.
- The levels tested are the ones a chart gives you. If you use profile levels differently — as
  targets, as context for a trade decided elsewhere, on a different range — this result does not
  speak to that, and says so.
- This is research code, published because the thing does not work. It is not a trading system, it is
  not advice, and nothing here is a recommendation.

**MIT. Take it.** The improvement we would most like back is a control matched on touch frequency
instead of construction — see point 1 above.

# Pre-registration — do volume profile levels carry information?

**Registered 2026-10-02, before any outcome in this repository was computed.** This file is the
reason the result means anything. It fixes the levels, the events, the control, the statistic and
the pass mark in advance, so that "0 of 20 cleared the bar" cannot be the product of choosing a bar
after seeing the numbers.

This is the published subset of a longer internal pre-registration: the data audit (§1), Stage A
(§5) and the amendments that bear on them. Stages that compare these levels against our own live
trading record are not published, because that record is not ours to hand out. Nothing in those
stages changes anything below.

## 0. What we expected, stated so it can be wrong in public

Two earlier studies in the same programme shape the prior:

- **94 level tests, 0 passed.** Prior-day, overnight, first-hour, weekly-open and round-number
  levels on 8 instruments carried no information about direction once the level was moved to a
  random nearby price. 39 of 94 beat a shifted-level placebo, against about 47 expected by chance.
- **A geometry study: direction 1 of 1,680 cells, forward volatility 415 of 3,360.** Structure
  derived from price appears to set the SCALE of the next move, not its LOCATION.

**So we expected** POC / VAH / VAL as support and resistance — a claim about direction — to fail the
placebo, and profile SHAPE to predict forward volatility. Either result gets reported.

## 1. Data, and the audit that had to pass first

| Feed | Volume column | Range used |
|---|---|---|
| 1m spot/CFD: gold, Nasdaq, S&P, DAX | tick count | 2018-01-01 → 2026-05-21 |
| 1m futures: MNQ, MES | **real contracts** | 2026-01-20 → 2026-04-15 |

The study's own charts are built from tick volume, so the first question is whether tick volume is
a usable stand-in for traded volume. `src/real_vs_tick.py`, 60 Nasdaq RTH sessions:

- **Tick volume is a validated proxy for the value area**: VAH and VAL within 2.0% and 2.5% of the
  session range, profile shape correlation r = 0.970. A profile built from time alone does far
  worse (6.5% / 12.5%, r = 0.903), which is what makes the first number mean something.
- **The point of control is not**: it matches to about 4 points in the median session but lands on a
  different node in roughly 27% of them (90th percentile gap 112 points). **The POC is therefore
  tested as a zone (± 0.1 × value-area width), never as an exact price.**
- Anything that passes on tick volume is re-checked against real futures volume for Jan–Apr 2026,
  for direction of effect only: that window is far too short for significance.

A hard cap at 2026-05-21 is asserted in the loader. The programme's sealed out-of-sample period
begins after it and was never loaded for this study.

## 2. Splits

| | |
|---|---|
| Development | 2018-01-01 → 2022-12-31 |
| Validation | 2023-01-01 → 2024-12-31 |
| Frozen holdout | 2025-01-01 → 2026-05-21 |

Parameters are chosen on development and fixed before validation is read. **Validation is read only
for a cell that clears the bar on development.** No cell did, so no later period was opened.

## 3. Profile construction

- 1m bars; each bar's volume spread evenly across its own high–low range (OHLC-range allocation).
  Typical-price and close-price allocation are robustness variants.
- 100 rows across the profile's own range (primary); fixed-point rows are a variant.
- Value area 70% (primary, the platform default); 60 / 65 / 68 / 75 / 80% reported as a stability
  band, never selected on.
- High and low volume nodes: local maxima and minima of the 3-row-smoothed histogram, prominence at
  least 25% of the POC row.

## 4. The range the profile is built on, and when it becomes knowable

Swings are 1H fractal pivots: a high with k lower highs on each side, **usable only after the k-th
right-hand bar closes**. k = 6 primary; 3 and 12 as small and large variants.

| ID | Definition | Known from |
|---|---|---|
| **DR-1 (primary)** | **Anchored at the most recent confirmed 1H swing, running to the last closed bar** | each bar, once the anchor is confirmed |
| DR-2 | Last confirmed swing high to last confirmed swing low | confirmation of the later pivot |
| DR-3 | DR-2 with k = 12 | as DR-2 |
| DR-4 | Last completed pivot-to-pivot leg | confirmation of its end pivot |
| DR-5 | Previous session (18:00–17:00) | session close |
| DR-6 | Current developing session | each bar |
| DR-7 | Rolling 24 hours | each bar |

A discretionary trader marks an "obvious" swing as soon as price leaves it; a fractal needs k bars
to confirm. **That lag is measured and reported rather than hidden** — in the worked example that
started this study, the low became usable about 3 to 4 hourly bars after it printed. A backtest that
anchors to a swing the moment it prints is reading the future.

## 5. Stage A — does the location carry information? (primary)

**Event.** The first 1m bar whose range enters a level's zone (level ± 0.1 × value-area width) after
the previous bar closed outside it. Levels stamped at the close of hour t are applied only to bars
inside hour t+1. 08:00–16:00 New York for the US indices, all hours for gold.

**Direction.** "Rejection" means back toward the side price approached from.

**Outcomes.** Signed forward return at 5 / 15 / 30 / 60 minutes, MFE and MAE in units of 1m
ATR(60), and P(+1 ATR before −0.5 ATR).

**Control — the whole point.** The identical event on a **shifted level**: the same level moved ±0.3
to 0.7 value-area widths at random with a fixed seed. The placebo therefore has the same touch
frequency, the same hours and the same measurement, and differs only in sitting at a price where no
volume node exists. A second control uses the previous day's profile, matched on time of day.

**Primary tests: 5 levels (POC zone, VAH, VAL, profile high, profile low) × 4 instruments = 20.
Pass mark |t| ≥ 3.0 on (real − placebo), Sidak-corrected for 20 tests.**

## 6. Ledger

Every experiment appends a row to an internal ledger: id, hypothesis, period, instrument, profile
definition, parameters, entry, stop, target, n, result, out-of-sample result, status, reason for
rejection. **Failed experiments are kept.** That is what makes the count of tests honest.

---

## Amendment 1 — 2026-10-02, before any Stage A outcome was computed

- **DAX window corrected to 03:00–11:30 New York**, its own cash session. The registered 08:00–16:00
  window was written for the US indices and would have tested DAX mostly outside its own trading
  hours. Nasdaq and S&P keep 08:00–16:00; gold stays all hours.
- **The primary statistic is named:** the 30-minute forward return of the touch bar's close, signed
  in the rejection direction, divided by 1m ATR(60). Inference is on the **per-day mean of
  (real − placebo)**, paired over days that have both, so that a cluster of touches inside one day
  counts once rather than as many independent observations. The 5 / 15 / 60-minute returns, MFE, MAE
  and P(+1 ATR before −0.5 ATR) are reported but not tested.
- **Stage A runs on development data (2018–2022) only.**

## Amendment 2 — 2026-10-02, after Stage A, before anything else was computed

Registered then, and reported in the README: a break-and-retest split of the same events by approach
side, and a test of whether profile shape predicts forward volatility. Both on development data
only, both with their own pre-set bars (|t| ≥ 2.73 across 8 tests, and |t| ≥ 3.0 across 20 tests).
Their code is not in this repository.

## What would have changed our mind

A cell clearing |t| ≥ 3.0 on (real − placebo) in development, confirmed with the same sign and
|t| ≥ 2.0 in validation, surviving the previous-day-profile control, and visible in the direction of
effect in the real-volume window. **None of the 20 cleared the first of those.**

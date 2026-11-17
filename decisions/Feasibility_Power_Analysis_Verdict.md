# Feasibility and power analysis: verdict

16 November 2026. Run on SDUD 2017Q1 to 2025Q4, 1,392,368 state-product-quarter observations,
3,611 products, 51 states, 42 never-switcher states. Scripts in ~/work/feas1-4.py.

## VERDICT: drop candidate B. Switch to candidate A.

Candidate B (shortage absorption by payer arrangement) is underpowered by roughly a factor of
four to six. This was not knowable from the data-completeness gate, which it passed. It only
became visible when power was tested, which is why power is now the first gate on anything,
not the last.

## Test 1: state-level difference-in-differences, actual estimates

Relative-outcome DiD on log prescriptions, plus or minus 8 quarter window, against the mean of
42 never-switcher states.

| State | Switch | Direction | Pre q | Post q | Products | DiD | Permutation p |
|---|---|---|---|---|---|---|---|
| NC | 2021Q3 | carve-**in** | 8 | 8 | 938 | **-0.165** | 0.349 |
| CA | 2022Q1 | carve-out | 8 | 8 | 1,506 | **-0.116** | 0.465 |
| OK | 2024Q2 | carve-**in** | 8 | 7 | 617 | **+0.123** | 0.163 |
| NY | 2023Q2 | carve-out | 8 | 8 | 1,288 | **+0.187** | not run, confounded by unwinding |
| WV | 2017Q3 | carve-out | 2 | 8 | 0 | **unusable** | needs 2014-2016 |

Two findings, both fatal:

1. **No estimate is distinguishable from noise.** Permutation p values of 0.349, 0.465 and
   0.163 against 42 placebo states. Placebo SDs were 0.167, 0.128 and 0.107 log points, so
   every treated estimate sits inside the placebo distribution.
2. **The signs are incoherent.** The two carve-ins go in opposite directions (NC -0.165, OK
   +0.123) and so do the two carve-outs (CA -0.116, NY +0.187). If the mechanism were real and
   detectable, direction would track the switch. It does not.

## Test 2: triple difference, within-state shortage vs non-shortage

The first test was arguably the wrong estimand, since the paper's claim is about the
differential shortage response rather than the overall level. Differencing shortage against
non-shortage products within the same state and quarter should remove state-level shocks.
It barely helped, because the noise moves to the product-set sampling variance.

Minimum detectable effect, 80% power, 5% two-sided, as a percentage change in dispensing:

| Shortage products in set | T=19 | T=21 | T=30 |
|---|---|---|---|
| 30 | 64.9% | 63.6% | 57.1% |
| 60 | 41.7% | 40.8% | 36.2% |
| 120 | 27.5% | 25.6% | 25.6% |
| 300 | 16.4% | 15.3% | 14.4% |

Realistic shortage counts are 60 to 120 products with balanced Medicaid panels (FDA lists
roughly 60 to 113 ongoing; ASHP 216 to 323, not all mapping to Medicaid-dispensed products).

**So the design can only detect a 26% to 42% differential effect.** A real policy effect on
dispensing would be single digits to low double digits. The design is short by four to six
times, and it cannot be rescued: the binding constraints are 3 to 4 treated states and
quarterly state-level data, and SDUD has no finer geography or time grain.

## Test 3: why it failed, and what the data CAN support

The failure is structural, not incidental. **SDUD supports designs where treatment varies
across products, not across states.** There are only 51 states, few ever switch, and
state-level idiosyncratic variance (placebo SD 0.107 to 0.167) swamps any plausible effect.

Same machinery, treatment assigned at product level across all states:

| Treated products | Placebo SD | MDE (80%, 5%) | MDE as % change |
|---|---|---|---|
| 30 | 0.1448 | 0.4055 | 50.00% |
| 60 | 0.0987 | 0.2764 | 31.83% |
| 120 | 0.0689 | 0.1930 | 21.29% |
| 300 | 0.0451 | 0.1263 | 13.46% |
| 600 | 0.0299 | 0.0838 | **8.74%** |
| 1,200 | 0.0229 | 0.0641 | **6.62%** |

Noise falls as one over the square root of the treated count, and the treated count is capped
by the number of products rather than the number of states.

**This is why the recall paper and the discontinuation paper worked.** Recalls and
discontinuations are product-level events with thousands of treated NDCs. That is the design
pattern this dataset supports, and it is the pattern to stay inside.

## Why candidate A now wins

The Medicaid CPI rebate (generics from 1 Jan 2017) and the AMP cap removal (1 Jan 2024) apply
at **product** level, with exposure intensity varying continuously by product. Health Affairs
2023 found nearly half of generic drugs owed inflationary rebates in 2017-20, and generics are
about 90% of prescriptions, so the treated set is on the order of 1,000 to 2,000 products.

At 1,200 treated products the MDE is **6.6%**, which is inside the plausible range for a real
policy effect. Candidate A is powered. Candidate B is not.

A second advantage: the natural outcome for A is product-level market exit, a binary event
(does the NDC stop appearing in SDUD). Exit is a larger and cleaner signal than a change in
dispensing volume, and discrete-time logistic hazard is already in the method set from the two
completed papers.

**The risk changes character, and improves.** B's risk was an undetectable effect, which is a
certain failure. A's risk is being scooped by an NBER team that holds the method, which is an
uncertain failure. Prefer the uncertain one.

## What this costs and what it saves

Cost: one afternoon. Saving: not discovering this after writing a manuscript.

## Next gates for candidate A, in order

1. **Power first, properly.** Build the actual exposure measure and re-run this machinery on
   it before writing anything. The lesson of today is that power comes before everything.
2. SSRN and NBER sweep on rebate reform and generic exit, already partly done: no paper
   answers the question, four NBER papers hold adjacent ground, and NBER w32249 already
   approximates the inflation penalty from SDUD for the 340B program.
3. Read in full: Health Affairs 2023 (hlthaff.2022.01029) for the estimation method, and the
   CRA/Viatris report for the claim being tested.
4. Download SDUD 2014 to 2016, needed for baseline quarters (the earliest allowed baseline
   under BBA 2015 is 2014Q3), and NADAC from 2013 for the price series.

---

# PART 2: candidate A tested. VERDICT: GO.

Run 16 November, SDUD 2014Q1 to 2025Q4 (13 files, 5.7 GB). Scripts ~/work/expo.py,
powerA.py, powerA2.py. These are feasibility-grade estimates on a crude pipeline, not
final results.

## Exposure measure validates against published work

CPI-rebate exposure built from SDUD alone, as excess growth in Medicaid reimbursement per
unit above an inflation benchmark since the 2014Q3 baseline quarter. No NADAC needed.
*Health Affairs* 2023 used average Medicaid reimbursement as one of its three price measures,
so this is precedented.

**52.9% of products classified as exposed.** Health Affairs 2023 found nearly half of generic
drugs owed inflationary rebates in 2017-20. The measure reproduces their result independently.

## Power: adequate, roughly four times better than candidate B

| | candidate A | candidate B |
|---|---|---|
| Treated units | 1,800 to 3,600 products | 3 to 4 states |
| MDE, dispensing | **~8%** | 26% to 42% |
| MDE, exit rate | ~1.2 pp | n/a |

Treatment varying across products rather than states is what makes the difference.

## Primary result: the 2024 AMP cap removal

Exposure measured baseline 2014Q3 to 2023Q4, predetermined. Pre 2022-2023, post 2024-2025.
Permutation inference, 400 draws, exposure labels permuted across products.

| Specification | n | exposed | dispensing DiD | p |
|---|---|---|---|---|
| 2% per year benchmark | 3,668 | 2,067 (56.4%) | **-0.1115** | **0.002** |
| 3.5% per year benchmark | 3,668 | 1,802 (49.1%) | **-0.1160** | **0.002** |
| PLACEBO-IN-TIME 2022Q1, 2% | 4,185 | 2,245 | -0.0140 | 0.676 |
| PLACEBO-IN-TIME 2022Q1, 3.5% | 4,185 | 1,997 | -0.0330 | 0.284 |

**Products more exposed to Medicaid inflation rebates saw roughly 11% larger declines in
Medicaid dispensing after the AMP rebate cap was removed on 1 January 2024.** Robust to the
inflation benchmark. The placebo-in-time two years earlier is clean, so this is not mean
reversion.

This is the industry claim (CRA for Viatris, Bates White for AAM) tested independently on
public data for the first time.

## What the testing killed

**The exit outcome is not usable as specified.** The first run showed exit DiD +0.0345,
p=0.007, but that used exposure measured 2014Q3 to 2016Q4 for a 2024 event, which is stale.
Correctly timed, the real-event exit effect vanishes (+0.0035, p=0.454) while the
**placebo-in-time becomes significant** (-0.0103, p=0.025 to 0.030). Exit needs redefining,
probably at NDC level rather than product-name level, before it can be used at all.

**The 2017 CPI-rebate extension is the weaker event.** Real dispensing DiD -0.0512 (p=0.050),
but the placebo-in-time at 2016Q1 gives -0.0304 (p=0.100), roughly 60% of the real estimate.
Mean reversion contaminates it. Volume-restricted it loses significance entirely (p=0.117).
**Lead with 2024, treat 2017 as secondary with the placebo reported alongside.**

## Known weaknesses to fix before writing

1. **CPI-U is a 2% / 3.5% proxy, not the real series.** Real inflation ran far above 2% in
   2021-22, so the proxy misclassifies exposure. Misclassification attenuates, so the true
   effect is plausibly larger. Needs the actual BLS CPI-U series, a small file.
2. **"Product" is the SDUD 10-character FDA list name**, a crude molecule proxy. Needs the
   real NDC to ingredient crosswalk from the FDA NDC Directory.
3. **Price is Medicaid reimbursement per unit**, a proxy for AMP. Precedented but needs the
   three-measure triangulation Health Affairs used.
4. **2024-25 contains the IRA Part D redesign and the Medicaid unwinding tail.** Needs
   controls and an argument that neither differentially hits exposed products.
5. **Competitive risk stands.** Four NBER papers hold adjacent ground and w32249 already
   approximates the inflation penalty from SDUD for 340B. Move quickly.

## Next steps

1. Real CPI-U series, and NDC to ingredient crosswalk.
2. Rebuild exposure at NDC level with real CPI-U, re-run everything above.
3. Redefine the exit outcome at NDC level and re-test against the placebo.
4. SSRN and NBER sweep, final check before writing.
5. Read Health Affairs 2023 and the CRA/Viatris report in full for positioning.

---

# PART 3: candidate A fails identification. VERDICT: DO NOT WRITE EITHER PAPER.

Run 16 November, same data. Script ~/work/rob1.py. The earlier GO in Part 2 is **withdrawn**.
Power was adequate. Identification is not.

## Test 1: event-time path around 2024Q1. FAILS.

Exposure fixed, measured 2014Q3 to 2023Q4. Baseline quarter 2023Q4. 2,795 balanced products,
1,504 exposed. Difference between exposed and non-exposed log dispensing, by quarter:

| quarter | diff | | quarter | diff |
|---|---|---|---|---|
| 2021Q1 | +0.0236 | | 2024Q1 **(event)** | -0.0199 |
| 2021Q2 | -0.0069 | | 2024Q2 | -0.0248 |
| 2021Q3 | -0.0071 | | 2024Q3 | -0.0272 |
| 2021Q4 | -0.0122 | | 2024Q4 | -0.0258 |
| 2022Q1 | +0.0173 | | 2025Q1 | -0.0572 |
| 2022Q2 | -0.0008 | | 2025Q2 | -0.0713 |
| 2022Q3 | -0.0028 | | 2025Q3 | -0.0982 |
| 2022Q4 | -0.0206 | | 2025Q4 | -0.1237 |
| 2023Q1 | -0.0214 | | | |
| 2023Q2 | -0.0125 | | | |
| 2023Q3 | -0.0142 | | | |
| 2023Q4 | +0.0000 | | | |

**There is no break at 2024Q1.** All of 2024 sits at -0.020 to -0.027, inside the pre-period
wobble of plus or minus 0.02. The divergence begins in **2025Q1** and grows monotonically to
-0.124 by 2025Q4. A policy effective 1 January 2024 does not produce that shape.

Worse, the pre-period itself drifts: +0.024 in 2021Q1 down to -0.014 by 2023Q3, roughly
-0.004 per quarter. Extrapolated, that pre-trend alone delivers about -0.04 by 2025Q4, so a
large share of the 2025 divergence is pre-existing trend, not treatment.

And the 2025 timing has an obvious rival explanation: the **IRA Part D redesign took effect
January 2025**, a major drug-market shock that could plausibly hit high-prior-price-growth
products differentially.

## Test 2: dose-response. FAILS.

A genuine rebate-exposure effect must rise with exposure. It does not.

| exposure quintile | n | median excess | change vs lowest quintile |
|---|---|---|---|
| Q1 (lowest) | 559 | -1.155 | reference |
| Q2 | 559 | -0.381 | -0.0271 |
| Q3 | 559 | +0.075 | -0.0068 |
| Q4 | 559 | +0.391 | **-0.1495** |
| Q5 (highest) | 559 | +0.881 | **+0.0057** |

**The most exposed quintile shows no effect at all.** The entire result sits in Q4. That is a
single-bin artifact, not a dose-response. The -0.11 headline in Part 2 came from a binary
exposed/not split, which one quintile can drive on its own.

## Test 3: inflation benchmark sweep. Robust, but robust to the wrong thing.

| benchmark | exposed % | DiD | perm p |
|---|---|---|---|
| 1.5%/yr | 56.0% | -0.0425 | 0.047 |
| 2.0%/yr | 53.8% | -0.0491 | 0.053 |
| 2.5%/yr | 51.4% | -0.0591 | 0.023 |
| 3.0%/yr | 49.2% | -0.0618 | 0.023 |
| 3.5%/yr | 47.0% | -0.0607 | 0.010 |
| 4.0%/yr | 44.8% | -0.0645 | 0.003 |
| 5.0%/yr | 39.2% | -0.0631 | 0.010 |

The estimate is stable across every plausible CPI proxy, so CPI precision was never the risk.
But stability of a pattern that has no break at the policy date and no dose-response is not
evidence for the policy. It is evidence of a persistent differential trend.

## Where this leaves the supply chain line

Three candidates, all now tested or killed:

| | verdict | reason |
|---|---|---|
| B: payer arrangement | **dead** | underpowered 4 to 6 times. 3 to 4 treated states, MDE 26-42% |
| A: rebate reform | **dead** | adequately powered, but no break at the policy date, non-monotone dose-response, pre-trend, and a rival 2025 shock |
| C: shortage cascade | untested | product-level so power may hold; event count unknown |

The pattern across sixteen candidate questions and two full feasibility tests: the open
questions in this literature are not answerable at the precision required with the public
data available. That is a finding about the research position, not a failure of effort.

**Recommendation: do not start either paper.** Cost of learning this: one day. Cost of
learning it after drafting: a quarter or more.

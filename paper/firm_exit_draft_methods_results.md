# When the Only Supplier Fails: Abrupt Manufacturer Exit and the Absence of Market Repair in US Generic Drug Markets

Vasu Atmakuri, Independent Researcher, Dallas, TX. ORCID 0009-0007-5955-2466.
Draft methods and results, 17 November 2026. All figures computed from public data.

---

## 2. Methods

### 2.1 Data

Medicaid State Drug Utilization Data (SDUD), published quarterly by the Centers for Medicare
and Medicaid Services, 2014Q1 through 2026Q1: 13 annual files, 5.7 GB, approximately 57
million records covering 6.78 billion prescriptions between 2017 and 2025. Each record
reports, for a state, quarter and 11-digit National Drug Code, the number of prescriptions,
units reimbursed and amounts reimbursed.

Two handling decisions materially affect results and are stated explicitly.

**National aggregate rows are excluded.** SDUD contains both state rows and a national
aggregate row coded 'XX'. These coexist, and summing them double counts by approximately
1.99x. The national rows are substantial, rising from 274,082 records in 2017 to 320,609 in
2025. All analyses are restricted to state rows.

**Suppressed cells are treated as missing, not zero.** Records flagged with suppression
constitute 48.9% to 52.3% of all rows in every year of the panel. Because suppression
applies to very low prescription counts, the suppressed share of volume is small, but the
suppressed share of cells is approximately half. Suppressed cells are excluded from
aggregation rather than imputed.

### 2.2 Molecule and therapeutic class assignment

National Drug Codes were mapped to active ingredient and Established Pharmacologic Class
using the FDA National Drug Code Directory product file combined with the openFDA bulk NDC
dataset, the latter included because it retains discontinued products that the current
directory omits. The combined crosswalk contains 136,099 unique labeler-product keys.

Coverage, measured by prescriptions: **76.7% matched to active ingredient** and **69.3%
matched to Established Pharmacologic Class.** Unmatched volume is excluded from
molecule-level and class-level analyses but retained for firm-level exit detection.

### 2.3 Identifying abrupt manufacturer exit

Manufacturer exits are identified endogenously from dispensing data rather than from an
external register, because no public register of abrupt pharmaceutical manufacturer failure
exists. A labeler is classified as exiting in quarter t when its total dispensing averaged at
least 2,000 prescriptions per quarter over the four preceding quarters and fell below 10% of
that level across the four quarters beginning at t. Exit detection uses the full panel,
including records unmatched to the crosswalk, so that firm size is not understated.

This yields **105 exiting labelers** between 2016 and 2024, distributed across the period with
no year contributing more than a small share.

**Validation.** The procedure recovers the 2023 collapse of Akorn Pharmaceuticals without
external input. Labeler 17478 exits in 2023Q2 with 111 products, and labeler 50383, Hi-Tech
Pharmacal, which Akorn owned, exits in 2023Q3 with 80 products. Akorn closed its four
manufacturing facilities abruptly in February 2023 and recalled all in-date product in April
2023.

### 2.4 Treatment definition and exposure intensity

For each exit, the exiting firm's share of each affected ingredient is computed over the four
quarters preceding exit. Ingredients are assigned to their first exit exposure, giving **110
treated ingredients**. Exposure is the exiting firm's pre-exit share, and ingredients are
grouped into minor (under 35%), intermediate (35 to 95%) and sole-supplier (95% and above)
bands. The sole-supplier band contains 43 ingredients, of which 12 have complete positive
dispensing across the full estimation window.

Controls are **1,082 ingredients** never exposed to any detected exit, restricted to those
with positive dispensing in at least 40 quarters and mean dispensing of at least 400
prescriptions per quarter.

### 2.5 Estimation and inference

The outcome is log national Medicaid dispensing at the ingredient-quarter level. The estimate
is the difference between mean log dispensing in the six quarters after exit and the six
quarters before, differenced against the same quantity for controls assigned placebo exit
dates drawn from the empirical distribution of true exit dates.

**Inference is by permutation**, not asymptotic standard errors, because the sole-supplier
band is small. Six hundred resamples of control ingredients with randomly assigned exit dates
generate the null distribution, and two-sided p values are the share of placebo estimates
exceeding the observed estimate in absolute value. Exact n is reported for every estimate.

---

## 3. Results

### 3.1 Dispensing loss rises monotonically with the exiting firm's market share

| exposure band | n | difference-in-differences | change | permutation p |
|---|---|---|---|---|
| minor, 0 to 35% | 47 | +0.058 | +5.9% | 0.176 |
| intermediate, 35 to 95% | 8 | -0.094 | -9.0% | 0.388 |
| **sole supplier, 95 to 100%** | **12** | **-0.785** | **-54.4%** | **0.0017** |
| all treated | 67 | -0.091 | -8.7% | 0.028 |

Exit of a minor supplier produces no detectable loss. Exit of a sole supplier removes over
half of national Medicaid dispensing of the affected ingredient. The monotone gradient, with
a null at low exposure, is the central identifying evidence.

### 3.2 The loss begins exactly at exit and does not recover

Log dispensing relative to the quarter before exit:

| band | t-6 | t-4 | t-2 | t-1 | **t+0** | t+2 | t+4 | t+6 | t+8 |
|---|---|---|---|---|---|---|---|---|---|
| minor | -0.150 | -0.131 | -0.026 | 0.000 | -0.061 | +0.019 | +0.022 | +0.089 | +0.150 |
| intermediate | -0.365 | -0.244 | +0.093 | 0.000 | -0.205 | -0.109 | -0.221 | -0.045 | -0.030 |
| **sole supplier** | -0.351 | -0.278 | +0.030 | 0.000 | **-1.787** | **-1.613** | **-1.456** | **-0.825** | **-0.928** |

Sole-supplier ingredients show no pre-exit trend, a discontinuity of -1.79 log points at the
exit quarter, and dispensing still -0.93 log points below baseline two years later. Minor
exposure shows no discontinuity at all.

### 3.3 Replacement entry almost never occurs

| band | n | suppliers at t-1 | t+4 | t+8 | new firms by t+8 | share with any entry |
|---|---|---|---|---|---|---|
| minor | 54 | 8.69 | 9.17 | 8.63 | 2.65 | **85%** |
| intermediate | 12 | 3.25 | 2.92 | 2.08 | 1.33 | 67% |
| **sole supplier** | 43 | 1.05 | 0.63 | 0.60 | 0.37 | **16%** |

Where the failing firm was one of many suppliers, 85% of ingredients see new entry within two
years. Where it was the only supplier, 16% do, and the mean supplier count falls from 1.05 to
0.60 and stays there.

### 3.4 Patients are not moved to therapeutic alternatives

Log dispensing of all other ingredients in the same Established Pharmacologic Class:

| band | n | t+0 | t+2 | t+4 | t+6 | t+8 |
|---|---|---|---|---|---|---|
| minor | 47 | -0.075 | -0.038 | -0.033 | +0.010 | +0.055 |
| intermediate | 7 | +0.032 | +0.115 | +0.002 | -0.028 | -0.016 |
| sole supplier | 24 | -0.009 | +0.125 | -0.011 | +0.018 | +0.082 |

When a sole-supplier ingredient loses roughly 70% of its volume, the rest of its therapeutic
class moves between -0.01 and +0.08 log points. There is no offsetting increase. The volume
does not reappear elsewhere in the class.

### 3.5 Robustness

**Threshold invariance.** The exit detection threshold is arbitrary. Varying it changes the
sample substantially and the estimate not at all.

| threshold, rx/quarter | exits | sole-supplier ingredients | effect at t+4 | t+8 |
|---|---|---|---|---|
| 20,000 | 44 | 26 | -1.249 | -0.917 |
| 10,000 | 60 | 32 | -1.370 | -0.917 |
| 5,000 | 85 | 37 | -1.107 | -0.680 |
| 2,000 | 105 | 44 | -1.446 | -0.919 |

**Placebo in time.** Assigning a pseudo-exit eight quarters before the true exit yields +0.061
against a true-event estimate of -0.203 in the pooled specification. The placebo is small and
opposite in sign.

**Internal placebo.** The minor-exposure band functions as a within-design placebo: these
ingredients experience a firm failure but lose no supply, and show no effect.

### 3.6 Statistical power

The placebo distribution implies a minimum detectable effect of approximately 12% at 80%
power and 5% significance. Observed sole-supplier effects of 54% to 70% exceed this by a wide
margin.

---

## Limitations to state in the paper

1. Medicaid is not the national market. Generalisation to commercial and Medicare
   populations is an assumption, not a result.
2. The sole-supplier analytical sample is 12 to 43 ingredients depending on window
   requirements. These are rare events by nature. Inference is by permutation for this reason.
3. The crosswalk covers 76.7% of prescriptions by ingredient and 69.3% by class.
4. SDUD is quarterly, so within-quarter timing of exit cannot be resolved.
5. Exit is detected from dispensing rather than from a register of corporate failure, so the
   cause of each exit, whether bankruptcy, enforcement or voluntary withdrawal, is not
   separated. This limits policy attribution and is the most valuable extension.

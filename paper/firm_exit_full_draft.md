# When the Only Supplier Fails: Abrupt Manufacturer Exit and the Absence of Market Repair in US Generic Drug Markets

Vasu Atmakuri, Independent Researcher, Dallas, TX. ORCID 0009-0007-5955-2466.
Full draft, 17 November 2026. All estimates computed from public data; every figure in this
draft traces to a logged run.

---

## 1. Introduction

Policy attention to pharmaceutical supply reliability has concentrated almost entirely on
shortages: their causes, their prediction, and the effectiveness of regulatory response. The
underlying market event that produces many of them has received far less scrutiny. Generic
drug markets in the United States are highly concentrated, and a substantial number of
molecules are supplied by a single manufacturer. When such a manufacturer fails, the question
is not whether supply is interrupted, which is immediate and arithmetic, but whether the
market repairs itself. Competitive markets are expected to attract replacement entry, and
clinical practice is expected to substitute within therapeutic class. Neither assumption has
been tested at national scale.

The existing literature asks a different question. Work on generic market structure documents
entry and exit and relates supplier counts to prices, and work on firm behaviour explains
*why* firms leave markets. What happens to patients after a firm leaves, and whether anyone
replaces it, is not established.

This paper addresses that gap. Using twelve years of national Medicaid dispensing records, it
identifies 105 abrupt manufacturer exits, measures what happens to the affected molecules, and
tests the two repair mechanisms directly: replacement entry by other manufacturers, and
therapeutic substitution within pharmacologic class.

The central result is that repair largely does not occur. Where the failing firm was one of
many suppliers, dispensing is unaffected and new entry is common. Where it was the sole
supplier, roughly a third of affected prescription molecules cease to be dispensed
altogether, replacement entry occurs for a small minority, and the rest of the therapeutic
class absorbs essentially none of the lost volume.

This matters for three reasons. First, it identifies supplier count, rather than shortage
status, as the operative resilience variable. Second, it shows that the loss is not a
transition cost: it persists for at least two years. Third, it contrasts directly with planned
exits. Prior work on Medicaid Drug Rebate Program terminations found that the market absorbs
most of the lost volume. Planned withdrawal transfers supply. Abrupt failure destroys it.

---

## 2. Methods

### 2.1 Data

Medicaid State Drug Utilization Data, published quarterly by the Centers for Medicare and
Medicaid Services, 2014Q1 to 2026Q1: 13 annual files, 5.7 GB, approximately 57 million
records covering 6.78 billion prescriptions between 2017 and 2025.

Two handling decisions materially affect results.

**National aggregate rows excluded.** SDUD contains state rows and a national aggregate row
coded 'XX'. Summing both double counts by approximately 1.99x. The aggregate rows are large,
rising from 274,082 records in 2017 to 320,609 in 2025. All analyses use state rows only.

**Suppressed cells treated as missing.** Suppression flags 48.9% to 52.3% of rows in every
year. Because suppression applies to very low counts, the suppressed share of volume is
small while the suppressed share of cells is about half. Suppressed cells are excluded from
aggregation, not imputed.

### 2.2 Molecule, class and product type

National Drug Codes were mapped to active ingredient, Established Pharmacologic Class and
product type using the FDA National Drug Code Directory product file combined with the
openFDA bulk NDC dataset. The latter is required because it retains discontinued products
the current directory omits. The combined crosswalk holds 136,099 unique labeler-product
keys and matches **76.7% of prescriptions to ingredient and 69.3% to pharmacologic class**.

**The main analysis is restricted to products typed HUMAN PRESCRIPTION DRUG.** An unrestricted
first pass produced larger effects, but inspection showed the affected set mixed clinically
significant drugs with over-the-counter products such as senna, psyllium and zinc oxide cream.
Restricting to prescription drugs roughly halves the estimated effect and is the specification
reported throughout.

### 2.3 Identifying abrupt exit

No public register of abrupt pharmaceutical manufacturer failure exists, so exits are
identified from dispensing. A labeler is classified as exiting in quarter t when its total
dispensing averaged at least 2,000 prescriptions per quarter over the preceding four quarters
and fell below 10% of that level across the four quarters from t. Detection uses the full
panel, including records unmatched to the crosswalk, so firm size is not understated.

This yields **105 exiting labelers** between 2016 and 2024.

**Validation.** The procedure recovers the 2023 collapse of Akorn Pharmaceuticals with no
external input. Labeler 17478 exits in 2023Q2 with 111 products; labeler 50383, Hi-Tech
Pharmacal, which Akorn owned, exits in 2023Q3 with 80 products. Akorn closed four
manufacturing facilities abruptly in February 2023 and recalled all in-date product in April
2023.

### 2.4 Treatment, exposure and controls

For each exit, the exiting firm's share of each affected ingredient is computed over the four
preceding quarters. Ingredients are assigned to their first exposure, giving **65 treated
prescription ingredients**, of which **29 are sole-supplier** cases at 95% share or above.
Bands are minor (under 35%), intermediate (35 to 95%) and sole supplier (95% and above).

Controls are **998 prescription ingredients** never exposed to a detected exit, with positive
dispensing in at least 40 quarters and mean dispensing of at least 400 prescriptions per
quarter.

### 2.5 Specification

Two outcomes are reported, because a single log specification is inadequate here.

**Extensive margin.** An indicator for whether mean dispensing in the six quarters after exit
falls below 2% of the six-quarter pre-exit mean. This captures complete cessation, which a log
specification cannot represent and which an earlier draft of this analysis silently dropped.

**Intensive margin.** Change in mean log(1+prescriptions) over the six quarters after exit
against the six before. The log(1+x) form retains zeros. A plain log specification excludes
any molecule that reached zero, which are precisely the most severe cases, and understates
the effect by roughly a factor of three.

Both are differenced against controls assigned placebo exit dates drawn from the empirical
distribution of true exit dates. **Inference is by permutation**, 500 to 600 resamples, not
asymptotic standard errors, because the sole-supplier band is small. Exact n is reported
everywhere.

---

## 3. Results

### 3.1 Main estimates

Prescription drugs only. Collapse is cessation of dispensing as defined above.

| exposure band | n | collapse, treated | collapse, control | p | intensive margin | change | p |
|---|---|---|---|---|---|---|---|
| minor, under 35% | 31 | 0% | 0% | 1.000 | +0.116 | +12.3% | 0.349 |
| intermediate, 35 to 95% | 5 | 0% | 0% | 1.000 | -0.842 | -56.9% | 0.0017 |
| **sole supplier, 95%+** | **26** | **38%** | **0%** | **0.002** | **-3.018** | **-95.1%** | **0.0017** |
| all treated | 62 | 16% | 0% | 0.002 | -1.275 | -72.1% | 0.0017 |

Minor-supplier exits produce no detectable loss and no cessation. Sole-supplier exits cause
complete cessation of dispensing for 38% of affected molecules, against zero of 998 controls.

### 3.2 Pre-trends and the restricted sample

Sole-supplier molecules display a positive pre-exit trend, mean slope +0.092 log points per
quarter against +0.013 for controls, though medians are closer at +0.019 and +0.008. The mean
is driven by a minority. 77% of sole-supplier molecules have pre-trend slopes within plus or
minus 0.10 log points per quarter.

Restricting to that flat-pre-trend subsample:

| band | n | collapse, treated vs control | p | intensive margin | change | p |
|---|---|---|---|---|---|---|
| minor | 25 | 0% vs 0% | 1.000 | +0.185 | +20.3% | 0.012 |
| **sole supplier** | **20** | **30% vs 0%** | **0.002** | **-2.360** | **-90.6%** | **0.002** |
| all treated | 50 | 12% vs 0% | 0.002 | -0.928 | -60.5% | 0.002 |

The result survives. The extensive margin is by construction immune to trend artefacts: a
molecule reaching literal zero is not an extrapolated trend.

### 3.3 Event-time path

Log(1+prescriptions) relative to the quarter before exit, sole-supplier band, n=29, zeros
retained. Figure 1: `fig1_event_time_firm_exit.png`.

| t-6 | t-4 | t-2 | t-1 | **t+0** | t+2 | t+4 | t+6 | t+8 |
|---|---|---|---|---|---|---|---|---|
| -1.273 | -0.708 | -0.041 | 0.000 | **-2.507** | -3.660 | -3.558 | -4.058 | -3.963 |

A discontinuity at the exit quarter, deepening over the following year, and no recovery
through eight quarters. The path worsens rather than reverts.

### 3.4 Replacement entry does not occur

| band | n | suppliers at t-1 | t+4 | t+8 | new firms by t+8 | share with any entry |
|---|---|---|---|---|---|---|
| minor | 54 | 8.69 | 9.17 | 8.63 | 2.65 | **85%** |
| intermediate | 12 | 3.25 | 2.92 | 2.08 | 1.33 | 67% |
| **sole supplier** | 43 | 1.05 | 0.63 | 0.60 | 0.37 | **16%** |

Where the failing firm was one of many, 85% of molecules see new entry within two years.
Where it was the only supplier, 16% do, and mean supplier count falls to 0.60 and stays there.

### 3.5 Therapeutic substitution does not occur

Log dispensing of all other ingredients in the same Established Pharmacologic Class:

| band | n | t+0 | t+2 | t+4 | t+6 | t+8 |
|---|---|---|---|---|---|---|
| minor | 47 | -0.075 | -0.038 | -0.033 | +0.010 | +0.055 |
| intermediate | 7 | +0.032 | +0.115 | +0.002 | -0.028 | -0.016 |
| sole supplier | 24 | -0.009 | +0.125 | -0.011 | +0.018 | +0.082 |

When a sole-supplier molecule loses most of its volume, the remainder of its class moves
between -0.01 and +0.08 log points. There is no offsetting increase.

### 3.6 Remaining supplier count determines recovery

All treated molecules, grouped by supplier count four quarters after exit:

| suppliers remaining | n | intensive margin | change |
|---|---|---|---|
| 1 | 15 | -0.722 | -51.4% |
| 2 to 3 | 8 | -0.097 | -9.2% |
| 4 or more | 44 | +0.199 | +22.0% |

Monotone. This is the paper's policy content: resilience is a function of how many suppliers
remain, not of the size or visibility of the failing firm.

### 3.7 Spending tracks volume

In the sole-supplier band, prescriptions fall 52.2% and Medicaid spending falls 50.8% on the
surviving-molecule subsample. There is no compensating price increase. The loss is borne as
reduced access, not higher expenditure.

### 3.8 Clinical composition

Sole-supplier prescription molecules affected include beclomethasone dipropionate inhalation
aerosol, the largest at 90,722 prescriptions per quarter before exit, lidocaine 5% patch,
collagenase for wound debridement, teriflunomide for multiple sclerosis, propylthiouracil,
goserelin, voxelotor for sickle cell disease and agalsidase beta for Fabry disease. Aggregate
pre-exit volume at risk across the unrestricted sole-supplier set is approximately 320,000
prescriptions per quarter. Median change was -100% and 68% lost more than half their volume.

### 3.9 Robustness

**Threshold invariance.** The 2,000 prescription detection threshold is arbitrary. Varying it
changes the sample substantially and the estimate negligibly.

| threshold | exits | sole-supplier molecules | effect t+4 | t+8 |
|---|---|---|---|---|
| 20,000 | 44 | 26 | -1.249 | -0.917 |
| 10,000 | 60 | 32 | -1.370 | -0.917 |
| 5,000 | 85 | 37 | -1.107 | -0.680 |
| 2,000 | 105 | 44 | -1.446 | -0.919 |

**Placebo in time.** A pseudo-exit eight quarters before the true exit yields +0.061 against a
true-event estimate of -0.203 in the pooled log specification: small and opposite in sign.

**Internal placebo.** The minor-exposure band is a within-design placebo. These molecules
experience a firm failure but lose no supply, and show zero cessation and no decline.

**Power.** The placebo distribution implies a minimum detectable effect of approximately 12%
at 80% power and 5% significance. Observed sole-supplier effects far exceed it.

---

## 4. Discussion

Three mechanisms were tested and all three point the same way. Dispensing collapses, nobody
enters, and nothing substitutes. The volume is destroyed rather than redirected.

The contrast with planned exit is the substantive contribution. Work on Medicaid Drug Rebate
Program terminations found the market absorbs the large majority of lost volume. Planned
withdrawal gives notice, leaves the firm operating, and transfers supply to competitors.
Abrupt failure does none of these. Treating the two as equivalent supply events, as shortage
monitoring implicitly does, understates the harm from the second.

The policy implication follows from section 3.6. Supplier count four quarters out predicts
recovery almost deterministically: four or more remaining suppliers and dispensing rises,
one remaining and it halves. Resilience policy that targets drugs already in shortage is
therefore late. The at-risk population is identifiable in advance from supplier counts in
public data, before any failure occurs.

Three limitations bound the interpretation.

**Generalisation.** Medicaid is not the national market. Whether commercial and Medicare
populations show the same pattern is an assumption, not a result here.

**Sample size.** The sole-supplier analytical sample is 20 to 29 molecules. Abrupt
sole-supplier failures are rare by nature. This is why inference is by permutation and why
exact n is reported throughout rather than relying on asymptotics.

**Exit cause is unidentified.** Exits are detected from dispensing, not from a register of
corporate failure, so bankruptcy, regulatory enforcement and voluntary withdrawal are not
separated. This is the most valuable extension and would sharpen policy attribution
considerably.

---

## Files

- `firm_exit_results_twopart.json` main estimates
- `firm_exit_results_flat_pretrend.json` pre-trend restricted
- `firm_exit_results_rx_only.json` log specification, prescription only
- `firm_exit_main_results.json` unrestricted first pass, superseded
- `fig1_event_time_firm_exit.png` Figure 1
- `Candidate_D_Firm_Exit_Validated.md` validation record
- `Feasibility_Power_Analysis_Verdict.md` why candidates A and B were rejected

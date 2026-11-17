# When the Last Supplier Leaves: Supplier Loss, Absent Market Repair, and Access in US Generic Drug Markets

Vasu Atmakuri (first author), Independent Researcher, Dallas, TX. ORCID 0009-0007-5955-2466.
Souseelya Kidambi (second author).
Draft of 17 November 2026. Every figure traces to a logged run on public data.

---

## 1. Introduction

Policy attention to pharmaceutical supply reliability concentrates on shortages: their
prediction, their causes, and the effectiveness of regulatory response. The market event that
produces many of them is less examined. US generic drug markets are concentrated, and many
drug-form markets are served by a single manufacturer. When that manufacturer stops supplying,
the interesting question is not whether supply is interrupted, which is immediate, but whether
the market repairs itself. Economic theory expects replacement entry. Clinical practice expects
therapeutic substitution. Neither has been tested at national scale.

The existing literature asks a different question. Work on generic market structure documents
entry and exit and relates supplier counts to prices. Work on firm behaviour explains why firms
leave. What happens to patients after a supplier leaves, and whether anyone replaces it, is not
established.

This paper tests both repair mechanisms directly using eleven years of national Medicaid
dispensing records. The finding is that repair largely does not happen, and that the operative
variable is the departing supplier's market share rather than the size or visibility of the
firm. Where the departing supplier held under 35% of a market, 0.8% of markets lose supply
entirely. Where it was the sole supplier, 54% do.

---

## 2. Methods

### 2.1 Data

Medicaid State Drug Utilization Data, published quarterly by CMS. The full series runs from
1991, and all 36 years were obtained (37 files, 12 GB), but the analysis window is 2016Q1 to
2026Q1 for a reason stated in 2.2.

Two handling decisions materially affect results.

**National aggregate rows excluded.** SDUD contains state rows and a national aggregate row
coded 'XX'. Summing both double counts by approximately 1.99x. The aggregate rows are large,
rising from 274,082 records in 2017 to 320,609 in 2025. All analyses use state rows only.

**Suppressed cells treated as missing.** Suppression flags 48.9% to 52.3% of rows in every
year. Suppression applies to very low counts, so the suppressed share of volume is small while
the suppressed share of cells is about half. Suppressed cells are excluded, not imputed.

### 2.2 Why the window starts in 2016

National Drug Codes were mapped to ingredient, dosage form, Established Pharmacologic Class and
prescription-versus-OTC status using the FDA National Drug Code Directory product file combined
with the openFDA bulk NDC dataset, which retains discontinued products the current directory
omits. The combined crosswalk holds 136,099 labeler-product keys.

Coverage is strongly time-dependent, because the FDA directory does not retain historical NDCs:

| year | 1993 | 1999 | 2005 | 2011 | 2014 | 2017 | 2020 | 2023 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| prescriptions matched | 6% | 15% | 20% | 42% | 49% | 63% | 82% | 93% | 100% |

Coverage first exceeds 60% in 2017. Extending the panel back therefore adds years but not
usable observations, and the pre-2016 data is not used. This is stated because it is a real
constraint on any study of this kind using SDUD with a current-vintage crosswalk.

**The analysis is restricted to products typed HUMAN PRESCRIPTION DRUG.** An unrestricted first
pass produced larger effects, but the affected set mixed clinically significant drugs with
over-the-counter products such as senna, psyllium and zinc oxide cream.

### 2.3 Market definition

The unit of analysis is the **ingredient by dosage-form market**, following the molecule-form
convention in the generic drug literature. Amoxicillin suspension and amoxicillin tablets are
distinct markets with distinct suppliers, and aggregating them conceals sole-supplier status.
Dosage forms are grouped into nine buckets (tablet, capsule, oral liquid, injectable, topical,
inhaled or spray, drops, rectal, other) so that label variants do not fragment markets.

This yields **3,258 markets** and 230,541 labeler-market-quarter observations.

### 2.4 Treatment: supplier loss and exposure intensity

A supplier-loss event occurs when a labeler supplying a market at a sustained rate of at least
200 prescriptions per quarter over four quarters falls below 5% of that rate. Exposure is the
departing supplier's share of the market over the four preceding quarters.

This yields **398 supplier-loss events**, of which 60 are sole-supplier (95% share or above).
After restricting to events with a complete pre and post window inside the data, 189 events
remain, including 39 sole-supplier markets and 24 with complete baselines.

**Edge exclusion matters.** An earlier version of this analysis allowed event windows to extend
past the end of the panel and filled the missing quarters with zeros, which manufactures
collapses. Events are now restricted to those with the full window inside the data.

Controls are **1,272 markets** never exposed to a supplier-loss event, with positive dispensing
in at least 34 of the window's quarters and mean dispensing of at least 400 prescriptions per
quarter.

### 2.5 Specification

**Baseline is quarters t-8 to t-5, not t-1.** Event-time paths show dispensing declining by
roughly one log point from t-4 to t-1: departing suppliers wind down before stopping. A
baseline immediately before the event is therefore already depressed, and using it overstates
the effect. The baseline is moved back four quarters to sit before the wind-down.

Two outcomes:

**Extensive margin (primary).** An indicator for whether mean dispensing over the six quarters
after the event falls below 2% of the baseline. This captures complete cessation of supply, is
immune to pre-trend contamination, and is the result the paper leads with.

**Intensive margin (secondary).** Change in mean log(1+prescriptions). The log(1+x) form retains
zeros; a plain log specification silently drops every market that reached zero, which are the
most severe cases, and understates the effect roughly threefold.

Both are differenced against controls assigned placebo event dates drawn from the empirical
distribution of true event dates. **Inference is by permutation** (600 resamples), not asymptotic
standard errors, because the sole-supplier band is small. Exact n is reported throughout.

---

## 3. Results

### 3.1 Supply loss rises sharply with the departing supplier's share

| exposure band | n | cessation rate | control | intensive margin | p |
|---|---|---|---|---|---|
| minor, under 35% | 128 | 0.8% | 0.2% | -8.2% | 0.158 |
| 35 to 65% | 12 | 0.0% | 0.2% | +14.4% | 0.243 |
| 65 to 95% | 9 | 0.0% | 0.2% | -11.3% | 0.305 |
| **sole supplier, 95%+** | **24** | **54.2%** | **0.2%** | **-98.9%** | **0.0017** |
| all events | 173 | 8.1% | 0.2% | -49.8% | 0.0017 |

Losing a minor supplier produces no detectable effect. Losing the sole supplier causes complete
cessation of dispensing in **54% of markets**, against 0.2% of 1,272 controls.

### 3.2 Robustness to safety withdrawals

A supplier that stops because its product was withdrawn for safety is not a supply-chain
failure. Ranitidine (NDMA, 2020) and varenicline (nitrosamine, 2021) are the clearest cases and
are among the largest events detected. FDA enforcement records (18,166 recalls) were used to
flag any sole-supplier market with a contemporaneous recall mentioning the ingredient.

| group | n | cessation rate | intensive margin | p |
|---|---|---|---|---|
| all sole-supplier | 24 | 54.2% | -99.0% | 0.0017 |
| recall-contemporaneous excluded | 11 | 54.5% | -98.4% | 0.0017 |
| recall-contemporaneous only | 13 | 53.8% | -99.3% | 0.0017 |
| minor exposure (placebo) | 128 | 0.8% | -12.3% | 0.023 |

**The two subgroups are indistinguishable.** Safety withdrawals do not drive the result, and the
screen's aggressiveness is therefore immaterial.

### 3.3 Replacement entry does not occur

| band | n | suppliers at t-1 | t+4 | t+6 | new firms by t+6 | share with any entry |
|---|---|---|---|---|---|---|
| minor, under 35% | 128 | 7.23 | 7.42 | 7.52 | 1.41 | **68%** |
| intermediate | 22 | 3.09 | 3.14 | 3.00 | 0.77 | 41% |
| **sole supplier** | 39 | 1.00 | 0.64 | 0.62 | 0.18 | **18%** |

Markets that lose one of several suppliers see entry in 68% of cases and their supplier count is
unchanged. Markets that lose their only supplier see entry in 18%, and the mean supplier count
falls to 0.62 and stays there.

### 3.4 Therapeutic substitution is partial at best

Log dispensing of all other markets in the same Established Pharmacologic Class:

| band | n | t+0 | t+2 | t+4 | t+6 |
|---|---|---|---|---|---|
| minor, under 35% | 113 | -0.023 | +0.012 | +0.012 | +0.030 |
| sole supplier | 29 | +0.053 | +0.108 | +0.103 | **+0.146** |

Class volume rises about 15% over six quarters after a sole-supplier loss. That is a real
substitution response, and it is far smaller than the roughly 99% decline in the affected
market. Most of the lost volume does not reappear within the class.

### 3.5 Markets affected, recall-contemporaneous cases excluded

| ingredient | form | event | before | after | suppliers after |
|---|---|---|---|---|---|
| 1.1% sodium fluoride dental cream | topical | 2023Q4 | 25,016 | 0 | 0 |
| terbinafine 250 mg | tablet | 2023Q3 | 21,215 | 300 | 1 |
| griseofulvin | oral liquid | 2023Q2 | 14,182 | 444 | 1 |
| vitamin-mineral omega-3 | capsule | 2021Q1 | 6,634 | 0 | 0 |
| elbasvir and grazoprevir | tablet | 2018Q2 | 5,661 | 329 | 1 |
| dorzolamide and timolol | oral liquid | 2023Q4 | 3,085 | 176 | 2 |
| pegfilgrastim-bmez | injectable | 2023Q4 | 2,877 | 39 | 1 |
| goserelin | other | 2021Q4 | 2,368 | 8 | 0 |
| lumacaftor and ivacaftor | tablet | 2021Q4 | 1,111 | 3 | 0 |
| estradiol and norethindrone | tablet | 2019Q2 | 678 | 4 | 0 |
| colesevelam | tablet | 2023Q1 | 578 | 0 | 0 |
| alcaftadine | oral liquid | 2022Q2 | 531 | 7 | 0 |

Approximately 98,000 prescriptions per quarter across 14 markets. The clinical range includes
hepatitis C therapy, cystic fibrosis therapy, an oncology implant, a neutropenia biosimilar,
glaucoma therapy and two systemic antifungals.

Two entries are anomalies worth naming: benztropine tablets (12,951 to 13,647) and alirocumab
(1,500 to 3,340) rose after the detected event. These are labeler reassignments rather than
supply loss, and they attenuate rather than inflate the estimates.

### 3.6 Price and spending

Spending tracks volume rather than price. Against controls, the sole-supplier band shows a
98.9% volume decline and a 99.7% spending decline. Among sole-supplier markets where supply did
not cease entirely (n=16), reimbursement per prescription fell 8.1%. The minor band shows a
15.1% decline per prescription.

There is no price spike. The harm from sole-source supplier loss is pure loss of access, not a
cost shock to the payer. This distinguishes the event from the shortage episodes that generate
price spikes in the sterile injectable literature, where supply contracts but does not stop.

### 3.7 Robustness

**Cessation threshold.** The 2% cessation threshold is a choice. The conclusion does not depend
on it, though the headline rate does:

| threshold | sole band (n=24) | control |
|---|---|---|
| 1% of baseline | 29.2% | 0.0% |
| 2% (reported) | 54.2% | 0.1% |
| 5% | 62.5% | 0.2% |
| 10% | 79.2% | 0.4% |
| 20% | 83.3% | 0.5% |

At every threshold the treated rate exceeds the control rate by two orders of magnitude. The
reported 54.2% is the middle of the range and the most conservative defensible choice.

**Statistical power.** The placebo distribution at n=24 has a standard deviation of 0.138 log
points, giving a minimum detectable effect of 47.2%. The observed effect is 32.7 standard
deviations from zero. The design is far better powered for an effect of this size than for a
moderate one, which is a limitation when interpreting the null results in the intermediate
bands.

**Pre-trend restriction.** Restricting sole-supplier markets to those with pre-event slopes
within plus or minus 0.15 log points per quarter leaves 10 markets with a 60% cessation rate and
an intensive margin of -98.7%.

**Suppliers remaining, and why this is not independent evidence.** Cessation is 100% where no
supplier remains (n=4), 50% where one remains (n=18), and 0% where two or more remain (n=2
within the sole band, n=152 overall). This gradient is reported for description only. The
cross-tabulation shows it is nearly collinear with exposure share by construction: 18 of 24
sole-supplier events leave exactly one supplier, and 111 of 128 minor-supplier events leave four
or more. It restates the main result in different units and is not a second, independent test.

One substantive observation survives that caveat, at n=18 and therefore tentatively. In the
cases where one supplier remained, that supplier had held under 5% of the market, and in half of
them it did not scale up to replace the departed volume. A fringe supplier's presence is
therefore weak protection, though the sample is too small to treat this as established.

**Internal placebo.** The minor-exposure band is a within-design placebo: these markets lose a
supplier but not their supply, and show a 0.8% cessation rate against 0.2% in controls.

**Threshold invariance in detection.** At the firm level, varying the exit-detection threshold
from 20,000 to 2,000 prescriptions per quarter changes the number of events from 44 to 105 and
the estimate negligibly (t+4 effect between -1.11 and -1.45 log points).

**Firm-level specification.** Defining treatment as whole-labeler collapse rather than
market-level supplier loss gives 105 firm exits and a consistent pattern. The market-level
definition is preferred because it is the economically relevant unit and yields more events.


---

## 4. Discussion

Three mechanisms were tested. Supply ceases in a majority of sole-supplier markets, replacement
entry occurs in 18% of them, and the therapeutic class absorbs around 15% of lost volume. The
loss is largely not redirected and largely not repaired within six quarters.

The policy content is in the gradient. Losing a supplier is harmless when others remain and
close to total when none do. Market concentration is observable in public data before any
failure occurs, so the at-risk set is identifiable in advance: it is the set of ingredient and
dosage-form markets with one meaningful supplier. Resilience policy keyed to shortage status is,
by construction, late, because it activates only once supply has already stopped.

The absence of a price response sharpens this. Payers see the event as a volume disappearance
rather than a cost increase, so the usual financial signal that prompts attention does not fire.
A market can lose its only supplier, fail to attract entry, and leave no trace in spending.

The contrast with planned exit is instructive. Prior work on Medicaid Drug Rebate Program
terminations found the market absorbs most lost volume. A planned withdrawal gives notice and
leaves the firm operating. A supplier that simply stops does neither.

Four limitations bound the interpretation.

**Generalisation.** Medicaid is not the national market. Whether commercial and Medicare
populations show the same pattern is an assumption here, not a result.

**Sample size.** The sole-supplier band is 24 to 39 markets depending on window requirements.
Losing one's only supplier is rare, which is the binding constraint on this design. The
consequence is asymmetric: the design is well powered to detect the large effect it finds (32.7
placebo standard deviations) and poorly powered in the intermediate bands, where the minimum
detectable effect is 47.2%. The nulls at 35 to 65% and 65 to 95% exposure should therefore be
read as uninformative rather than as evidence of no effect. Inference is by permutation and
exact n is reported throughout rather than relying on asymptotics.

**Cause of departure is only partly identified.** Recall-contemporaneous events can be flagged,
and doing so does not change the result. Bankruptcy and voluntary withdrawal cannot be
separated, because neither is available as structured public data at the firm-quarter level.

**Crosswalk vintage.** Coverage falls from 100% in 2026 to 6% in 1993, which confines any
SDUD study of this design to roughly the last decade unless historical NDC vintages are obtained.

---

## Files

- `firm_exit_FINAL_clean.json` safety-withdrawal screen, primary
- `firm_exit_FINAL_all.json` main, entry, substitution
- `firm_exit_results_FINAL_marketform.json` market-form specification
- `firm_exit_results_FINAL.json` ingredient-level specification
- `firm_exit_cause_split.json` firm-level cause split
- `firm_exit_FINAL_robustness.json` threshold sensitivity, supplier gradient, power
- `firm_exit_FINAL_spending.json` spending and price
- `figures/fig1_event_time_supplier_loss.png` Figure 1, 300 dpi
- `decisions/` candidates A and B, and why they were rejected

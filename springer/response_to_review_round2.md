# Response to second review

Second-round assessment was 7.5/10, major revision, with three P0 items. All three are addressed,
and one of them changed a headline number.

## P0.1 Reconcile the 121 / 122 / 132 sample sizes

The reviewer was right that "one eligibility rule" was not true in practice. Three different
cohorts were in use. The cause was a rule that picked the first event *inside the analysis
window*, which conditions event selection on the window.

The rule is now: take each market's **first detected event anywhere in the series**, then apply
window, baseline and follow-up conditions. A new Table 1 reports the full flow:

| Departing share | Detected | In window | Baseline complete | Post observed | No post |
|---|---|---|---|---|---|
| Under 35% | 128 | 84 | 83 | 83 | 0 |
| 35 to 65% | 20 | 8 | 8 | 8 | 0 |
| 65 to 95% | 15 | 8 | 7 | 7 | 0 |
| 95% or above | 55 | 28 | 28 | 20 | 8 |
| Total | 218 | 128 | 126 | 118 | 8 |

Analysis cohort is 118, used by every table. Entry was recomputed on it and changed: sole-supplier
entry is 20 percent, not 14. The replacement-ratio table carries 117 rather than 118 for a
mechanical reason now stated in the methods: one minority event has all four of its departing
labeler's baseline quarters suppressed, so the ratio's denominator is unobservable.

The abstract median of 1.47 was the value at exactly t+6 while Table 2 reported the window median
of 1.45. Both now read 1.45.

## P0.2 Suppression bound and fully unobserved follow-up

**The bound was wrong and the reviewer was right.** Suppression applies per NDC record, and a
labeler-market-quarter averages 2.72 records. The corrected bound is ten prescriptions per
suppressed record: median 10, ninetieth percentile 20, maximum 140 per labeler-product-quarter.
Aggregated to market level over the post-event window this averages 12.5 prescriptions per quarter
in the sole-supplier stratum, 0.26 percent of baseline, which is still far below the two percent
threshold.

**The unobserved-follow-up concern was correct and material.** Eight events had no observed
post-event quarter. All eight are sole-supplier, with baselines from 748 to 23,923 prescriptions
per quarter. Dropping them excluded the most complete disappearances. The outcome is now reported
as bounds:

- Lower bound, dropping them: 45.0 percent (95% CI 25.8 to 65.8), n=20
- Upper bound, counting them as below threshold: 60.7 percent (95% CI 42.4 to 76.4), n=28

The estimate moves up, not down. Both bounds sit far above the matched control rate.

## P0.3 Uncertainty and counterfactual for the primary outcome

Bootstrap 95 percent intervals on the median, 20,000 resamples:

| Departing share | n | Median R | 95% CI | IQR |
|---|---|---|---|---|
| Under 35% | 82 | 1.45 | 0.36 to 2.11 | -1.01 to 4.29 |
| 35 to 65% | 8 | 1.13 | 0.02 to 1.48 | 0.44 to 1.26 |
| 65 to 95% | 7 | 0.97 | 0.41 to 1.12 | 0.51 to 1.08 |
| 95% or above | 20 | 0.00 | 0.00 to 0.00 | 0.00 to 0.00 |

Difference in medians between extreme strata: 1.45 (95% CI 0.36 to 2.15); at or below zero in
0.04 percent of draws.

**Counterfactual drift**, which the reviewer correctly noted was missing: in matched never-exposed
markets the same quantity drifts by a median of 0.16 (95% CI -0.04 to 0.40). The minority stratum
sits well above that; the sole stratum sits below it.

## P1 items

**Event-level distribution (R4).** Of the 20 sole-supplier markets, 15 have a ratio of exactly
zero and 5 are positive at 0.08, 0.24, 0.25 and 0.67. Among those five the median is 0.24, so even
where someone steps in, roughly three quarters of the volume is not covered. The paper now states
plainly that the zero median and the low entry rate are two measurements of one phenomenon, not
independent corroboration, since other-labeler volume starts at zero in a single-labeler market.
What the ratio adds is magnitude. The figure also notes that quarters t+4 to t+6 lie entirely
outside the four-quarter detection window.

**Table baseline columns (R5).** The reviewer's implied-share arithmetic was right and the columns
were misleading: they were means across markets, so the pooled ratio was not the mean share. Both
columns are removed and replaced with median, CI, IQR and mean of the ratio itself.

**Safety withdrawals (R8).** Now split inside the primary 20, not the state panel. Flagged n=14 at
42.9 percent, unflagged n=6 at 50.0 percent, median ratio 0.00 in both. The flagging rule matches
on ingredient name and is deliberately over-inclusive, so the unflagged subgroup is the
conservative one and shows the same result. Leave-one-out gives 42.1 to 47.4 percent.

**Generic subset (R7).** 16 of 20 involve an ANDA or authorized-generic departing labeler at 37.5
percent; the other 4 at 75.0 percent. Median ratio 0.00 in both. The four are reported but not
interpreted.

**Matching protocol (R6).** The cap discrepancy was real: the sole-vs-sole comparison uses 25 per
treated market, not 20, giving 500 for 20 treated. Now stated, along with the fact that controls
are drawn per treated market and may recur across matched sets, so control observations are not
independent and are treated as a comparison distribution. The matched comparisons are now
described as strong descriptive associations rather than identified causal effects, with the
unmatched covariates named.

**"Pre-specified" (R10).** Corrected. No analysis plan was registered and the manuscript was
revised after inspecting data, so the outcome is described as designated, not pre-specified.

## P2 policy framing (R9)

**The reviewer was right and the claim was wrong.** Section 506C of the FD&C Act requires
notification of a permanent discontinuance or manufacturing interruption six months in advance, or
as soon as practicable, regardless of market share. Calling the apparatus necessarily reactive was
incorrect. The argument is now: notification is triggered by one firm's decision about one product
and carries no information about market exposure, whereas labeler concentration is a standing
property of every market. The two are complementary. The paper also now states that SDUD is
released quarterly and with a lag, so this is not a real-time monitor.

## Verification

Twenty-one automated consistency checks run against the compiled PDF, covering every reported
figure and every stratum sum. All pass. Strata sums: 218 detected, 128 in window, 118 cohort,
117 replacement table (one suppressed denominator, explained), 118 entry.

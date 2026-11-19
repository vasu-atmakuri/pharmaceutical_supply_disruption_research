# Response to reviewer

Thank you for your comments on this revision. Each point has been addressed through
additional analyses, reporting corrections, or an explicitly stated limitation. Below
we list what changed, and then set out our standing position on a small number of items
that have recurred, so that the remaining disagreements are explicit rather than
repeated.

We also report, in Section 0 below, four errors that we found ourselves in the course
of rebuilding the manuscript's reporting pipeline. None of them was raised in review.
We report them because two changed published quantities and one withdrew a claim.

The manuscript is now generated rather than transcribed. Every reported quantity in the
text, including the spelled-out counts, is a LaTeX macro emitted from the analysis
output files, and seven of the tables and the abstract are emitted whole, so a stale
number is not representable. Four scripts are run after every build and all pass on the
attached version:

- `audit_numbers.py` fails if any number in the source appears in no analysis output.
- `verify_manuscript.py` checks structure: that the abstract contains no hand-typed
  statistic, that every cross-reference and citation resolves, that every float is
  referenced, and that the PDF is newer than every source it was built from.
- `check_relationships.py` runs 53 assertions on relationships rather than presence:
  that band counts sum to their cohort, that figure sample sizes equal their table's,
  that the key-collapse distribution reconstructs both market counts, that the bound
  arithmetic closes, and that each generated table reproduces its source file.
- `check_determinism.py` re-runs every stochastic stage and requires byte-identical
  output.

---

## 0. Errors we found ourselves

**The bound on the sole-labeler collapse rate was wrong.** It was reported as 26.3 to
57.9 percent over 19 calendar-eligible exits. Computed from the panel, the
calendar-eligible population is 20 and seven of those are dropped because every
post-event quarter is suppressed, not six. The bound is 25.0 to 60.0 percent. The cause
was a hard-coded `5/19` in the script that collected reported numbers; that denominator
is now derived from the event flow and asserted against the cohort.

**We have withdrawn the claim that ingredient-level recall matching flagged fourteen of
twenty exits against one at firm level.** That pair of figures is not reproducible from
the FDA enforcement data. Recomputed with the window held fixed at the exit quarter, the
counts are six on a shared ingredient and three on the departing firm. At four quarters
either side both saturate at fifteen of twenty. The revised text reports these and makes
the stronger point they support: the window dominates the matching level, so a recall
flag defined on a generous window carries almost no information about cause. The
classification in Table 5 never rested on recall co-occurrence and is unchanged.

**The form-based bucketing yields eight buckets, not nine.** Counted from the
specification A panel.

**Two reporting defects.** The raw-to-corrected transition table printed a bootstrap
confidence bound in place of one market's corrected share, and listed the two ranitidine
exits as two markets when the normalisation makes them one. That table is now generated
from its source file, with the identity 20 minus 7 equals 13 asserted at emit time. A
paragraph was also duplicated verbatim in two sections; three floats were never
cross-referenced; four references were uncited. All are fixed.

**Two stages were not reproducible.** The matched-set confidence interval and the merge
validation count both moved between runs despite a fixed seed: array order determined
which elements the draws indexed, and `Counter.most_common` broke a tie by insertion
order, letting an empty substance set win. Both are fixed and the determinism check is
now part of the build. The matched-set interval is 15.1 to 61.7 points and the merge
agreement is 292 of 292 testable groups.

---

## 1. The near-sole event flow (your Section 2, P0)

You were right and the arithmetic was wrong. The flow is now computed from one
manifest and every stage is asserted against it:

| Stage | Previously reported | Computed |
|---|---|---|
| Detected exits with departing share at least 95% | 39 | **41** |
| Outside the event window | 20 | **21** |
| Inside the window | — | 20 |
| Fail the baseline rule | none | 0 |
| Every post-event quarter suppressed | 6 | **7** |
| Observed cohort | 13 | 13 |

21 + 0 + 7 + 13 = 41.
Three of the four previously reported numbers were wrong. Sections 2.5 and the
limitations are rewritten from macros emitted by the same computation, so the two
passages cannot disagree.

`results/near_sole_event_flow.csv` is the manifest you asked for: one row per
detected near-sole exit, with the stage at which it leaves the cohort, its departing
share, and for observed events its replacement ratio and collapse flag. Nine checks
assert the manifest against the flow, the flow against the cohort, and the manifest's
collapse count against the reported numerator.

We also flag a coincidence in the manuscript so it is not read as a further error: the
corrected panel has 20 near-sole exits inside the window, and the raw
convention's cohort separately contains 20 sole-labeler events.
Those two counts are equal by accident and are measured on different panels. The text
now says so.

## 2. The two 34.1% figures (your C7, P0)

You were right to ask. They are different quantities and we had used one number for
both. Computed separately, of 853M flagged prescriptions:

| Measure | Numerator | Share |
|---|---|---|
| Largest-component rule, whole raw market-quarters | 292M | **34.3%** |
| Volume allocated across all corrected components | 291M | **34.1%** |

Both appear in Table 4 with their numerators, and the text states that they are
different operations which agree only approximately.

## 3. Macro spacing (your C5, P0)

Entirely our defect and introduced by the generation change itself: TeX swallows the
space after a control word, so a macro defined without `\xspace` rendered
"292testable". There were 55 such joins. All 245 macros now carry `\xspace`, the count is zero,
and `verify_manuscript.py` reads the rendered PDF and fails on any digit joined to a
word. Our previous checks read extracted text for presence only, which is exactly why
they were blind to it.

## 4. Trace Elements (your C3, P0)

The limitation was outdated and is removed. In the final mapping, Trace Elements 4 and
Trace Elements 5 are separate normalised keys, and the two manufacturers' Trace
Elements 4 products that FDA records with different element sets are also separated by
the composition tie-break. No residual false merge survives this check. Section 3.3 now
states the order of operations explicitly: merge rule applied, substance data used to
identify wrong joins, rule changed, check re-run. The agreement is therefore
agreement after adjudication by the same field, which we say wherever we report it, and
Section 2.4 no longer calls that field an independent referee.

## 5. Missing-route handling (your C4, P0)

Both descriptions were wrong, in opposite directions. The actual rule: where
`ROUTENAME` is absent, a cascade on the form string is tried in the same order, and
only records matching none of its tests go to `other`. That residue is large, not
small: of 22,651 crosswalk records with no route, the cascade
classifies 5,520
(24.4%) and 17,131
(75.6%) reach `other`. We state this in the methods and have
rewritten the Table 9 caption to match. We also state why we keep them: dropping a
product because FDA did not populate one field would remove it from its market's
supplier count and could manufacture an apparent sole supplier, which is the error this
paper is about.

## 6. Formulation mismatch (your C2, P0)

Table 2 was right and Figure 1(a) was wrong: the corrected market is
`AMPHETAMINE,... | ORAL CAPSULE`. The figure had its own hard-coded label map with
"tablet" as a fallback string. There is now one shared label map that both the table
and the figure import, it raises an error on any key it does not cover, and a check
compares the rendered figure's labels against the table's, dosage form included.

## 7. Near-sole terminology (your C8)

Adopted. The share-defined stratum is called near-sole-labeler throughout the event
analysis, and we report the exact-labeler count you asked for:
12 of the 13 observed events had exactly
one active labeler across the four pre-exit quarters;
1 had a second labeler whose dispensing was small enough
that the departing share still rounded to 100 percent.

## 8. Overstated claims (your C9)

All three corrected. The recovery result is now described as suggestive and not
statistically established, in the abstract and the discussion. The matched comparison
reports 0.31% rather than "zero" everywhere. The
duplicate-key prevalence is stated as 11.5%
of route-aware raw market keys.

## 9. One more we found while doing this

`reclass_multi.py` was not reproducible. `max()` broke ties on component volume by
dictionary order, so the headline reclassification count moved between
15,743 and 15,744 across runs. Fixed with a
deterministic tie-break; the correct count is 15,743. The
determinism check now covers nine stages rather than four.

Your observation that our checks were still incomplete was correct, and the two
failures you found had a common shape: they compared numbers to a list of values rather
than to each other. The checks now assert relationships, including figure-to-table label
agreement and manifest-to-flow reconciliation, and one of them reads the rendered PDF
rather than its extracted text.

---

## 10. Changes made in earlier rounds

### The construction of the reclassification rate (your Section 2)

You were right that assigning a split raw market to its largest corrected component is
a modelling choice rather than a mapping, and that the headline should not rest on it.
Of the 58,905 raw near-sole market-quarters, those that split into more than one corrected
market. The manuscript now reports all three rules you proposed, plus a volume
allocation that requires no rule at all:

| Rule | Reclassified | Rate |
|---|---|---|
| Largest corrected component no longer near-sole | 15,743 | 26.7% |
| No component still near-sole | 9,549 | 16.2% |
| At least one component no longer near-sole | 17,004 | 28.9% |
| Volume allocated across all components | — | **34.1% of flagged dispensing** |

The count is bracketed between 16.2% and 28.9%. We now describe 26.7% as the rate
under the largest-component rule, not as an established false-positive rate, and we
treat the volume figure as the more robust of the two because it needs no assignment
choice. This is a better result than the one it replaces and we are grateful for it.

### The remaining false merge (your Section 3)

Fixed rather than documented. We added a composition tie-break: where the merge rule
would join keys for which FDA records different active-substance sets, the keys are
kept apart. This splits four groups, including Trace Elements 4, and brings agreement
with the substance data to **all 292 testable groups, with none contradicted**. We
state in the manuscript that this is not an independent test: the same composition
field was used to adjudicate the merges it contradicted, so the agreement reported is
agreement after adjudication. We have removed any claim that all absorbed keys are
proven duplicates; 15 groups remain untestable because substance names are missing for
every member, and that is stated. An RxNorm-adjudicated replication remains the right
external check and is named as the single most valuable extension.

### The outdated conclusion and the route-correction nuance (your Section 4)

Both corrected. The conclusion now gives 26.7% and 34.1% with the mapping rule named.
On the route correction, you are right that "essentially all the change" was too
strong: route correction accounts for 0.59 of the 4.17 percentage-point fall in
near-sole dispensing share, about 14%, while being close to neutral (−0.02 points) for
the exact single-labeler volume measure. The manuscript now states both rather than
generalising from the measure where the effect is smallest.

### OTC switches and Medicaid coverage (your C3)

You are correct and we have withdrawn the claim. A prescribed over-the-counter drug can
remain a covered outpatient drug under a state plan, so a switch does not necessarily
remove a product from Medicaid. The text now says only that the prescription product,
its NDC and the market it is counted in change, which is sufficient to produce the
observed exit without any supply interruption. Both events are labelled
regulatory-transition-associated exits and carry an ingredient-level evidence marker in
the appendix.

### Route coverage (your C5)

Route is populated for 83.4% of crosswalk *records*, which is the figure we reported,
but for **94.4% to 95.8% of dispensing volume in every year from 2016 to 2026**, with no
trend. The records lacking a route are small products. The fallback to the form string
therefore governs about five percent of volume rather than a sixth of it. Added, by year.

### Replacement-ratio influence (your C7)

Added, and it changed what we report. The minority band's median is stable under
trimming (1.77 → 1.73 → 1.58 → 1.47 removing the largest one, three and five), but the
mean falls from 19.29 to 11.32, 2.94 and -0.83, and the
volume-weighted ratio from 14.65 to 6.88, -5.43 and -12.08, changing sign. The five largest ratios are 625, 370, 273, 170 and 107. **We have
withdrawn the volume-weighted figure for that band**, since no stable value exists.

### Suppression scenario (your C9)

Reported alongside the primary estimate: the ten-prescription imputation moves one
market, taking 5 of 13 to 4 of 13, or 38.5% to 30.8%. Stated as a scenario, not a bound,
and kept separate from the missing-follow-up bounds of 25.0% to 60.0% (see Section 0).

### Market granularity (your C4)

We ran it. Adding strength gives 200,525 market-quarters, with 62.0% near-sole holding
19.96% of volume, against 55.7% and 10.54% at ingredient-and-route granularity. Finer
markets are mechanically more concentrated, so this is not a competing estimate of the
same quantity, and we now say so explicitly: the corrected figure is the concentration
of ingredient-and-route markets, not an estimate of true concentration at every
granularity. A reader who wants strength-level markets will measure more concentration,
not less.

### Repository

The repository was private. It is being made public before submission, and the claim in
the code-availability statement will be verified from a signed-out session.

---

## 2. Standing positions on recurring items

These have each been raised more than once. We state our position so the disagreement,
where there is one, is on the record.

**RxNorm validation.** We agree this is the strongest available check and we have not
done it. The web service is unreachable from our analysis environment and the offline
release requires a UMLS account, which is free but takes several days to approve. We
have not represented the FDA substance check as equivalent: the manuscript states that
both fields come from the same product-listing system and that agreement between them
is weaker evidence than an external terminology would provide. We would rather ship
with that limitation stated than imply a validation we did not perform. If the journal
requires it before review we will obtain the licence and add it.

**Strength-level market definitions.** We have now run this and report it, but we will
not adopt it as the primary specification. The paper's thesis is that market keys built
from unnormalised free text fragment single markets; defining markets at strength level
multiplies that fragmentation by a factor of more than two. The comparison belongs in
robustness, which is where it now sits.

**The matched-control comparison.** We agree with you entirely and have acted on it by
demotion rather than by engineering. Thirteen treated events will not support a
defensible causal design under any control construction. The comparison is labelled
descriptive and secondary, the forward-looking eligibility rule is disclosed rather than
defended, and the control reuse is quantified in the text (325 observations from 60
distinct markets, one appearing in all thirteen sets). We do not intend to expand it
further, and we would rather it were read as a descriptive contrast than as an estimate.

**The recovery and verified-disruption analyses.** We agree these cannot carry general
conclusions and have not asked them to. Three observations from two episodes are
reported as a case-based illustration. The log-rank result of p = 0.056 is described as
suggestive and not established, and Figure 3 now carries confidence bands that overlap
across the whole follow-up, which makes the point visually. Our only claim from this
material is negative: the data do not support the statement that sole-supplier markets
fail to replace lost volume after a documented supply disruption.

**The manufacturing-establishment analysis.** We accept it is supporting context rather
than an established contribution, and the manuscript labels it that way. Current
listings do not establish historical production sites. Reconstructing them is a separate
study.

---

## 3. What we believe the paper now establishes, and what it does not

**Establishes.** That the standard ingredient-by-dosage-form market definition, applied
to public Medicaid dispensing data, contains two measurement defects; that correcting
them changes the national picture materially, moving dispensing in near-sole markets
from 14.71% to 10.54% and reclassifying between 16.2% and 28.9% of apparent near-sole
market-quarters carrying 34.1% of flagged volume; that seven of twenty apparent
sole-labeler exits are not sole-labeler exits; and that three of the thirteen that
survive are regulatory actions rather than supply failures.

**Does not establish.** That the corrected definition is the clinically correct one at
every granularity; that the reclassification rate is an independently adjudicated
false-positive rate; that concentration causes dispensing loss; or anything general about
recovery after supply disruptions.

We would welcome the paper being assessed on the first list.

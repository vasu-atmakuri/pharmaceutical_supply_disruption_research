# Response to the reviewer

We thank the reviewer for a close and useful reading. Every comment is addressed below, in the
order given, with the section, table or file in the revised manuscript where the change appears.
Where we have not done what was asked, we say so and give the reason.

Two things changed in how we work rather than in the text. First, a new check,
`check_literals.py`, requires every digit in the body prose to be a generated macro or to appear
on a short allowlist with the reason it is fixed by the paper's design; it exists because this
review found two numbers that were right in the results and wrong in the sentence. Second, the
round-by-round development record that previously formed most of this letter has moved to
`decisions/review_history.md` in the repository, so this document can be what it should be: a
response to the comments.

A note on the repository, since it bears on several comments. The corrected detector, the
updated README and the new scripts were committed locally but had not been pushed when the
reviewer inspected the public branch. They are pushed now, and the build records the commit it
ran from in `results/build_provenance.json`, which `check_released_files.py` requires to match
`HEAD`. The paper's code-availability statement cites that file, so the version a reader clones
is the version the paper describes.

## 0. One correction we made after this revision was drafted

While clearing disk space we found that the product-to-market crosswalk was not
reproducible, and fixing it moved some descriptive counts. We report it here rather than let
the reviewer find that a rerun does not reproduce the previous PDF.

A product code listed twice in the source data, once in FDA's NDC directory and once in the
openFDA listing, was resolved with SQL's `any_value`, which picks an arbitrary row. With
parallel aggregation the choice varied between runs, so a product code with two different
recorded routes could land in either market from one build to the next. The crosswalk now picks
one listing per product code by a total order that prefers FDA's own directory, so the result is
fixed and every field of a product comes from the same listing instead of being mixed across
listings. Two consecutive builds now produce identical crosswalk content.

Preferring FDA's directory also recovers routes that the openFDA listing leaves blank, which is
an improvement rather than a side effect. What moved:

| | Before | After |
|---|---|---|
| Raw ingredient-and-route keys | 3,295 | 3,294 |
| Markets after normalisation | 2,916 | 2,915 |
| Dispensing volume with an explicit route, by year | 94.4 to 95.8% | 98.4 to 99.0% |
| Market-quarters at strength granularity | 200,534 | 193,885 |
| Near-sole volume at strength granularity | 19.96% | 1657.00% |

Nothing in the paper's findings moves. The number of absorbed duplicate keys is still 379 the
national near-sole dispensing share still falls from 14.71 to 10.54 percent, the observed cohort
is still 19 events with 8 collapses, and every event-level result, stratum and detector count is
unchanged. The affected quantities are descriptive counts and one sensitivity, and the
sensitivity moves in the direction that makes the strength-level contrast smaller.

---

## 1. The replacement subgroups in Section 3.8 were wrong

Accepted in full, and the reviewer's recomputation is correct.

The paragraph attributed the eleven-event result to the removal of the withdrawal alone, and
then again to the removal of the withdrawal and the transitions. Both were wrong. The failure is
worth naming because no check could see it: the macro was correct and the sentence attached it
to the wrong population, so every number in the paragraph traced to a real analysis output.

The exclusions are now six named populations, each computed on its own sample in
`scripts/cause_strata.py`, tabulated in Table 9, and cited from the prose by name:

<!-- GENERATED:ladder -->
| Population | Events | Median R | Collapsed |
|---|---|---|---|
| Every observed near-sole exit | 19 | 0.00 | 8 |
| Excluding the market-wide withdrawal | 18 | 0.00 | 7 |
| Excluding the withdrawal and the three transitions | 15 | 0.08 | 4 |
| Excluding only market-wide or product-and-firm explanations | 15 | 0.00 | 5 |
| Excluding every alternative-explanation class | 11 | 0.08 | 2 |
| Documented supply disruptions only | 2 | 0.47 | 0 |
<!-- END:ladder -->

The fourth row is the conservative exclusion the reviewer asked for under C4: it removes only
the alternative explanations whose record is market-wide or names both the firm and the
formulation, and leaves the ingredient-level transitions and the misspelled keys in. It still
sits below the pooled rate.

Section 3.8 and Table 9 are rewritten around these rows.

## 2. The limitations contradicted the event flow on baseline eligibility

Accepted. Section 4.1 said no in-window exit failed the baseline requirement where Table 2
reports one. The sentence now cites the same macro as the table and says that the baseline rule
removes one of the forty-four, so relaxing it would not materially enlarge the cohort.

## 3. The recovery cohort and the analysis cohort are now reconciled

Accepted, and this was the most useful comment in the review. The reviewer identified the cause
correctly from the public script: the two cohorts have different observation requirements.

The analysis cohort requires an observed market quarter within t+1 to t+6, because its outcome
is the mean over those six quarters. Recovery requires no such quarter, because its outcome is
the time from a market's own first crossing to its first restoration and both can fall later; it
requires instead that the panel extend twelve quarters past the exit. Neither is a subset of the
other. Section 3.9 now gives the crosswalk in both directions:

<!-- GENERATED:crosswalk -->
| | Markets |
|---|---|
| In both cohorts | 105 of 108 |
| In the recovery cohort only | 3 |
| Near-sole in both | 17 |
| Near-sole in the analysis cohort only, panel too short here | 2 |
| Near-sole in the recovery cohort only, no observed quarter in the first six | 3 |
<!-- END:crosswalk -->

That is the whole of the difference between twenty and nineteen.

Because the three extra markets are all near-sole, and so could flatter the comparison, we
repeat the test on the 105 markets the two cohorts share. At the 90 percent threshold it gives
p = 0.002 on fifteen near-sole and forty minority-loss markets that cross, against p = 0.002 on
the full cohort. At 50 percent it gives p = 0.271 against p = 0.188. The result does not depend
on the markets the analysis cohort excludes.

`results/recovery_event_manifest.csv` is the file the reviewer asked for under C9: one row per
market per threshold, with the event quarter, the quarter of first crossing, the quarter of
restoration where there is one, the censoring indicator, the time at risk and a flag for
membership of the analysis cohort. The log-rank tests and the Kaplan-Meier curves in Figure 3
can be reproduced from it directly, without rebuilding the panel.

## 4. The interpretation of the cause-stratified collapse rates (C4)

Accepted. The pooled-to-excluded difference is now described as the sensitivity of the observed
collapse rate to removing specified event classes, not as a measure of the cost of failing to
audit causes, and Table 9's caption states that its rows are six descriptions of six samples
rather than six estimates of one quantity. The conservative exclusion in row four is reported
alongside, as recommended.

## 5. The strength of the regulatory attributions (C5)

Accepted, and applied from the abstract through the conclusion rather than only in the methods.

Three specific changes. The prescription-to-over-the-counter transitions are described as
exits that a documented regulatory action overlaps on ingredient-level evidence, with no
firm-level record of why the departing generic labeler left; the appendix link column already
said so and the discussion now does too. The discussion no longer says that dispensing simply
moves off the Medicaid benefit: a prescribed over-the-counter product can remain covered, so
what the switch changes is the ordinary route by which a product reaches a patient and is
reimbursed rather than eligibility as such. The limitations paragraph on the rebate-programme
withdrawal now carries the same qualification as the methods: leaving the programme removes the
basis for ordinary federal matching and so for ordinary coverage, states retain discretion, and
at least one continued to cover the product in specified circumstances.

## 6. The normalisation validation (C6)

Partly accepted.

The lower-bound claim is qualified where it is made. It now carries both limits explicitly:
fifteen merge groups have no structured substance set for any member, so neither direction of
the check reaches them; and products that share a substance set and a route can still differ in
strength, release characteristics or formulation, which this check cannot see. What the check
establishes is that the keys it merged name the same active substances, not that every merged
group is one market in a clinical sense.

We have not done the independently adjudicated validation sample. It is the right experiment and
we say so in the limitations; RxNorm requires a UMLS account whose approval we did not obtain in
time for this revision. We would rather ship with the limitation stated than imply a validation
we did not perform.

The NDC-level mapping for the trace-element products is a reasonable request and we have not
added the appendix table for it. The composition tie-break is implemented on the substance set
rather than on the raw key, which is why the two firms' Trace Elements 4 products with different
element sets end up in different keys; the mechanism is described in Section 2.3 and its
consequence is reported against us in Section 3.4. A product-level demonstration would be
better and we will add it if the editor wants it.

## 7. The market definition and substitutability (C7)

Accepted. Section 2.3 no longer claims that strengths share a production line or substitute in
dispensing. It states that strength is excluded to match the convention the paper is testing,
that FDA's framework treats strength as a product characteristic and establishes bioequivalence
per strength, and that the key is therefore a specified administrative market definition rather
than a validated measure of clinical substitutability. The strength-level specification stays in
robustness, where it measures what the choice costs.

## 8. Suppression and the dense grid (C8)

Accepted, and tested rather than argued.

The detector reads a quarter absent from the data as zero. We now report what happens under
other readings. Replacing every absent quarter with five prescriptions leaves 423 events and 72
near-sole exits; replacing it with ten, which is the most a withheld quarter can hold under a
threshold of eleven, leaves 408 and 68. The published cohort does not move under any of the
three: the observed near-sole cohort is 19 events with 8 collapses whether an absent quarter is
read as zero, five or ten. The assumption moves the detected count by about six percent at its
most extreme and the reported cohort not at all. This is in Section 3.13.

On the persistence window: of the 433 events, 154 have the full twelve quarters and 279 are
judged on a shorter one; within the near-sole candidates, 38 of 72 have the full window.
Restricting the detector to events it can fully evaluate leaves 154 events, which is now
reported rather than described. We keep the truncated events in the main specification because
the bias is one-sided, a short window can only fail to see a return and so can only admit an
event a longer window would remove, and because dropping two thirds of the events to avoid a
one-sided bias costs more than it buys.

## 9. What the recovery analysis conditions on (C9)

Accepted. The comparison is among markets that crossed the threshold, and crossing is itself
related to concentration: eighteen of twenty near-sole markets cross below 90 percent against
forty of seventy-seven minority-loss markets. Section 3.9 states the comparison narrowly, as
time to restoration among markets that crossed, and not as an effect of concentration on
recovery across all markets. The manifest named under comment 3 above is the reproducibility
file requested here.

## 10. The typo-corrected sensitivity on exit outcomes (C10)

Accepted. The sensitivity now reports what the correction does to the published outcome instead
of leaving it to be inferred: the observed cohort becomes seventeen events and the collapse
count seven, a rate of 41.2 percent against 42.1. The reviewer's arithmetic was right. This is
in Section 3.13 and computed by `scripts/typo_sensitivity.py`.

## 11. Source identifiers in the evidence appendix

Accepted, and the reviewer is right that our reason for omitting links was a bad trade for a
paper about reproducibility. `results/event_cause_classification.csv` now carries, for each
declared event, the issuing authority, the document's exact title, its date, its kind, the
product codes where the record names them, a URL where we have retrieved and read one, and a
flag saying whether the citation was verified that way. Three citations carry verified URLs; the
rest are identified by issuer, exact title and date, and are flagged as unverified rather than
presented as checked.

## 12. The smaller items

| Item | Change |
|---|---|
| "one further events" | The noun now agrees with the count, which is generated |
| "10.54-level concentration" | Replaced with the two measures stated plainly |
| R = 1 described as replacing the departed volume | Now stated as net aggregate growth equal to the departing labeler's baseline, explicitly not product-for-product replacement |
| Recovery described as suggestive in the letter | This letter is new; the manuscript, Figure 3 and the discussion all describe the 90 percent comparison as significant under the test performed, with its three qualifications |
| Response letter organised around our iteration | Reorganised around the comments; the history is now `decisions/review_history.md` |

## 13. What we have not done

Three of the reviewer's suggestions are not in this revision, and we would rather say so than
imply otherwise.

The independently adjudicated normalisation sample, for the reason in comment 6. The
controlled-missingness experiment that would deliberately suppress observations from known
continuous series and measure detector precision and recall: we agree it would turn the
detector work into a standalone methodological contribution, and it is the first thing we would
add, but it is a second paper's worth of work rather than a revision. And the
monitoring-priority benchmark, for the same reason.

## 14. What we believe the paper establishes, and what it does not

**Establishes.** That the standard ingredient-by-dosage-form market definition, applied to
public Medicaid dispensing data, contains two measurement defects; that correcting them moves
dispensing in near-sole markets from 14.71 to 10.54 percent and reclassifies between 16.2 and
28.8 percent of apparent near-sole market-quarters carrying 34.3 percent of flagged volume; that
9 of 26 apparent sole-labeler exits are not sole-labeler exits; and that of the 19 the corrected
panel observes, 2 are a documented supply disruption, 8 are explained by something that is not a
supply failure, 5 have supply continued by another labeler, and 4 are undetermined.

It also establishes a methodological point we did not set out to make: an event detector built
on administrative dispensing data has to be tested against the case where the series stops, not
only against the case where it falls.

**Does not establish.** That the corrected definition is the clinically correct one at every
granularity; that the reclassification rate is an independently adjudicated false-positive rate;
that concentration causes dispensing loss; that the collapse rates across the exclusion ladder
are comparable causal estimates; or anything general about recovery after supply disruptions
from two events in one episode.

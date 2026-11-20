# Review and revision history

This is a development log, not a journal response. It records, round by round, what each
internal review found, what we changed, and what we declined to change and why. We keep it in
the repository because the reasoning behind a correction is worth more than the correction, and
because several of the pipeline's checks exist only because a specific defect got through.

**Figures in this file are as of the round that discusses them and may be superseded.** The
current numbers are in the manuscript, which generates every one of them, and in
`results/`. Nothing here should be read as the paper's present claims. The formal response to
the reviewer is `springer/response_to_reviewer.md`, which is organised around the comments
rather than around our own iteration.

---

## 0. You found four numbers we shipped wrong, and you were right about all four

Before anything else: your independent reconciliation of the two CSVs matches our pipeline
exactly, including the per-class collapse split, so we are reading the same data. The four
inconsistencies you identified were real and are fixed. We describe each one and what let it
through, because the mechanism matters more than the correction.

**The collapse rate.** Table 7's collapse column was a literal in the table generator,
`coll="38.5%" if k=="sole" else "0.0%"`, from a thirteen-event cohort. A generated table with a
hard-coded cell is worse than a typed table, because it looks generated. The collapse rate is
now computed per band by the stage that computes the bands: 42.1 percent in the near-sole band,
and 0.9 percent in the minority band, which was also not the 0.0 percent the table asserted.

**The seventeen-event sentences.** Sections 3.5 and 3.6 cited `\nRemainSole`, which is the raw
convention's sole count less the reclassified, 26 less 9, and not the corrected panel's observed
cohort of 19. The macro was defined correctly and used in the wrong sentences, so every check
that verifies a macro against its source passed. The treated-event count, the collapse
numerator, the matched-set count and the control-reuse figures now come from the matched
analysis's own output, and the 325 control observations you flagged were a literal, now 475.

**The recovery interpretation.** You are right that p = 0.002 cannot be described as not
established. The abstract, Section 3.9, Figure 3's caption and the discussion now describe the
90 percent comparison as significant under the test performed, with three qualifications stated
in place of the previous hedge: it is one of two thresholds tested, so the nominal level
overstates the evidence; it compares 20 markets with 77; and the design conditions on a detected
exit, so it is an association and not an effect. We also adopted your point about the bands: the
caption now says that overlapping pointwise intervals do not contradict a log-rank statistic
computed over the whole follow-up.

**A duplicated paragraph and a false claim inside it.** The recall-matching paragraph appeared
twice in Section 3.4, and it said the matching level "roughly doubles" the count when the
figures are 7 and 6. The duplicate is removed and the claim now says what the numbers say: the
matching level barely changes the count, the window changes everything, and at one quarter
either side the ordering reverses.

**What we have added as a result.** We are adding a check that would have caught the first and
second of these: the manuscript's prose is now scanned for literal numbers, and a literal that
is not on a short declared allowlist fails the build. Our checks verified that every number
traces to an analysis output and that every macro matched its source. Neither asks the question
your review asked, which is whether the right macro is in the sentence.

---

## 0a. The cause-specific collapse table, which is your recommendation and is now in the paper

You were right that this is the more revealing cut, and we have made it a results subsection
with its own table rather than a remark. Our computation reproduces yours exactly:

| Class | Events | Collapsed |
|---|---|---|
| Documented supply disruption | 2 | 0 |
| Market-wide regulatory withdrawal | 1 | 1 |
| Regulatory transition | 3 | 3 |
| Medicaid rebate withdrawal | 1 | 1 |
| Marketing-rights transfer | 1 | 0 |
| Measurement artefact | 2 | 1 |
| Supply continued by another labeler | 5 | 0 |
| Undetermined | 4 | 2 |
| **All observed exits** | **19** | **8 (42.1%)** |
| **Excluding the explained classes** | **11** | **2 (18.2%)** |
| **Documented supply disruptions only** | **2** | **0** |

The paper now states the three figures as three populations rather than three estimates of one
rate, says that the 18.2 percent is still not shortage-specific because the eleven include five
continued-supply and four undetermined exits, and draws the conclusion you point at: the gap
between 42.1 and 18.2 percent is the measurable cost of not auditing causes. We have kept the
two claims you separate explicitly separate in the discussion and the conclusion.

---

## 0b. The three sensitivities you asked for

**The two misspellings, corrected.** `scripts/typo_sensitivity.py` applies both corrections to
the panel keys, re-aggregates, and reruns the detector and the concentration measure. The
near-sole dispensing share moves from 10.54 to 10.52 percent, the market count from 2,916 to
2,914, and the detected near-sole exits from 72 to 70, which are the two artefact events and
nothing else. We report it as a sensitivity and leave the main specification unchanged, because
no rule available to the normalisation identifies a typing error in an ingredient name: a rule
that merged near-identical strings would merge genuinely different drugs with similar names,
which is a worse error than the one it fixes. The result is reassuring rather than otherwise,
and we would not have known that without running it.

**The persistence window's follow-up.** You are right that an event after 2023Q1 cannot have
twelve post-event quarters in a panel ending 2026Q1. 154 of the 433 events have the full window
and 279 do not; within the near-sole subset the split is 38 of 72. The Methods now state the
split and the direction of the bias, which is one-sided: a shorter window can only fail to see a
return, so truncation can admit an event a full window would have removed and never the
reverse. We state the split rather than restricting the panel, because restricting it would
discard the recent exits that any monitoring use of these data cares most about.

**Historical firm identity.** Your Viatris example is correct and the name is from the current
FDA labeler file. Table 6's caption now says so explicitly: names are the current FDA labeler
name for the NDC labeler code, not necessarily the entity that held the code at the time, and
the classification is keyed on the code, the market and the quarter and never on the displayed
name.

---

## 0c. Two attributions made more exact, as you asked

**TerSera and Zoladex.** We have softened the claim. The paper now says that leaving the rebate
programme removes the basis for ordinary Medicaid coverage and federal matching, that this is
not a blanket prohibition, and that states retain discretion with at least one publishing terms
for continued coverage in specified circumstances. What the record establishes is that the
ordinary reimbursement route closed on a known date, which is all the argument needs.

**Sanofi, Regeneron and the four-quarter gap.** The effective date is 2020Q2 and the detected
exit is 2021Q2, four quarters later, and the paper now says so and says why that does not undo
the classification: a transfer works through inventory, contracting and formulary timelines
rather than on its effective date, and the classification rests on the successor dispensing in
this market afterwards as much as on the announcement. We have stopped short of calling it a
same-quarter cause.

**American Regent.** We agree and have not changed the wording, which already reports this case
against our own method rather than as a clean non-supply event: the approved successors dispense
in the panel, but our composition tie-break holds them in a sibling key, so a product-generation
change reads as an exit with no replacement.

---

## 0d. The repository

The commits were local when you inspected it. That is our error in sequencing, not a
discrepancy in the work, and the README you saw was the one your previous review flagged. The
checks now include one that asserts the README's title, headline counts, stage and check counts
and every number in it against the analysis outputs, and the manuscript's own check count is a
macro, which is why three documents could previously quote six, eight and nine. We will pin the
submission to a public commit identifier as you ask.

---

## 1. What testing the thirteenth-round P0 uncovered

**Your window comment was right, and it was the smaller of two defects.** You observed that the
event windows were implemented with SQL `ROWS` frames while the manuscript defines them in
calendar quarters. That is correct: 13.1 percent of labeler-market series have at least one
missing quarter, so for those the window was not four quarters wide. Fixing it moved the event
count from 282 to 292.

Testing the fix exposed something worse in the same code. A labeler that stops dispensing
altogether has no records after its exit, so its post-event average was null, the comparison was
null, and the event never fired. The detector could only see labelers that kept dispensing a
little. It was blind to the exits the paper is about. We now evaluate the detector on a dense
calendar grid running from each series' first appearance to the end of the panel, with an absent
quarter read as zero dispensing, which is what absence means in these data. We count 66
labeler-market series that stop at least four quarters before the panel ends with a final
four-quarter mean of 200 prescriptions or more and that the previous detector never reported.

Fixing that raised the event count from 292 to 500, and inspecting the new events exposed a
third issue: 67 of the 500 were labelers whose dispensing resumed later, which is a suppression
gap or a short interruption rather than an exit. We therefore added a persistence requirement,
that the labeler not return to half its own baseline at any quarter from four to twelve after
the event. That leaves 433 events, which is the specification the paper now uses. All four
counts are in Table 4 of the manuscript, computed by `scripts/detector_variants.py`, which
refuses to write its output unless the last row agrees with the panel's own recorded total.

**What the correction did to the results.** The observed near-sole cohort grew from 13 events to
19. The matched-set interval widened from its previous value to 20.6 to 63.2 points. The
recovery log-rank at the 90 percent threshold improved from p = 0.056 to p = 0.002, which we
previously reported as suggestive and now report as established at that threshold while still
not established at 50 percent. Against us: the larger cohort let us audit six more events, and
the audit found three mechanisms we had not described, one of which is a defect in our own
method. Section 2 below sets them out.

**Four figures in the manuscript were stale and are corrected.** The abstract and the
discussion both gave 0.24 as the median replacement ratio among documented supply disruptions;
the current value is 0.47. `audit_numbers.py` had not caught it because 0.24 is a real value in
the results, the varenicline ratio in Table 5, so the number was traceable while being the wrong
number in its sentence. The crossing comparison cited eight of 58 minority markets when the
recovery cohort now holds 77; that cohort's own band sizes are now written by the stage that
computes it, so the manuscript cannot pair a count with a denominator from a different cohort.
The conclusion said three events from two episodes where there are two from one. The evidence
appendix was typed against the thirteen-event cohort and is now generated from its source file.

**Three figures from the last round carry forward, recomputed on the new cohort.** The bound on
the near-sole collapse rate is computed from the event flow rather than a hard-coded
denominator: 43 calendar-eligible exits, 24 of them dropped because every post-event quarter is
suppressed. The bound is 18.6 to 74.4 percent, and we continue to report the complete-case rate
and the bound separately rather than collapsing them into one number.
The matched-set interval is 20.6 to 63.2 points.
Against FDA substance data the merge agreement is 292 of 292 testable groups, after the
adjudication the manuscript describes, and we continue to state that this is not an independent
test.

---

## 2. The near-sole event flow, recomputed

The flow is computed from one manifest and every stage is asserted against it. Under the
corrected detector:

| Stage | Count |
|---|---|
| Detected exits with departing share at least 95% | 72 |
| Outside the event window | 28 |
| Inside the window | 44 |
| Fail the baseline rule | 1 |
| Every post-event quarter suppressed | 24 |
| Observed cohort | 19 |

28 + 44 = 72, and 1 + 24 + 19 = 44.

`results/near_sole_event_flow.csv` is the manifest you asked for: one row per detected near-sole
exit, with the stage at which it leaves the cohort, its departing share, and for observed events
its replacement ratio and collapse flag.

Two counts in the paper are close and we now say explicitly that they are not the same
quantity. The corrected panel has 44 near-sole exits inside the window. The raw convention's
cohort separately contains 26 sole-labeler events, of which 9 are reclassified by the
corrections, leaving 17 where the corrected panel's own detector finds 19. The gap of 2 is
itself a result: merging duplicate keys can make a market near-sole that the raw convention
never flagged, and can move an event quarter. We report both counts and the gap rather than
forcing an identity between them, and the relationship check now asserts the gap is small and
cited rather than asserting an equality that does not hold.

---

## 3. What the nineteen observed exits actually are

The audit is the part of the paper we would most like read, and the larger cohort changed it.
Of the 19 near-sole-labeler exits the corrected panel observes:

| Class | Events | What the record shows |
|---|---|---|
| Documented supply disruption | 2 | One recall episode affecting two formulations |
| Market-wide regulatory withdrawal | 1 | Every labeler asked to leave at once |
| Regulatory transition | 3 | Two prescription-to-over-the-counter switches and one product-generation change |
| Medicaid rebate withdrawal | 1 | Firm left the rebate programme; product still marketed |
| Marketing-rights transfer | 1 | Rights moved to the originator; supply continued |
| Measurement artefact | 2 | The ingredient string is a misspelling of a multi-supplier market |
| Supply continued by another labeler | 5 | A labeler absent before the exit supplies the market afterwards |
| Undetermined | 4 | No record found for this firm and period |

Three of these are new in this round and two of the three work against claims we previously
made.

**The rebate-programme withdrawal.** One firm withdrew from the Medicaid Drug Rebate Program
effective 1 October 2021, after which state programmes stopped covering its products while the
product itself remained FDA-approved and marketed. In the previous version we could state the
risk that Medicaid dispensing is not US dispensing but not demonstrate it. We can now, with a
date, and the limitation is rewritten accordingly.

**The marketing-rights transfer.** One exit is a transfer of US responsibility for a product
from one firm to its originator, announced with the statement that availability was not expected
to be affected, and the other firm does dispense in the market afterwards. Its replacement ratio
is 5.45, the largest in the cohort.

**A defect in our own method.** One exit is a firm retiring an unapproved multi-element
injectable line under FDA's unapproved drugs initiative and replacing it with approved products.
Those products dispense in the panel, but their composition differs enough that our own
composition tie-break holds them in a sibling key. A product-generation change therefore reads
as an exit with no replacement. We report it against ourselves in Section 3.4 and in the
appendix, because the same mechanism will affect any study that keys markets on composition, and
because it bounds how far a composition tie-break can be trusted.

**What this does to the headline.** The stratified result is stronger than before, in the
direction that is uncomfortable for a supply-resilience reading. The median replacement ratio is
0.00 across all 19 observed exits, 0.08 across the 11 the records do not explain, and 0.47
across the 2 documented supply disruptions, neither of which collapses below two percent of
baseline. Zero replacement is concentrated in the exits that are not supply failures.

---

## 4. The remaining items from earlier rounds

Each of these was addressed in the version you last saw and is unchanged by the detector
correction unless noted. They are kept here so the record is in one document.

### The two 34.1% figures (your C7, P0)

You were right to ask. They are different quantities and we had used one number for
both. Computed separately, of 853M flagged prescriptions:

| Measure | Numerator | Share |
|---|---|---|
| Largest-component rule, whole raw market-quarters | 292M | **34.3%** |
| Volume allocated across all corrected components | 291M | **34.1%** |

Both appear in Table 4 with their numerators, and the text states that they are
different operations which agree only approximately.

### Macro spacing (your C5, P0)

Entirely our defect and introduced by the generation change itself: TeX swallows the
space after a control word, so a macro defined without `\xspace` rendered
"292testable". There were 55 such joins. All 425 macros now carry `\xspace`, the count is zero,
and `verify_manuscript.py` reads the rendered PDF and fails on any digit joined to a
word. Our previous checks read extracted text for presence only, which is exactly why
they were blind to it.

### Trace Elements (your C3, P0)

The limitation was outdated and is removed. In the final mapping, Trace Elements 4 and
Trace Elements 5 are separate normalised keys, and the two manufacturers' Trace
Elements 4 products that FDA records with different element sets are also separated by
the composition tie-break. No residual false merge survives this check. Section 3.3 now
states the order of operations explicitly: merge rule applied, substance data used to
identify wrong joins, rule changed, check re-run. The agreement is therefore
agreement after adjudication by the same field, which we say wherever we report it, and
Section 2.4 no longer calls that field an independent referee.

### Missing-route handling (your C4, P0)

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

### Formulation mismatch (your C2, P0)

Table 2 was right and Figure 1(a) was wrong: the corrected market is
`AMPHETAMINE,... | ORAL CAPSULE`. The figure had its own hard-coded label map with
"tablet" as a fallback string. There is now one shared label map that both the table
and the figure import, it raises an error on any key it does not cover, and a check
compares the rendered figure's labels against the table's, dosage form included.

### Near-sole terminology (your C8)

Adopted. The share-defined stratum is called near-sole-labeler throughout the event
analysis, and we report the exact-labeler count you asked for:
17 of the 19 observed events had exactly
one active labeler across the four pre-exit quarters;
2 had a second labeler whose dispensing was small enough
that the departing share still rounded to 100 percent.

### Overstated claims (your C9)

All three corrected. The recovery result is now described as suggestive and not
statistically established, in the abstract and the discussion. The matched comparison
reports 0.31% rather than "zero" everywhere. The
duplicate-key prevalence is stated as 11.5%
of route-aware raw market keys.

### One more we found while doing this

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

### Items settled in rounds before the last one

### The construction of the reclassification rate (your Section 2)

You were right that assigning a split raw market to its largest corrected component is
a modelling choice rather than a mapping, and that the headline should not rest on it.
Of the 58,914 raw near-sole market-quarters, those that split into more than one corrected
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
trimming (1.66 → 1.56 → 1.47 → 1.46 removing the largest one, three and five), but the
mean falls from 287.71 to 5.83, -3.36 and -7.04, and the
volume-weighted ratio from 420.49 to -0.08, -17.22 and -24.56, changing sign. The five largest ratios are 31012, 625, 370, 273 and 107. **We have
withdrawn the volume-weighted figure for that band**, since no stable value exists.

### Suppression scenario (your C9)

Reported alongside the primary estimate: reading every suppressed post-event quarter as ten
prescriptions, which is the most generous reading the suppression rule allows,
takes 8 of 19 to 7 of 19, or 42.1% to 36.8%. Stated as a scenario, not a bound,
and kept separate from the missing-follow-up bounds of 18.6% to 74.4% (see Section 0).

### Market granularity (your C4)

We ran it. Adding strength gives 200,534 market-quarters, with 62.0% near-sole holding
19.96% of volume, against 55.7% and 10.54% at ingredient-and-route granularity. Finer
markets are mechanically more concentrated, so this is not a competing estimate of the
same quantity, and we now say so explicitly: the corrected figure is the concentration
of ingredient-and-route markets, not an estimate of true concentration at every
granularity. A reader who wants strength-level markets will measure more concentration,
not less.

### Repository

The repository is public and the code-availability statement has been verified from a
signed-out session. The README described the previous paper, with findings this analysis does
not support, which was your first comment. It is rewritten, and `check_readme.py` now asserts
that its title is the manuscript's title, that its headline counts are the ones the results
files hold, that the stage and check counts it promises match `run_all.sh`, and that every
number in it traces to an analysis output.

---

## 5. Standing positions on recurring items

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
demotion rather than by engineering. Nineteen treated events will not support a defensible
causal design under any control construction, and the corrected detector raising the count
from thirteen does not change that. The comparison is labelled descriptive and secondary, the
forward-looking eligibility rule is disclosed rather than defended, and the control reuse is
quantified in the text (475 observations from 88 distinct markets, one appearing in 18 of the
19 sets). We do not intend to expand it further, and we would rather it were read as a
descriptive contrast than as an estimate.

**The recovery and verified-disruption analyses.** We agree these cannot carry general
conclusions and have not asked them to. Two observations from one episode are reported as a
case-based illustration, and two is weaker than the three we previously had. The recovery
comparison is the one place the corrected detector made a result stronger: the log-rank at the
90 percent threshold is now p = 0.002 where it was 0.056, and we report it as established at
that threshold and still not established at 50 percent, where it is p = 0.188. Figure 3 carries
confidence bands throughout. Our only claim from the verified-disruption material is negative:
the data do not support the statement that sole-supplier markets fail to replace lost volume
after a documented supply disruption.

**The manufacturing-establishment analysis.** We accept it is supporting context rather
than an established contribution, and the manuscript labels it that way. Current
listings do not establish historical production sites. Reconstructing them is a separate
study.

---

## 6. What we believe the paper now establishes, and what it does not

**Establishes.** That the standard ingredient-by-dosage-form market definition, applied to
public Medicaid dispensing data, contains two measurement defects; that correcting them changes
the national picture materially, moving dispensing in near-sole markets from 14.71% to 10.54%
and reclassifying between 16.2% and 28.9% of apparent near-sole market-quarters carrying 34.3%
of flagged volume; that 9 of 26 apparent sole-labeler exits are not sole-labeler exits; and
that of the 19 the corrected panel observes, 2 are a documented supply disruption, 8 are
explained by something that is not a supply failure, 5 have supply continued by another
labeler, and 4 are undetermined.

We would add a second claim this round earned, on your prompting: that the pooled collapse rate
among near-sole exits is carried by exits that are not supply failures, 8 of 19 pooled against 2
of 11 once the explained classes are removed and 0 of 2 in the documented disruptions, and that
the gap is the measurable cost of not auditing causes.

We would add one methodological claim we did not make before, because this round earned it: an
event detector built on administrative dispensing data has to be tested against the case where
the series stops, not only against the case where it falls. Ours was not, for two rounds, and
the defect was invisible in every number we reported because the events it hid never appeared
anywhere to be counted.

**Does not establish.** That the corrected definition is the clinically correct one at
every granularity; that the reclassification rate is an independently adjudicated
false-positive rate; that concentration causes dispensing loss; or anything general about
recovery after supply disruptions.

We would welcome the paper being assessed on the first list.

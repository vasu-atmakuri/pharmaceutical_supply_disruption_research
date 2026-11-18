# Response to reviewer

Thank you for the eighth round of comments. Every point in this round was acted on.
Below we list what changed, and then set out our standing position on a small number
of items that have recurred across rounds, so that the remaining disagreements are
explicit rather than repeated.

The manuscript is accompanied by two scripts that enforce internal consistency:
`verify_manuscript.py`, which pins named figures in the text to the analysis output
files by value, and `audit_numbers.py`, which extracts every number in the source and
fails if any of them appears in no analysis output. Both pass on the attached version.

---

## 1. Changes made in response to this round

### The construction of the reclassification rate (your Section 2)

You were right that assigning a split raw market to its largest corrected component is
a modelling choice rather than a mapping, and that the headline should not rest on it.
14,649 of the 58,905 raw near-sole market-quarters split into more than one corrected
market. The manuscript now reports all three rules you proposed, plus a volume
allocation that requires no rule at all:

| Rule | Reclassified | Rate |
|---|---|---|
| Largest corrected component | 15,744 | 26.7% |
| Any component still near-sole | 9,549 | 16.2% |
| Every component still near-sole | 17,004 | 28.9% |
| Volume allocated across all components | — | **34.1% of flagged dispensing** |

The count is bracketed between 16.2% and 28.9%. We now describe 26.7% as the rate
under the largest-component rule, not as an established false-positive rate, and we
treat the volume figure as the more robust of the two because it needs no assignment
choice. This is a better result than the one it replaces and we are grateful for it.

### The remaining false merge (your Section 3)

Fixed rather than documented. We added a composition tie-break: where the merge rule
would join keys for which FDA records different active-substance sets, the keys are
kept apart. This splits four groups, including Trace Elements 4, and raises agreement
with the substance data from 293 of 294 to **all 291 testable groups**. We have
removed any claim that all absorbed keys are proven duplicates; 16 groups remain
untestable because substance names are missing for every member, and that is stated.

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
mean falls from 19.21 to −0.92 and the volume-weighted ratio from 14.55 to −12.18,
changing sign. The five largest ratios are 625, 370, 273, 170 and 107. **We have
withdrawn the volume-weighted figure for that band**, since no stable value exists.

### Suppression scenario (your C9)

Reported alongside the primary estimate: the ten-prescription imputation moves one
market, taking 5 of 13 to 4 of 13, or 38.5% to 30.8%. Stated as a scenario, not a bound,
and kept separate from the missing-follow-up bounds of 26.3% to 57.9%.

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

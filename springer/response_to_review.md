# Response to review

Reviewer recommendation was Major Revision, 6.5/10. Most findings were correct. This records
what was verified, what was fixed, and what was retracted.

## Findings that were correct and are now fixed

**1. Table 1 did not reconcile.** Correct, and the cause was worse than an arithmetic slip. The
table mixed two specifications: the sole-supplier row came from a t-6 to t-3 baseline run, the
other rows and the overall row from an earlier t-8 to t-5 run. Those are different samples.
Rebuilt on one eligibility rule and one baseline: strata are 87, 8, 7, 20, summing to 122, with
10 markets below threshold, 8.2 percent overall. The reviewer's inferred count of 10 was right.

**2. Treatment and outcome were partly the same event.** Correct, and this was the most important
finding in the review. A 95 percent supplier dropping to near zero mechanically reduces market
volume. The paper now leads with the **replacement ratio**: volume taken up by all *other*
suppliers, divided by the departing supplier's baseline volume. The event definition constrains
only the departing supplier, so this quantity is not mechanical. Median at six quarters: 1.45
under 35 percent, 1.13 at 35 to 65, 0.97 at 65 to 95, and 0.00 for sole suppliers. The result is
stronger stated this way than it was before.

**3. Control group was selected on survival.** Correct. The old controls required dispensing in
34 of 41 quarters, which conditions on survival. Replaced with risk-set matching on pre-event
labeler count, dosage form, calendar quarter and baseline volume, with no survival requirement.
The contrast is undiminished: 20 single-labeler markets that lost their labeler show 45.0 percent
below threshold against 0.0 percent of 500 matched single-labeler markets that did not, with
dispensing of -96.6 vs +2.7 percent, permutation p = 0.00005. The critique was reasonable and the
result survives it.

**4. Substitution compared different denominators.** Correct, and this killed the finding. In
absolute volume the affected markets lost about 226,000 prescriptions per quarter while their
classes gained about 3.23 million. Class movement is more than fourteen times the loss, so it is
secular growth, not substitution. The "absorbs one sixth" claim is **retracted**. The paper now
states that this design cannot identify therapeutic substitution and explains why. The log-point
versus percentage error is also fixed; percentages are now computed as 100(exp(d)-1) throughout
and log points are never printed as percentages.

**5. Labeler is not manufacturer.** Correct. The paper now uses "labeler" throughout, carries a
dedicated methods subsection stating that an NDC labeler may be a manufacturer, repackager,
relabeler or private-label distributor, and lists this first among limitations. Note that the
primary outcome is unaffected: whether some other labeler took up the volume does not depend on
resolving corporate identity.

**6. Generic status was not established.** Correct. Added marketing category from the FDA product
file. 97.4 percent of panel dispensing is from ANDA or authorized generic labelers, and 16 of 20
sole-supplier departures involve such a labeler. Stated explicitly rather than assumed.

**7. Contradictory eligibility criteria.** Correct, the text was sloppy. Now a single numbered
rule, with the funnel reported: 285 events, 132 inside the window, 122 meeting all conditions.

**8. Missingness algorithm.** Added. Observed, suppressed and absent are defined separately;
baseline must be complete; post-event zeros are substituted only when at least one post quarter
is observed. Because national-row suppression implies fewer than eleven prescriptions nationally,
the zero substitution errs by at most ten prescriptions per quarter.

**9. Price conclusion overstated.** Correct, and the sign flipped on the corrected specification.
Reimbursement per prescription among the 11 surviving sole-source markets is **+11.8 percent**,
not negative as previously reported. With n = 11, gross-of-rebate amounts, and composition
effects, this supports no conclusion in either direction. The "no price signal" claim is
withdrawn; the paper now states only that aggregate reimbursement tracked volume.

**10. Permutation floor.** Correct. 800 draws put the floor at 0.00125, which is what was being
reported as the p value. Now 20,000 draws, floor 0.00005, stated explicitly.

**11. Confidence intervals.** Added Wilson intervals throughout. The sole-supplier interval is
25.8 to 65.8 percent, matching the reviewer's calculation exactly.

**12. Control count 1432 vs 1433.** Resolved by the control redesign; counts are now reported
per matched comparison.

**13. "Replacement entry does not occur" too absolute.** Changed to "Replacement entry is
limited". Also added that the entry measure counts returning labelers and relabeling, so it is an
upper bound on true entry.

**14. Li and Wu (2022) concerns China.** Correct. Removed from the price discussion.

## Where the review's inference was close but the underlying number differed

The reviewer inferred 9 of 20 sole-supplier markets below threshold from the printed 45.0
percent. That is exactly right. They inferred the overall count should be about 8 from 6.8
percent of 118. The true figures are 10 of 122, 8.2 percent. The discrepancy they detected was
real; its cause was the mixed specification rather than a rounding error.

## Still open, and acknowledged in the manuscript

- Labeler codes are not linked to FDA establishment registrations. Named as the single most
  valuable extension.
- Safety withdrawals can be flagged but not cleanly excluded on the national panel, because the
  sole-supplier stratum is too small to split there.
- n = 20 in the primary stratum. Direction is secure, magnitude is not precise.
- Substitution remains unidentified and is stated as an open question.

## Title

Changed to reflect what the paper now establishes:
"When the last supplier leaves: absent replacement after sole-source supplier loss in US Medicaid
drug markets"

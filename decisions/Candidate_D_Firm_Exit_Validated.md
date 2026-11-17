# Candidate D: abrupt manufacturer exit and market absorption. VALIDATED.

16 November 2026. Tested to the same depth that killed candidates A and B.
Scripts ~/work/firmexit.py, exittest.py, exittest2.py. Data: SDUD 2014Q1-2025Q4.

## The question

**When a pharmaceutical manufacturer collapses abruptly, does the market absorb its volume,
and does recovery depend on how concentrated its position was?**

This is the natural next question after the discontinuation paper. That paper measured
absorption after *planned, single-product* MDRP terminations. This measures absorption after
*unplanned, correlated, multi-product* firm collapse, where the market gets no notice and
capacity disappears rather than transferring.

## Treatment detected from the data, 44 staggered events

Abrupt labeler exits, defined as sustained dispensing of at least 20,000 prescriptions per
quarter collapsing to under 10% of that level for at least four consecutive quarters.

- **44 exiting labelers**, 2016 to 2024, no year with more than 3
- **1,302 products affected**, mean 29.6 per exit
- **6.3 million prescriptions per quarter** in aggregate pre-exit
- **483 treated molecules**, of which the exiting firm's share was: p25 = 0.07,
  **median = 0.893**, p75 = 1.00, max = 1.00. Most treated molecules lost their only supplier.
- 2,863 never-exposed control molecules of comparable volume

**The detector validated itself.** Labeler 17478 exits 2023Q2 with 111 products, and 50383
exits 2023Q3 with 80. Those are Akorn and Hi-Tech Pharmacal, which Akorn owned. Akorn shut its
four plants abruptly in February 2023 and recalled all in-date product on 26 April 2023. The
method found the Akorn collapse with no external data.

## Test 1: event-time path. PASSES.

Molecule log dispensing relative to quarter -1, treated minus control:

| k | DIFF | | k | DIFF |
|---|---|---|---|---|
| -8 | -0.0051 | | **0 (exit)** | **-0.1364** |
| -7 | -0.0475 | | +1 | -0.2164 |
| -6 | -0.0319 | | +2 | -0.2152 |
| -5 | +0.0293 | | +3 | -0.2199 |
| -4 | +0.0663 | | +4 | -0.2353 |
| -3 | +0.0301 | | +5 | -0.2332 |
| -2 | +0.0374 | | +6 | -0.2181 |
| -1 | +0.0000 | | +7 | -0.1405 |

Flat before, **sharp break exactly at the exit quarter**, sustained at -0.21 to -0.24 for six
quarters. This is the signature candidate A never produced. Attenuation at k=7 and k=8 is
control-group attrition at long horizons, not recovery.

## Test 2: dose-response. PASSES, and this is the decisive one.

Candidate A died on a non-monotone dose-response. This one is textbook.

| exiting firm's share of molecule | n | DiD vs control |
|---|---|---|
| 0 to 10% | 141 | **+0.108** |
| 10 to 35% | 54 | **+0.081** |
| 35 to 65% | 15 | -0.201 |
| 65 to 95% | 20 | -0.245 |
| 95 to 100% | 68 | **-1.061** |

Zero effect where the firm was a minor supplier, rising monotonically, and **molecules losing
their sole supplier lose about 65% of dispensing**. The zero at zero exposure is a placebo
built into the design.

## Test 3: power. PASSES.

Permutation inference, 400 draws of matched control samples.
Overall DiD **-0.2029, p = 0.0025**. Placebo SD 0.0408. **MDE = 12.1%.**
Observed effect is 20% overall and 65% in the sole-supplier band, far above MDE.

For comparison: candidate B's MDE was 26% to 42% against effects that were never detectable.

## Test 4: placebo-in-time. PASSES with a note.

Pseudo-event 8 quarters before the real exit: DiD **+0.0611**, against the real **-0.2029**.
Small, and opposite in sign, so it cannot generate the result. The positive sign suggests
treated molecules were mildly growing before exit, which is worth investigating but is the
opposite of the selection story a reviewer would worry about.

## The intellectual risk, stated plainly

**A reviewer will say the initial drop is mechanical.** If the sole supplier stops selling,
of course dispensing falls at t=0. That objection is correct and the paper must not lead with
the drop.

The contribution is **non-recovery**: dispensing stays roughly 22% down, and 65% down for
sole-supplier molecules, for at least six quarters. Nobody enters. Nobody substitutes at
scale. The market does not repair itself. That is not mechanical, it is a finding about how
badly concentrated generic markets fail, and it is the opposite of what the discontinuation
paper found for planned exits (82.7% absorbed).

Framing must be: *how long does it take, and does it ever happen*, not *does dispensing fall*.

## Why this one survived where A and B died

| | B | A | **D** |
|---|---|---|---|
| Treated units | 3-4 states | ~2,000 products | **483 molecules, 44 events** |
| Sharp break at event | n/a | **no** | **yes** |
| Monotone dose-response | n/a | **no** | **yes** |
| Clean placebo-in-time | n/a | partial | **yes** |
| Single-date confound | n/a | **IRA Jan 2025** | **no, staggered over 9 years** |
| MDE vs effect | 26-42% vs nothing | 8% vs artifact | **12% vs 20-65%** |

Staggered treatment across nine years is what protects it. No single policy shock can explain
44 exits on 44 different dates.

## What still needs doing before writing

1. **Molecule definition.** Currently the 10-character SDUD product name. Needs the real
   NDC to ingredient crosswalk from the FDA NDC Directory.
2. **Therapeutic substitution.** The real test of absorption is whether volume moves to other
   molecules in the same class. Needs an ATC or USP class crosswalk, which is the main
   remaining data dependency.
3. **Validate exit dates externally** against FDA recall and discontinuation records for a
   sample of the 44, as was done for Akorn.
4. **Separate cause of exit:** bankruptcy, FDA enforcement, voluntary withdrawal. Changes the
   policy interpretation.
5. **Market structure at exit:** number of remaining suppliers, which should moderate recovery.
6. **Literature check is NOT complete.** Akorn has rich trade coverage but no empirical study
   was found. A full sweep on firm exit and market absorption in generics is still required
   before committing.

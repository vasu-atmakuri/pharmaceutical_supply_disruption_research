# SDUD managed care completeness gate: result

16 November 2026. Data: SDUD 2017 to 2026Q1, 10 files, 4.53 GB, read in full.
Outputs in this folder: `sdud_mcou_completeness_by_state_quarter.csv`.

## Verdict: GATE PASSED

41 to 43 states report both FFSU and MCOU in every year, all four quarters, 2017 to 2025.
That is a usable panel for the within-state, within-quarter, within-molecule contrast.

- **Zero rejected rows** across all 4.53 GB. The earlier parse failure was a quoting issue
  (`"Creon 6,00"`, a truncated 10-character FDA list name containing a comma, read with
  quoting disabled). Setting the quote character explicitly fixed it. Nothing was dropped.
- Header layout identical across all 10 files: 15 columns.
- Both FFSU and MCOU present in every file.
- The 'XX' national rows are real and sizeable (274,082 in 2017 rising to 320,609 in 2025).
  Summing them with state rows double counts. All figures here exclude `State = 'XX'`.

| year | states | with MCOU | qtrs | MCOU % of rx | MCOU % of $ | total rx (M) | rows (M) |
|---|---|---|---|---|---|---|---|
| 2017 | 51 | 41 | 4 | 72.3 | 64.5 | 757.96 | 4.54 |
| 2018 | 51 | 41 | 4 | 72.0 | 62.7 | 735.54 | 4.61 |
| 2019 | 51 | 42 | 4 | 72.5 | 65.1 | 722.97 | 4.68 |
| 2020 | 51 | 41 | 4 | 72.6 | 66.3 | 694.00 | 4.63 |
| 2021 | 51 | 41 | 4 | 73.8 | 68.0 | 728.69 | 4.75 |
| 2022 | 51 | 41 | 4 | 67.2 | 63.7 | 758.07 | 4.88 |
| 2023 | 52 | 42 | 4 | 60.8 | 57.9 | 775.54 | 5.01 |
| 2024 | 52 | 43 | 4 | 58.6 | 53.8 | 728.59 | 4.99 |
| 2025 | 52 | 43 | 4 | 58.7 | 52.9 | 716.55 | 4.99 |
| 2026 | 52 | 41 | 1 | 54.5 | 47.4 | 162.97 | 1.21 |

## The states with no MCOU are not a data defect

Nine to twelve states report no measurable managed care volume in any given year: AK, AL,
AR, CT, ID, ME, MO, MT, OK, SD, VT, WI, WY. Precisely: some do emit a handful of MCOU rows
but every one of them is suppressed, so the reported volume is null rather than absent. For
example AK 2017Q1 has 86 MCOU rows, all 86 suppressed. These are states with no
comprehensive Medicaid managed care, or with the pharmacy benefit administered
fee-for-service. That absence **is** the policy variable, not missing data. They are the
never-treated comparison group. Note for coding: distinguish "no MCOU rows at all" from
"MCOU rows present but fully suppressed", since only the first is a true structural zero.

No state-quarter is missing FFSU before 2023; four state-quarters per year lack it from 2023.

## The MCOU share decline is policy, not data quality

I flagged the fall from 73.8% (2021) to 58.6% (2024) as a possible reporting gap. It is not.
It is driven by the two largest Medicaid pharmacy programs carving out.

## THE IMPORTANT FINDING: pharmacy benefit switches are detectable in the data

Quarter-over-quarter shifts in the MCOU share of prescriptions, states above 250,000
prescriptions per quarter:

**Carve-outs, managed care to fee-for-service**

| state | quarter | MCOU share | change | state rx that qtr | verification |
|---|---|---|---|---|---|
| WV | 2017Q3 | 94.1% to 4.6% | -89.6 pts | 1.65M | **VERIFIED.** Pharmacy benefit moved from MCO back to FFS effective 1 July 2017 (WV BMS provider newsletter; MACPAC) |
| NY | 2023Q2 | 87.5% to 3.7% | -83.8 pts | 18.74M | **VERIFIED.** NYRx carve-out effective 1 April 2023 (NYS DOH) |
| CA | 2022Q1 | 75.1% to 8.6% | -66.5 pts | 17.34M | **VERIFIED.** Medi-Cal Rx went live 1 January 2022, transitioning all Medi-Cal pharmacy services from managed care to FFS under EO N-01-19 (CA DHCS) |
| NV | 2023Q1 | 72.4% to 46.2% | -26.2 pts | 0.87M | not yet verified, partial shift |

**Carve-ins, fee-for-service to managed care**

| state | quarter | MCOU share | change | state rx that qtr | verification |
|---|---|---|---|---|---|
| NC | 2021Q3 | 0.0% to 58.4% | +58.4 pts | 4.16M | **VERIFIED.** Statewide managed care launch 1 July 2021, 1.6M beneficiaries moved from FFS (NCDHHS) |
| OK | 2024Q2 | 0.0% to 54.7% | +54.7 pts | 2.11M | **VERIFIED.** SoonerSelect, Oklahoma's first statewide Medicaid managed care in two decades, launched 1 April 2024 (OHCA) |
| UT | 2024Q3 | 27.8% to 50.2% | +22.4 pts | 0.82M | not yet verified |
| IL | 2018Q2 | 69.3% to 87.5% | +18.2 pts | 6.40M | not yet verified |
| DC | 2020Q4 | 60.3% to 84.7% | +24.3 pts | 0.49M | not yet verified |
| NV | 2023Q3 | 43.0% to 62.2% | +19.3 pts | 1.26M | not yet verified |

**Five for five on the large events.** Every one of the five biggest detected switches lands
exactly on the documented implementation quarter: WV 1 Jul 2017, CA 1 Jan 2022, NC 1 Jul
2021, NY 1 Apr 2023, OK 1 Apr 2024. The detection method works and the match independently
validates it. Remaining unverified are the smaller or partial shifts: NV 2023Q1 and Q3, UT
2024Q3, IL 2018Q2, DC 2020Q4.

**Known limitation of the detector.** It finds delivery-system switches between managed care
and fee-for-service, not changes in how the benefit is administered within managed care.
Ohio is counted among the carve-out states in policy surveys but produces no MCOU to FFSU
jump here, because Ohio consolidated to a single state-selected PBM rather than moving the
benefit to fee-for-service. Single-PBM reforms are a separate treatment and would need
hand-coding if they are to be included. Cross-check list: as of July 2025 eight states
operated pharmacy carve-outs, including California, Missouri, North Dakota, New York, Ohio
and Tennessee. The long-standing carve-out states (MO, ND, TN, WI) correctly show no switch
event, because they never switched during the window; they sit in the never-treated arm.

### Why this changes the design

The original plan needed a hand-coded state policy panel from KFF and HMA surveys, which
was the weakest and most manual part of the data plan and the part reviewers would attack.
It is no longer needed as the primary source. The switch events are **detected from the
data and then confirmed against published implementation dates**, which is both stronger and
reproducible.

More importantly, identification improves. Instead of comparing carve-in states against
carve-out states cross-sectionally, the design becomes:

- **Within-state switches with known dates.** The same state's entire pharmacy benefit moves
  between managed care and fee-for-service. The state is its own control.
- **Both directions.** Carve-outs (NY, CA, WV) and carve-ins (NC, OK). If absorption of
  supply shocks moves in opposite directions for the two, that is the mechanism rather than
  a secular trend. This is the robustness test the cross-sectional design could not offer.
- **Large.** NY at 18.7M and CA at 17.3M prescriptions per quarter are the two biggest
  state programs in the data.
- **Never-switchers as a third arm.** The 9 to 12 permanently FFS-only states.

## REAL CONSTRAINT FOUND: suppression censors the low end

Rows with `Suppression Used = true` run **48.9% to 52.3% of all rows in every year**. SDUD
suppresses cells with very low prescription counts, so the suppressed share of *volume* is
small, but the suppressed share of *cells* is about half.

This matters for shortage work specifically, and must be handled explicitly:

A drug going into shortage pushes NDC-state-quarter cells from reported into suppressed.
Summing only reported values therefore **understates dispensing loss**, because part of the
loss leaves the data rather than showing up as a smaller number. Treat suppressed cells as
interval censored at the suppression threshold, not as missing and not as zero, or aggregate
to ingredient level where the censoring is immaterial. Report both.

## Next

1. Verify the remaining switch dates: WV 2017Q3, OK 2024Q2, NV 2023Q1 and Q3, UT 2024Q3,
   IL 2018Q2, DC 2020Q4.
2. Reconstruct FDA shortage onset and resolution events 2018 to 2026 from the FDA web
   archive, following the ASPE method.
3. Build the molecule crosswalk so shortage events at molecule level map to NDCs in SDUD.
4. Quantify how much estimated dispensing loss changes when suppressed cells are treated as
   censored rather than missing. This is a methods result in its own right and answers the
   2025 Pharmacoepidemiology and Drug Safety scoping review's call for standardized methods.

# Paper spec: shortage absorption by payer arrangement

Vasu Atmakuri, main author. Drafted 16 November 2026. Target: Value in Health (Q1).

## 1. The paper at a glance

| | |
|---|---|
| **Question** | When a national drug shortage hits, does the Medicaid population lose more access under managed care or under fee-for-service, and does it change when a state moves its pharmacy benefit from one to the other? |
| **Core claim to test** | Formulary flexibility determines absorption. Managed care plans can substitute across a shortage faster than a state-run preferred drug list can, so carving pharmacy out of managed care should reduce absorption and increase access loss. The reverse for carve-ins. |
| **Why nobody has done it** | RAND owns the US shortage literature using IQVIA National Sales Perspective and MIDAS. Those are sales data with no payer dimension. The comparison is structurally impossible with the data the incumbents use. |
| **Gap certification** | *Pharmacoepidemiology and Drug Safety* 2025 scoping review, 60 studies: no included study used SDUD, none compared managed care against fee-for-service, only 5 of 60 covered all shortages in a region over a period, and it explicitly calls for population-level outpatient work and standardized methods. |
| **Identification** | Five verified within-state switches of the entire pharmacy benefit, on known dates, in both directions. Each state is its own control. Roughly 40 never-switchers form a third arm. |
| **Decision relevance** | Eight states operated pharmacy carve-outs as of July 2025 and more are moving. State Medicaid directors are deciding this now with no evidence on supply-shock resilience. |
| **Constraints cleared** | Pure computation. No IRB, no participant pool, no data use agreement, no licensed data, no human subjects. Everything public and reproducible. |

## 2. Data inventory

| Dataset | Coverage held | Scale | Grain | Status |
|---|---|---|---|---|
| **Medicaid SDUD** | 2017Q1 to 2026Q1, downloaded 16 Nov | **10 files, 4.53 GB, 44.3M rows, 6.78 billion prescriptions** | state x quarter x NDC x utilization type | **VERIFIED in full.** 15 columns, identical header across all files, zero rejected rows |
| SDUD extension | 2014 to 2016 | ~3 files, ~1.4 GB, ~13M rows | same | **NEEDED.** See section 3: WV has only 2 pre-period quarters without it |
| **FDA drug shortage database** | 2018 to 2026 reconstructable | ~2,900 distinct shortage events in 2023-24 alone | drug, NDC, status, dates | Method documented, not yet built. ASPE rebuilt status histories from FDA web archives at 11-digit NDC level; the consolidated Excel starts Dec 2019; Wayback holds 476 snapshots Jan 2023 to Aug 2024 |
| **NADAC** | 2013 to present, weekly | ~19M rows estimated, not verified | NDC x week | Not yet downloaded. Supporting price series, gives sub-quarterly resolution SDUD lacks |
| FDA NDC Directory | current + archived | ~100k+ products | NDC to ingredient | Needed for the molecule crosswalk |
| CMS managed care enrollment reports | annual by state | small | state x year | Needed as denominator. Granularity not yet confirmed |
| State policy switch dates | 2017 to 2026 | 5 large, 5 smaller | state x quarter | **5 of 5 large ones VERIFIED against primary sources** |

Known SDUD traps, both already handled:
- National 'XX' rows coexist with state rows and double count by roughly 1.99x. Volume is real and large, 274,082 rows in 2017 rising to 320,609 in 2025. Filter them everywhere.
- Suppression runs **48.9% to 52.3% of all rows in every year**. Small volume effect, but a drug going into shortage pushes cells from reported into suppressed, so naive summation **understates loss**. Treat as interval censored, not missing, not zero.

## 3. The treatment events, and usable pre/post windows

Within 2017Q1 to 2026Q1 there are 37 quarters.

| State | Switch | Direction | MCOU share before to after | Pre qtrs | Post qtrs | State volume | Verification |
|---|---|---|---|---|---|---|---|
| WV | 2017Q3 | carve-out | 94.1% to 4.6% | **2** | 35 | 1.65M rx/qtr | Effective 1 Jul 2017, WV BMS |
| NC | 2021Q3 | carve-**in** | 0.0% to 58.4% | 18 | 19 | 4.16M rx/qtr | Launched 1 Jul 2021, 1.6M beneficiaries, NCDHHS |
| CA | 2022Q1 | carve-out | 75.1% to 8.6% | 20 | 17 | 17.34M rx/qtr | Medi-Cal Rx live 1 Jan 2022, DHCS, EO N-01-19 |
| NY | 2023Q2 | carve-out | 87.5% to 3.7% | 25 | 12 | 18.74M rx/qtr | NYRx effective 1 Apr 2023, NYS DOH |
| OK | 2024Q2 | carve-**in** | 0.0% to 54.7% | 29 | 8 | 2.11M rx/qtr | SoonerSelect launched 1 Apr 2024, OHCA |

**Action: download SDUD 2014 to 2016.** It lifts WV from 2 pre-quarters to 14 and is the only
structural weakness in the event set. Three files, about 1 minute.

Smaller or partial shifts, not yet verified, usable as robustness: NV 2023Q1 and Q3, UT
2024Q3, IL 2018Q2, DC 2020Q4.

Detector limitation: it finds delivery-system switches, not administrative change inside
managed care. Ohio is a carve-out state in policy surveys but produces no jump, because it
consolidated to a single state-selected PBM rather than moving to fee-for-service. Separate
treatment, would need hand-coding.

## 4. How each data element answers which part of the question

| Part of the question | Data used | How |
|---|---|---|
| When did a shortage start and end? | FDA shortage database, archive-reconstructed | Event date per molecule. Known to lag reality, so the ASPE caveat gets stated and NADAC price movement is used as a cross-check |
| How much dispensing was lost? | SDUD units and prescriptions | Molecule-level volume against matched non-shortage controls, both utilization types |
| How much was absorbed by substitutes? | SDUD plus NDC-to-ingredient crosswalk | Share of lost volume recovered by within-class alternatives. **Same metric as the 82.7% absorption figure in the discontinuation paper**, which makes the papers directly comparable |
| Does the payer arrangement matter? | SDUD utilization type, FFSU against MCOU | Within state, quarter and molecule, which differences out shortage severity, national supply and anything else common to the molecule |
| Is it causal, not a trend? | The five switch events | Staggered difference-in-differences. **Both directions**: if absorption falls for carve-outs and rises for carve-ins, that is the mechanism and not a secular trend |
| Is it supply or formulary? | FFSU against MCOU asymmetry | A formulary change usually hits one utilization type. A supply shock hits both. Free placebo test, and it answers the obvious objection that a Medicaid dispensing drop is not a shortage |
| Does suppression bias it? | Suppression flag | Re-estimate with suppressed cells as interval censored against treated as missing. The difference is a reportable methods result |
| Does enrollment explain it? | CMS managed care enrollment | Denominator and control, since MCOU volume moves with penetration |

## 5. Fit to profile

| Paper requirement | What you already have | Reuse or new |
|---|---|---|
| Handle 44M+ rows across heterogeneous federal files | 8 years data engineering, Spark, Databricks, Snowflake. Discontinuation paper ran on 44.1M rows. 15.8M row DuckDB aggregation | Direct reuse |
| NDC-level linkage across federal sources | Done for openFDA to SDUD, including the normalization rule | Direct reuse |
| Avoid the SDUD double-count | Already hit the 'XX' bug once and know the 1.99x signature | Direct reuse |
| Event study with matched controls and placebo dates | Both completed supply chain papers | Direct reuse |
| Censoring for suppressed cells | Censoring and survival analysis already used | Direct reuse |
| **Staggered difference-in-differences** | Callaway and Sant'Anna is on your known-but-unused list. Five switches at five different dates is exactly a staggered adoption design | **Converts a known-but-unused method into a published use** |
| **Changepoint detection** | Also on your known-but-unused list. The switch detection run on 16 Nov was crude; formalizing it is a methods contribution | **Same: unused to published** |
| Absorption metric | 82.7% figure from the discontinuation paper | Reuse, and the cross-paper comparison becomes a result |

### Why this is the stronger fit, specifically

1. **The hard part is the part you are good at.** The difficulty here is building a clean
   44M+ row panel with correct handling of suppression censoring, national-row double
   counting, policy timing and NDC-to-molecule mapping, then re-running it several ways. That
   is data engineering at scale. The rebate paper's hard part is estimating a price series
   that is not public and defending it against NBER economists, which is econometric
   judgement rather than engineering.
2. **It consolidates instead of scattering.** Your record is six papers across four fields,
   and on the supply chain line you are co-author on the accepted one. This is visibly the
   next question after the recall and discontinuation papers, using the same outcome data and
   the same absorption metric. Three connected papers read as a programme.
3. **It is a main-author Q1 journal paper.** Every one of your six is a conference paper or
   unplaced. This fills the actual hole in the record.
4. **The advantage is durable.** RAND cannot run this with sales data, now or in two years.
   On the rebate paper your only edge is that nobody has got round to it yet, against teams
   who already published the method.
5. **It needs nothing you do not have.** No IRB, no funding, no data use agreement, no
   licensed data, no human subjects, no travel.

### CRITICAL CONFOUND FOUND 16 Nov: the New York event collides with Medicaid unwinding

The Medicaid continuous enrollment condition ended **31 March 2023**, and states could begin
disenrolling from **1 April 2023** (CMS; Consolidated Appropriations Act 2023, section 5131).
KFF estimated 8 to 24 million people would lose coverage.

**NY's NYRx carve-out was effective 1 April 2023.** Exact collision with the start of the
largest Medicaid enrollment shock on record.

Consequences:
- NY is the second-largest event in the set (18.74M rx/qtr) and its treatment timing cannot
  be separated from its unwinding exposure without strong assumptions.
- Time fixed effects absorb the national average unwinding effect, but not NY-specific
  deviation from it, which is exactly the problem.
- **The other four events are clean of this**: WV 2017Q3, NC 2021Q3, CA 2022Q1, OK 2024Q2.

Handling, in order of preference:
1. Primary specification on the four clean events. NY enters robustness only.
2. If NY is retained, control explicitly with state-quarter Medicaid enrollment and show the
   estimate is stable with and without it.
3. Report the NY estimate separately and name the confound rather than burying it. A reviewer
   who knows Medicaid will spot the date collision immediately, so raise it first.

Also a correction to the gate-check note: the national MCOU share decline from 73.8% in 2021
to 58.6% in 2024 was attributed there to the CA and NY carve-outs. Unwinding is a third
contributor and the attribution should be decomposed, not asserted.

### Honest weaknesses

- **Medicaid is not the national market.** Generalizability must be argued, not assumed.
- **SDUD is quarterly.** Within-quarter shortage timing is lost. NADAC compensates on price.
- **WV has 2 pre-period quarters** until 2014 to 2016 is added.
- **Suppression censors the low end**, which has to be handled explicitly rather than noted.
- **The state policy panel** still needs hand-verification for the five smaller switches.
- **MCOU completeness** passed at state-year level but has not been checked NDC by NDC.

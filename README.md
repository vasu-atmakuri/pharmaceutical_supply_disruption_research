# Pharmaceutical supply disruption research

Research on supply disruption in US pharmaceutical markets using public federal data.

## Current paper

**When the Only Supplier Fails: Abrupt Manufacturer Exit and the Absence of Market Repair in
US Generic Drug Markets**

Vasu Atmakuri, Independent Researcher, Dallas TX. ORCID 0009-0007-5955-2466.

Finding: when a sole-supplier manufacturer collapses, 30 to 38% of affected prescription
molecules stop being dispensed entirely, against 0 of 998 control molecules. Replacement entry
occurs for 16%. Therapeutic substitution does not occur. No recovery through eight quarters.

## Data sources, all public, no data use agreement

| source | coverage | notes |
|---|---|---|
| Medicaid State Drug Utilization Data (CMS) | 2014Q1-2026Q1 | 13 files, 5.7 GB, ~57M rows |
| FDA National Drug Code Directory | current | product.txt |
| openFDA bulk NDC | current + discontinued | needed for exited products |

Raw data is not committed. It is public and reproducible from source. See `scripts/` for
download and build steps.

## Repository layout

- `paper/` manuscript drafts
- `results/` result JSON files, one per specification
- `figures/` figures
- `scripts/` analysis pipeline
- `decisions/` research decision record, including rejected candidates and why

## Reproducing

1. Download SDUD annual files from data.medicaid.gov and the two FDA crosswalk files.
2. Run `scripts/` in numeric order.
3. Results are written to `results/`.

## Research decision record

`decisions/` documents candidates that were tested and rejected, with the analysis that
rejected them. Three candidate papers were killed on feasibility before this one was adopted.

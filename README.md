# Pharmaceutical supply disruption research

Measurement work on US drug markets using public federal data. No data use agreement, no
licensed data, no restricted access: every input is downloadable by anyone.

## Current paper

**When a sole supplier is not sole: duplicate market keys, misclassified exits, and what
survives both in US Medicaid drug markets**

Vasu Atmakuri (Independent Researcher, Dallas TX; ORCID 0009-0007-5955-2466) and
Souseelya Kidambi.

The paper asks whether the standard way of counting drug suppliers measures what it is taken to
measure, and finds two errors that operate before any supplier is counted.

1. **The market key is wrong twice over.** Markets are conventionally defined by active
   ingredient and dosage form. Dosage form does not record route of administration, so the form
   string "solution" covers oral, topical, ophthalmic and otic products at once. The ingredient
   half is a free-text string that is not normalised, so one product occupies several keys.
   Correcting both, 379 of 3,295 route-aware keys turn out to be duplicates of another key,
   leaving 2,916 markets. The share of national Medicaid dispensing in markets where one
   labeler holds at least 95 percent falls from 14.71 to 10.54 percent, and 26.7 percent of
   apparent near-sole market-quarters are not near-sole once the market is defined properly.

2. **An observed exit is not a supply disruption.** Of the 19 near-sole-labeler exits the
   corrected panel observes, 2 are a documented supply disruption and those two are one recall
   episode. 8 are explained by something that is not a supply failure: a market-wide regulatory
   withdrawal, 3 prescription-to-over-the-counter and product-generation transitions, one
   firm's withdrawal from the Medicaid Drug Rebate Program with its product still marketed, one
   transfer of marketing rights, and 2 markets whose apparent sole supplier is a misspelled
   ingredient string. In 5 more a labeler absent before the exit supplies the market
   afterwards. 4 remain undetermined.

What survives both corrections is a conditional association: among detected exits, markets
whose departing labeler held at least 95 percent collapse below two percent of baseline
dispensing at 42.1 percent against 0.21 percent among matched risk-set controls.

But the collapse result is concentrated in the exits that are not supply failures. Of the 8
collapses among the 19 observed exits, none is one of the 2 documented supply disruptions. All 3
regulatory transitions collapse, as do the market-wide withdrawal and the rebate-programme
withdrawal. Excluding the 8 exits an outside record explains as something other than a supply
failure leaves 2 collapses in 11 events, or 18.2 percent against the pooled 42.1 percent. The
median replacement ratio tells the same story: 0.00 across all 19 observed exits, 0.47 in the
two documented disruptions.

The headline claim is therefore negative. These data do not support the statement that
sole-supplier markets fail to replace lost volume after a supply disruption, because in the
events where a supply disruption is actually documented, part of the volume was replaced.

## Data sources, all public

| source | coverage | notes |
|---|---|---|
| Medicaid State Drug Utilization Data (CMS) | 2016Q1-2026Q1 | national aggregate rows, ~12 GB of CSVs |
| FDA National Drug Code Directory | current | `product.txt`, used for route, form and labeler name |
| openFDA bulk NDC | current and discontinued | needed for products that have left the market |
| FDA structured active-ingredient data | current | `SUBSTANCENAME`, used to validate the key merges |

Raw data is not committed. It is public and rebuilt from source by the pipeline.

## Repository layout

- `springer/` the manuscript (`manuscript.tex`), its generated tables and macros, and the
  response to the reviewer
- `scripts/` the full pipeline, one stage per file, driven by `run_all.sh`
- `results/` every analysis output, as JSON and CSV, including the per-event manifests
- `figures/` figures, as PDF for the manuscript and PNG for inspection
- `decisions/` research decision record, including candidates that were tested and rejected,
  and `review_history.md`, the round-by-round log of what internal review found and what changed
- `paper/` earlier drafts, kept for provenance

## Reproducing

See `SETUP.md` for the interpreter and package requirements and the expected data layout. Then:

```
PSDR_ROOT=$(pwd) RESEARCH_ROOT=$(dirname $(pwd)) bash scripts/run_all.sh
```

The run executes 30 analysis stages and then 10 checks, and ends with
`ALL STAGES AND CHECKS COMPLETE`. Stages 0 to 6 rebuild the panels from the raw SDUD and FDA
listings and take the bulk of the runtime; the whole run takes roughly 6 to 8 minutes on a warm
machine, and it has to run in a session that stays alive for its duration. Without a TeX distribution the document build is skipped and the run ends with
`ANALYSIS COMPLETE; THE DOCUMENT BUILD WAS SKIPPED`; every analysis number is still produced.

## Why the checks are part of the pipeline

Every number in the manuscript is a generated macro, not a typed figure, and the run refuses to
finish if any of them disagrees with the results it came from. The ten checks assert, among
other things, that each number in the text traces to an analysis output, that the event flow
reconciles event by event, that every macro the manuscript cites is defined, that each stage
reads only files an earlier stage wrote, that no literal number sits in the prose where a
generated macro belongs, and that two runs from the same inputs produce byte-identical outputs. Several of these exist because a hand-typed number in an earlier draft
went stale when the cohort changed, which is the failure mode they are there to prevent.

## Detector specification

Events are detected on a dense calendar grid, with a quarter absent from the data read as zero
dispensing, and with a persistence requirement that the labeler not return to half its own
baseline between four and twelve quarters after the exit. Row-counted windows over the observed
quarters alone find 282 events; calendar windows find 292; the dense grid finds 500; the
persistence requirement removes 67 of those, leaving the 433 the paper uses.
`scripts/detector_variants.py` computes all four and refuses to write its output if the last
one disagrees with the panel's own recorded total.

# Data: what is here, what was deleted, and how to get it back

The analysis consumes about 17 GB of public bulk files. Almost none of that has to be
on disk to reproduce the paper, and in November 2026 it was deleted from the working
machine to recover space. This file records what the pipeline needs, what was removed,
and the exact way back for each group. `results/data_inventory.json` carries the
machine-readable version: every file's name, byte size and SHA-256 at the time the
published results were computed.

## What the pipeline needs

| Input | Size | Status |
|---|---|---|
| `data/sdud_parts/*.parquet` | 12 MB | **committed to this repository** |
| `RESEARCH_ROOT/crosswalk/ndctext.zip` | 11 MB | kept on disk |
| `RESEARCH_ROOT/crosswalk/openfda_ndc.json.zip` | 27 MB | kept on disk |
| `RESEARCH_ROOT/enforcement/` | 32 MB | kept on disk |

That is the whole list. `scripts/ensure_inputs.py` runs first in `run_all.sh` and
extracts `product.txt`, `package.txt` and the openFDA NDC listing from the two zips when
they are not already there, so the extracted copies (300 MB) do not need storing.

The per-year panel parts in `data/sdud_parts` are the aggregated form every panel stage
reads. They are 12 MB and they are in git, which means a clone of this repository plus
the two NDC zips reproduces every number in the paper without downloading anything.

## What was deleted, and how to restore it

| Group | Size | Needed to reproduce the paper? | Restore |
|---|---|---|---|
| SDUD yearly CSVs, 2016 to 2026 | 4.6 GB | No. Only to rebuild the parts, which are committed | `wget -i sdud/dl.txt -P sdud/` |
| SDUD yearly CSVs, 1991 to 2015 | 6.5 GB | No. The panel starts at 2016Q1 | `wget -i sdud/dl_pre2014.txt -P sdud/` and `dl1416.txt` |
| NADAC yearly CSVs | 1.0 GB | No. The spending check is not a pipeline stage; its output is in `results/RESULTS_nadac.json` | yearly files from the NADAC dataset page into `aux/` as `nadac_<year>.csv` |
| DailyMed SPL documents | 2.1 GB | No. The establishment analysis is not a pipeline stage; its output is in `results/RESULTS_establishments.json` | set ids are kept in `RESEARCH_ROOT/aux_spl_setids_full.txt`; fetch each as `https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/<setid>.xml` |
| Extracted crosswalk files | 0.3 GB | Yes, and they are rebuilt automatically | `scripts/ensure_inputs.py`, which runs as part of `run_all.sh` |
| Virtualenvs (three projects) | 1.6 GB | No | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |

Source pages, in case a URL list is lost:

- SDUD: <https://data.medicaid.gov/dataset/state-drug-utilization-data>
- NADAC: <https://data.medicaid.gov/dataset/dfa2ab14-06c2-457a-9e36-5cb1e4d906c6>
- FDA NDC directory: <https://www.accessdata.fda.gov/cder/ndctext.zip>
- openFDA NDC listing: <https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip>
- openFDA enforcement: <https://download.open.fda.gov/drug/enforcement/drug-enforcement-0001-of-0001.json.zip>
- DailyMed SPL: <https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm>

## The one caveat that matters

CMS revises published SDUD files in place. That is why the 2020 and later filenames
carry an `updatedJuly2026` suffix. A file downloaded again later is **not** guaranteed to
be byte identical to the one these results were computed from, so rebuilding the parts
from a fresh download can legitimately move a number.

This is why the parts are committed rather than the raw files, and why
`results/data_inventory.json` records a SHA-256 for every raw file as it stood when the
paper was built: a re-download can be checked against it. If the hashes differ, the
honest move is to report both, not to overwrite the published numbers.

## If a reviewer asks for new analysis

Nothing in the first list needs restoring. Clone, extract, run:

```
git clone https://github.com/vasu-atmakuri/pharmaceutical_supply_disruption_research
cd pharmaceutical_supply_disruption_research
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PSDR_ROOT=$(pwd) RESEARCH_ROOT=$(dirname $(pwd)) bash scripts/run_all.sh
```

Only four kinds of request need a download first: rebuilding the panel from raw files,
extending it to a newer SDUD release, anything about pre-2016 history, and anything
about NADAC prices or SPL establishments. The table above says what to fetch for each.

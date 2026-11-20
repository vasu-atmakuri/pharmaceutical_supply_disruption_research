# Running the pipeline

One command rebuilds the panel from the raw SDUD and FDA files, regenerates every
figure and every reported number, recompiles the manuscript and runs eight checks:

    bash scripts/run_all.sh

## Interpreter

`run_all.sh` uses, in order of preference:

1. `$PY`, if you set it;
2. `.venv/bin/python` in this folder, if it exists;
3. `python3` from your `PATH`.

On macOS with Homebrew, `python3` refuses `pip install` under PEP 668, so a
repo-local virtual environment is the simplest route:

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt

`run_all.sh` then finds `.venv` on its own. `.venv/` is already in `.gitignore`.

## Requirements

Python: duckdb, numpy, matplotlib (see `requirements.txt`).

On `PATH`, outside pip:

- `pdflatex` and `bibtex` from a TeX distribution (MacTeX, TeX Live)
- `pdfinfo` and `pdftotext` from poppler (`brew install poppler`)

`scripts/check_environment.py` runs first and reports everything missing at once,
with the exact install command for the interpreter actually in use. The pipeline
stops there rather than failing several stages in.

## Data

`RESEARCH_ROOT` is the folder holding `sdud/` and `crosswalk/`; it defaults to the
parent of this repository. Stage 0 aggregates the raw SDUD year files into
`$RESEARCH_ROOT/sdud_parts/`, skips any part already built, and so costs nothing
after the first run. `SDUD_PARTS` overrides where those parts live.

## What a successful run prints

    errors: 0, pages: 27

then eight check results, ending with:

    THE PIPELINE IS CLOSED: every intermediate is produced before it is read
    EVERY STAGE RESOLVES ITS PATHS FROM THE ENVIRONMENT
    EVERY PROMISED ARTIFACT IS TRACKED
    ALL STOCHASTIC STAGES REPRODUCIBLE (tree restored)

    ALL STAGES AND CHECKS COMPLETE

If any stage fails, the run stops at that stage and names it.

## Pinning a submission to a commit

The paper's code-availability statement cites `results/build_provenance.json` as the version a
reader should clone. That file records the commit the build ran from and whether the working
tree was clean at the time, and `check_released_files.py` fails if it does not match `HEAD`.
Because writing it changes the tree, a submission build is three steps:

```
git add -A && git commit -m "<message>"
PSDR_ROOT=$(pwd) RESEARCH_ROOT=$(dirname $(pwd)) bash scripts/run_all.sh
git add -A && git commit --amend --no-edit
```

The third step folds the regenerated provenance and outputs into the same commit, so the commit
the file names is the commit that contains it. Push that commit before submitting: the
repository a reviewer clones has to be the one the paper describes.

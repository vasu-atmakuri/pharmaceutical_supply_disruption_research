"""Preflight: confirm the interpreter and tools the pipeline needs are present.

The run failed at stage 2a with ModuleNotFoundError after stages 0 and 1 had already
spent time, because duckdb was installed and numpy was not. A preflight costs a second
and reports everything missing at once, with the command to fix it.
"""
import importlib.util, shutil, sys   # importlib.util must be imported explicitly:
# 'import importlib' alone leaves importlib.util undefined on some builds, which is
# how this preflight crashed on the first machine it was actually needed on
# Required: without these no analysis stage can run.
MODS=[("duckdb","duckdb"),("numpy","numpy"),("matplotlib","matplotlib")]
# Optional: these build and inspect the PDF. Their absence skips the compile and the
# two checks that read a PDF; every analysis stage and the other six checks still run.
# A full TeX distribution is a large install, so the pipeline does not demand one.
BINS=[("pdflatex","a TeX distribution, e.g. MacTeX or TeX Live"),
      ("bibtex","a TeX distribution"),
      ("pdfinfo","poppler, e.g. brew install poppler"),
      ("pdftotext","poppler, e.g. brew install poppler")]
miss_m=[p for m,p in MODS if not importlib.util.find_spec(m)]
miss_b=[(b,h) for b,h in BINS if not shutil.which(b)]
print(f"interpreter: {sys.executable}")
print(f"python: {sys.version.split()[0]}")
print("required:")
for m,p in MODS:
    spec=importlib.util.find_spec(m); v=""
    if spec:
        try: v=" "+importlib.import_module(m).__version__
        except Exception: pass
    print(f"  {'ok ' if spec else 'MISSING'} {m}{v}")
print("optional (document build):")
for b,h in BINS:
    print(f"  {'ok ' if shutil.which(b) else 'absent '} {b}")
if miss_m:
    print("\nPREFLIGHT FAILED: a required package is missing")
    print(f"  {sys.executable} -m pip install {' '.join(miss_m)}")
    sys.exit(1)
if miss_b:
    print("\nENVIRONMENT OK for the analysis; the document build will be skipped")
    for b,h in miss_b: print(f"  {b} is not on PATH: install {h}")
    print("  To compile the manuscript here, install the tools above and re-run.")
    print("  poppler alone (small) enables one of the two skipped checks.")
    sys.exit(0)
print("\nENVIRONMENT OK")

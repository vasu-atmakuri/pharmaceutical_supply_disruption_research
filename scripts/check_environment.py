"""Preflight: confirm the interpreter and tools the pipeline needs are present.

The run failed at stage 2a with ModuleNotFoundError after stages 0 and 1 had already
spent time, because duckdb was installed and numpy was not. A preflight costs a second
and reports everything missing at once, with the command to fix it.
"""
import importlib, shutil, sys
MODS=[("duckdb","duckdb"),("numpy","numpy"),("matplotlib","matplotlib")]
BINS=[("pdflatex","a TeX distribution, e.g. MacTeX or TeX Live"),
      ("bibtex","a TeX distribution"),
      ("pdfinfo","poppler, e.g. brew install poppler"),
      ("pdftotext","poppler, e.g. brew install poppler")]
miss_m=[p for m,p in MODS if not importlib.util.find_spec(m)]
miss_b=[(b,h) for b,h in BINS if not shutil.which(b)]
print(f"interpreter: {sys.executable}")
print(f"python: {sys.version.split()[0]}")
for m,p in MODS:
    s=importlib.util.find_spec(m)
    v=""
    if s:
        try: v=" "+importlib.import_module(m).__version__
        except Exception: pass
    print(f"  {'ok ' if s else 'MISSING'} {m}{v}")
for b,h in BINS:
    print(f"  {'ok ' if shutil.which(b) else 'MISSING'} {b}")
if miss_m or miss_b:
    print("\nPREFLIGHT FAILED")
    if miss_m:
        print(f"  install the missing Python packages:\n"
              f"    {sys.executable} -m pip install {' '.join(miss_m)}")
    for b,h in miss_b:
        print(f"  {b} is not on PATH: install {h}")
    sys.exit(1)
print("\nENVIRONMENT OK")

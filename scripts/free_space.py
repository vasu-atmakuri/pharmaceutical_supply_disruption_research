"""Delete the inputs that a run regenerates, and report what that recovered.

Three crosswalk files are extracted from two archives at the start of every run and are
300 MB; the panels and the DuckDB scratch files land in the system temporary folder and
are rebuilt by the panel stages. None of it needs to survive between runs, which matters
on a machine that is short of disk.

This removes only files that scripts/ensure_inputs.py or a pipeline stage puts back. It
never touches the archives, the committed panel parts, anything under results/, or any
raw download. Run it after a build, or whenever the disk is tight.
"""
import glob, os, shutil, sys

R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D=os.environ.get("RESEARCH_ROOT") or os.path.dirname(R)

TARGETS=[(f"{D}/crosswalk/product.txt", "extracted from ndctext.zip"),
         (f"{D}/crosswalk/package.txt", "extracted from ndctext.zip"),
         (f"{D}/crosswalk/drug-ndc-0001-of-0001.json", "extracted from openfda_ndc.json.zip")]
TARGETS+= [(p,"rebuilt by the panel stages") for p in sorted(glob.glob("/tmp/*.parquet"))]
TARGETS+= [(p,"python bytecode") for p in sorted(glob.glob(f"{R}/scripts/__pycache__"))]

freed=0; gone=0
for p,why in TARGETS:
    if not os.path.exists(p): continue
    n=sum(os.path.getsize(os.path.join(dp,f)) for dp,_,fs in os.walk(p) for f in fs) \
      if os.path.isdir(p) else os.path.getsize(p)
    try:
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    except OSError as e:
        print(f"   could not remove {os.path.basename(p)}: {e}"); continue
    freed+=n; gone+=1
    print(f"   removed {os.path.relpath(p, D) if p.startswith(D) else p} "
          f"({n/2**20:.0f} MiB, {why})")

print(f"\n{gone} paths removed, {freed/2**20:.0f} MiB recovered.")
print("The next run puts all of it back: ensure_inputs.py extracts the crosswalk files "
      "and the panel stages rebuild the parquet.")

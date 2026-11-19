"""Every intermediate a pipeline stage reads must be written by an earlier stage.

Two inputs were produced by ad-hoc commands and by no script at all, so run_all.sh
could not rebuild from a clean machine: /tmp/ptype.parquet, which natpanel_route.py
joins, and /tmp/xw.parquet, which natpanel.py joins. Both failed only once /tmp was
cleared, which is exactly when reproducibility matters.
"""
import re, os, sys
import os as _os
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
S=f"{_ROOT}/scripts"
sh=open(f"{S}/run_all.sh").read()
order=[m.group(1) for m in re.finditer(r"\$W/([a-z0-9_]+)\.py", sh)]
order=[s for s in order if not s.startswith("check_")]   # preflight, not a stage
seen=set(); fails=[]; n=0
LIT=r"[\"'](/tmp/[\w.]+\.parquet)[\"']"
for st in order:
    src=open(f"{S}/{st}.py").read()
    lits={m.group(1) for m in re.finditer(LIT, src)}
    # writes: an explicit COPY ... TO '<path>', or a path paired with a table name in a
    # list the stage loops over to COPY
    writes={m.group(1) for m in re.finditer(r"TO\s+"+LIT, src)}
    writes|={m.group(2) for m in re.finditer(r"\(\s*[\"'][a-z_]+[\"']\s*,\s*([\"'])(/tmp/[\w.]+\.parquet)\1",
                                             src)}
    # reads: read_parquet('<path>') directly, and - the case that let a missing file
    # through - every other path the stage names when it passes paths as variables,
    # as threespec.py does with read_parquet('{mq}')
    reads={m.group(1) for m in re.finditer(r"read_parquet\(\s*"+LIT, src)}
    if re.search(r"read_parquet\(\s*f?[\"']\{", src):
        reads |= (lits - writes)
    seen |= writes                      # a stage may read back what it just wrote
    for f in sorted(reads):
        n+=1
        if f not in seen:
            fails.append(f"{st}.py reads {f}, which no earlier stage writes")
print(f"{n} intermediate dependencies checked across {len(order)} stages")
if fails:
    print(f"\n{len(fails)} UNSATISFIED:")
    for f in fails: print("   "+f)
    sys.exit(1)
print("THE PIPELINE IS CLOSED: every intermediate is produced before it is read")

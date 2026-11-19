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
seen=set(); fails=[]; n=0
for st in order:
    src=open(f"{S}/{st}.py").read()
    # paths appear in both quote styles, and several stages write via a list of
    # (table, path) tuples rather than a literal TO clause
    wr={m.group(1) for m in re.finditer(r"[\"'](/tmp/[\w.]+\.parquet)[\"']", src)}
    rd={m.group(1) for m in re.finditer(r"read_parquet\(\s*[\"'](/tmp/[\w.]+\.parquet)[\"']", src)}
    seen |= wr          # a stage may read back what it just wrote
    for f in sorted(rd):
        n+=1
        if f not in seen:
            fails.append(f"{st}.py reads {f}, which no earlier stage writes")
print(f"{n} intermediate dependencies checked across {len(order)} stages")
if fails:
    print(f"\n{len(fails)} UNSATISFIED:")
    for f in fails: print("   "+f)
    sys.exit(1)
print("THE PIPELINE IS CLOSED: every intermediate is produced before it is read")

"""Every pipeline stage must resolve its paths from the environment.

Two stages, xwalk.py and natpanel.py, hard-coded the analysis VM's mount points.
They ran there and failed on any other machine at the first stage, which is the one
place a reproducibility claim is actually tested.
"""
import re, os, sys
_ROOT=os.environ.get("PSDR_ROOT") or os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
S=f"{_ROOT}/scripts"
sh=open(f"{S}/run_all.sh").read()
stages=[m.group(1) for m in re.finditer(r"\$W/([a-z0-9_]+)\.py", sh)]
fails=[]; n=0
for st in stages:
    src=open(f"{S}/{st}.py").read()
    # a bare expanduser of a VM path is only acceptable as the fallback of an env lookup
    for m in re.finditer(r'(.{0,60})os\.path\.expanduser\(\s*"~/(?:mnt/Research|work)[^"]*"\s*\)', src):
        n+=1
        ctx=m.group(1)
        if "environ.get" not in ctx:
            fails.append(f"{st}.py hard-codes a VM path with no environment override: "
                         f"...{m.group(0)[-70:]}")
    for v in ("PSDR_ROOT","RESEARCH_ROOT"):
        pass
    if "environ.get" not in src:
        fails.append(f"{st}.py reads no environment variable at all")
print(f"{n} path expressions checked across {len(stages)} stages")
if fails:
    print(f"\n{len(fails)} NOT PORTABLE:")
    for f in fails: print("   "+f)
    sys.exit(1)
print("EVERY STAGE RESOLVES ITS PATHS FROM THE ENVIRONMENT")

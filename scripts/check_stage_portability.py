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
stages=[s for s in stages if not s.startswith("check_")]   # preflight, not a stage
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

# A fixed-path persistent database couples one run to the next. A /tmp/xw.duckdb
# written by duckdb 2.0 could not be opened by 1.5, which failed the run at stage 1a.
for st in stages:
    src=open(f"{S}/{st}.py").read()
    for m in re.finditer(r"duckdb\.connect\(\s*(['\"])([^'\"]+)\1", src):
        n+=1
        fails.append(f"{st}.py opens a persistent database at the fixed path "
                     f"{m.group(2)}; use a per-run temporary directory")

# A fallback must not reference a name that does not exist. Two stages had
# "or __ROOT+''", which raises NameError the moment the environment is unset, and
# worked only because run_all.sh happens to export the variable.
import ast
for st in stages:
    src=open(f"{S}/{st}.py").read()
    try: tree=ast.parse(src)
    except SyntaxError as e:
        n+=1; fails.append(f"{st}.py does not parse: {e.msg} line {e.lineno}"); continue
    defined=set(dir(__builtins__)) | {"__file__","__name__"}
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            for a in node.names: defined.add((a.asname or a.name).split(".")[0])
        if isinstance(node,ast.Assign):
            for tgt in node.targets:
                for nm in ast.walk(tgt):
                    if isinstance(nm,ast.Name): defined.add(nm.id)
            if isinstance(node.value,ast.BoolOp) and isinstance(node.value.op,ast.Or):
                n+=1
                for nm in ast.walk(node.value.values[-1]):
                    if isinstance(nm,ast.Name) and nm.id not in defined:
                        fails.append(f"{st}.py line {node.lineno}: fallback references "
                                     f"undefined name {nm.id!r}")

print(f"{n} path expressions checked across {len(stages)} stages")
if fails:
    print(f"\n{len(fails)} NOT PORTABLE:")
    for f in fails: print("   "+f)
    sys.exit(1)
print("EVERY STAGE RESOLVES ITS PATHS FROM THE ENVIRONMENT")

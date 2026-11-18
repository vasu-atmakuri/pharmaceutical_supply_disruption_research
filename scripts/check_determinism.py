"""Re-run every stochastic stage and require byte-identical results.

A fixed RNG seed is not sufficient. The same draws index different elements when
the input array order changes, and Counter.most_common breaks ties by insertion
order. Both produced numbers that moved between runs of this pipeline, so the
guarantee is enforced here rather than assumed.
"""
import hashlib, json, os, subprocess, sys
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
R=_ROOT
W=_ROOT+"/scripts"   # the stages this re-runs live beside this file
STAGES=[("inference.py",["inference_normalized.json"]),
        ("reclass_multi.py",["reclassification_rules.json"]),
        ("national_impact.py",["national_impact.json"]),
        ("concentration_abc.py",["concentration_abc.json"]),
        ("threespec.py",["three_specifications.json"]),
        ("transition.py",["sole_event_transition.csv"]),
        ("validate_normalization.py",["normalization_validation.json"]),
        ("recovery_censored.py",["recovery_censored.json"]),
        ("sensitivities.py",["sensitivities.json"])]
def h(f):
    p=f"{R}/results/{f}"
    if f.endswith(".csv"):
        return hashlib.sha256(open(p,"rb").read()).hexdigest()[:16]
    return hashlib.sha256(json.dumps(json.load(open(p)),sort_keys=True).encode()).hexdigest()[:16]
fails=[]
for script,outs in STAGES:
    before={f:h(f) for f in outs}
    p=subprocess.run(["python3",f"{W}/{script}"],capture_output=True,text=True)
    if p.returncode!=0:
        fails.append(f"{script} failed to re-run: {p.stderr.strip().splitlines()[-1:]}" ); continue
    for f in outs:
        after=h(f)
        status="same" if after==before[f] else "CHANGED"
        print(f"  {script:<28} {f:<34} {status}")
        if after!=before[f]:
            fails.append(f"{script} -> {f} changed on re-run ({before[f]} then {after})")
if fails:
    print(f"\n{len(fails)} NOT REPRODUCIBLE:")
    for f in fails: print("   "+f)
    sys.exit(1)
print("ALL STOCHASTIC STAGES REPRODUCIBLE")

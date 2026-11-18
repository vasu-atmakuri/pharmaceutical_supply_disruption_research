"""Re-run every stochastic stage and require byte-identical results.

A fixed RNG seed is not sufficient. The same draws index different elements when
the input array order changes, and Counter.most_common breaks ties by insertion
order. Both produced numbers that moved between runs of this pipeline, so the
guarantee is enforced here rather than assumed.
"""
import hashlib, json, os, subprocess, sys
R=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
W=os.path.expanduser("~/work")
STAGES=[("inference.py",["inference_normalized.json"]),
        ("validate_normalization.py",["normalization_validation.json"]),
        ("recovery_censored.py",["recovery_censored.json"]),
        ("sensitivities.py",["sensitivities.json"])]
def h(f):
    return hashlib.sha256(json.dumps(json.load(open(f"{R}/results/{f}")),sort_keys=True).encode()).hexdigest()[:16]
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

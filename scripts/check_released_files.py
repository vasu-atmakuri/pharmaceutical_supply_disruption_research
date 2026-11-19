"""Every artifact the manuscript says it releases must be tracked in git.

The manuscript's data-availability statement and several passages promise specific
files. A blanket *.csv rule in .gitignore silently excluded all four event-level
result files, so the repository was public and the promised manifests were not in it.
Nothing in the number checks could catch that.
"""
import os, re, subprocess, sys
import os as _os
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
R=_ROOT
TEX=open(f"{R}/springer/manuscript.tex").read()
tracked=set(subprocess.run(["git","-C",R,"ls-files"],capture_output=True,text=True).stdout.split())
fails=[]; n=0
def ck(l,c,d=""):
    global n; n+=1
    if not c: fails.append(f"{l}: {d}")

# the files the paper promises, by name as the text or the scripts refer to them
PROMISED=["results/near_sole_event_flow.csv","results/sole_event_transition.csv",
          "results/event_cause_classification.csv","results/event_level_cohort_manifest.csv",
          "results/three_specifications.json","results/reclassification_rules.json",
          "results/normalization_validation.json","results/inference_normalized.json",
          "results/recovery_censored.json","results/manuscript_numbers.json",
          "results/market_key_normalization_map.json","results/recall_match_level.json",
          "scripts/run_all.sh","springer/manuscript.tex"]
for f in PROMISED:
    ck(f"{f} is tracked in git", f in tracked,
       "present on disk but not tracked" if os.path.exists(f"{R}/{f}") else "missing entirely")

# every pipeline stage run_all.sh invokes must be tracked too
sh=open(f"{R}/scripts/run_all.sh").read()
for m in re.finditer(r"\$W/([a-z0-9_]+\.py)",sh):
    ck(f"stage {m.group(1)} is tracked", f"scripts/{m.group(1)}" in tracked)

# the manuscript must not promise a file that is absent
ck("manuscript names the repository URL", "github.com/vasu-atmakuri" in TEX)

print(f"{n} release checks run")
if fails:
    print(f"\n{len(fails)} FAILED:")
    for f in fails: print("   "+f)
    sys.exit(1)
print("EVERY PROMISED ARTIFACT IS TRACKED")

"""Orphan-number audit.

verify_manuscript.py checks that numbers I remembered to list are present. It is
blind to numbers I forgot to update. This does the complement: it extracts every
number in the manuscript and flags any that appears in none of the results files
and is not on an explicit whitelist of legitimate non-result values. It is how
'429', '350 controls from 43 markets' and 'fourteen sets' survived three rounds.
"""
import json, os, re, sys, glob
ROOT=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
TEX=open(f"{ROOT}/springer/manuscript.tex").read()
TEX=re.sub(r"(?m)^\s*%.*$","",TEX)
# citation keys, ORCIDs and emails carry digits that are not results
TEX=re.sub(r"\\cite\{[^}]*\}"," ",TEX)
TEX=re.sub(r"\\orcidlink\{[^}]*\}"," ",TEX)
TEX=re.sub(r"\\email\{[^}]*\}"," ",TEX)
TEX=re.sub(r"\\label\{[^}]*\}"," ",TEX)
TEX=re.sub(r"\\ref\{[^}]*\}"," ",TEX)

vals=set()
def harvest(o):
    if isinstance(o,dict):
        for v in o.values(): harvest(v)
    elif isinstance(o,(list,tuple)):
        for v in o: harvest(v)
    elif isinstance(o,bool): pass
    elif isinstance(o,(int,float)):
        for f in (f"{o:.0f}",f"{o:.1f}",f"{o:.2f}",f"{o:.3f}",f"{o:.4f}",
                  f"{o*100:.0f}",f"{o*100:.1f}",f"{o*100:.2f}",f"{abs(o):.2f}"):
            vals.add(f.lstrip("-"))
        try: vals.add(f"{int(round(o)):,}".replace(",","{,}"))
        except Exception: pass
for f in glob.glob(f"{ROOT}/results/*.json"):
    try: harvest(json.load(open(f)))
    except Exception: pass
for f in glob.glob(f"{ROOT}/results/*.csv"):
    for line in open(f).read().split("\n")[1:]:
        for tok in re.split(r"[,\s]+",line):
            if re.fullmatch(r"0\d{3,4}",tok or ""): vals.add(tok)   # NDC labeler codes keep leading zeros
            if re.fullmatch(r"-?\d+(\.\d+)?",tok or ""):
                x=float(tok)
                for g in (f"{x:.0f}",f"{x:.1f}",f"{x:.2f}",f"{x*100:.1f}"): vals.add(g.lstrip("-"))

# legitimate non-result numbers: years, quarters, thresholds, structural constants
WHITE={"2016","2017","2018","2019","2020","2021","2022","2023","2024","2025","2026","1991",
 "0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20",
 "25","35","40","50","60","65","90","95","99","100","0.02","0.05","0.5","0.95","1.0","2.0",
 "200","0.00","1.00","41","5.80","28","32","24","0.25","0.75","5.5","7.8","10","0.1","0.3"}
nums=set()
for m in re.finditer(r"(?<![A-Za-z\\])(\d{1,3}(?:\{,\}\d{3})+|\d+(?:\.\d+)?)",TEX):
    nums.add(m.group(1))
orphans=sorted(n for n in nums if n not in vals and n.replace("{,}","") not in vals and n not in WHITE)
# spelled-out counts that previously went stale
WORDS={"fourteen":"13 sole-labeler exits","eleven":"contradicted groups","twenty-one":"","nineteen":"labelers"}
wordhits=[w for w in WORDS if re.search(rf"\b{w}\b",TEX,re.I)]
print(f"{len(nums)} distinct numbers in manuscript.tex; {len(vals)} values available from results files")
if orphans:
    print(f"\n{len(orphans)} numbers not found in any results file (check each):")
    for o in orphans:
        ctx=re.search(rf".{{0,60}}(?<![A-Za-z\\]){re.escape(o)}.{{0,40}}",TEX,re.S)
        c=" ".join(ctx.group(0).split()) if ctx else ""
        print(f"   {o:<12} ...{c}...")
else:
    print("\nno orphan numbers")
if wordhits:
    print(f"\nspelled-out counts present, confirm each is still correct: {', '.join(wordhits)}")
sys.exit(0)

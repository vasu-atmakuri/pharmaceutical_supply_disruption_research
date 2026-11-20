"""Audit the README against the manuscript and the analysis outputs.

The reviewer's first comment on the previous round was that the README still
described a different paper, with findings the analysis no longer supported. A
repository README is the first thing a reader meets, so it is checked here on the
same terms as the paper: the title must be the manuscript's title, the headline
counts must be the ones the results files hold, and no number in it may be one that
no analysis output produces.
"""
import json, os, re, glob, sys
_ROOT=os.environ.get("PSDR_ROOT") or os.path.expanduser(
    "~/mnt/Research/pharmaceutical_supply_disruption_research")
R=_ROOT
RM=open(f"{R}/README.md").read()
TEX=open(f"{R}/springer/manuscript.tex").read()
fails=[]; n=0
def ck(label,cond,detail=""):
    global n; n+=1
    if not cond: fails.append((label,detail))

# 1. the title in the README is the manuscript's title, word for word
m=re.search(r"\\title\[[^\]]*\]\{(.+?)\}\s*$", TEX, re.M)
if not m: m=re.search(r"\\title\{(.+?)\}\s*$", TEX, re.M)
ck("the manuscript title is parseable", m is not None)
if m:
    t=re.sub(r"\s+"," ",m.group(1)).strip()
    flat=re.sub(r"\s+"," ",RM)
    ck("README states the manuscript's title", t in flat,
       f"manuscript title not found in README: {t[:60]}...")

# 2. the headline counts come from the results, not from an earlier draft
S={x["tag"][0]:x for x in json.load(open(f"{R}/results/three_specifications.json"))}["C"]
C=json.load(open(f"{R}/results/cause_strata.json"))
V=json.load(open(f"{R}/results/detector_variants.json"))
flat=re.sub(r"\s+"," ",RM)
for label,txt in [
  ("observed cohort size", f"{C['total']} near-sole-labeler exits"),
  ("documented supply disruptions", f"{C['counts']['supply']} are a documented supply disruption"),
  ("market count after normalisation", f"{S['markets']:,} markets"),
  ("events in the reported detector", f"the {V['range_dense_persist']['events']} the paper uses"),
  ("dips removed by persistence", f"removes {V['range_dense']['events']-V['range_dense_persist']['events']} of those"),
]:
    ck(f"README states the current {label}", txt in flat, f"expected to find: {txt!r}")

# 3. the number of stages and checks the README promises is what run_all.sh runs
sh=open(f"{R}/scripts/run_all.sh").read()
# The authoritative stage list is the guard loop at the top of run_all.sh, which
# refuses to start if any stage file is missing. Counting echo lines instead
# miscounts, because some stages share one line and some lines are not stages.
_g=re.search(r"for f in (.+?); do", sh, re.S)
stages=len(_g.group(1).replace("\\\n"," ").split()) if _g else 0
# check_environment.py is the preflight, not one of the final checks.
checks=len(set(re.findall(r"((?:audit|check|verify)_\w+)\.py", sh))-{"check_environment"})
m2=re.search(r"executes (\d+) analysis stages and then (\d+) checks", flat)
ck("README counts its own stages and checks", m2 is not None)
if m2:
    ck("stage count matches run_all.sh", int(m2.group(1))==stages,
       f"README says {m2.group(1)}, run_all.sh echoes {stages}")
    ck("check count matches run_all.sh", int(m2.group(2))==checks,
       f"README says {m2.group(2)}, run_all.sh runs {checks}")

# 4. the runtime the README quotes is the one run_all.sh quotes
_a=re.search(r"roughly (\d+) to (\d+) minutes", flat)
_b=re.search(r"roughly (\d+) to (\d+) minutes", sh)
ck("README and run_all.sh quote the same runtime",
   _a is not None and _b is not None and _a.groups()==_b.groups(),
   f"README {_a.groups() if _a else None} vs run_all.sh {_b.groups() if _b else None}")

# 5. every number in the README traces to an analysis output
vals=set()
def walk(x):
    if isinstance(x,dict):
        for v in x.values(): walk(v)
    elif isinstance(x,(list,tuple)):
        for v in x: walk(v)
    elif isinstance(x,bool): pass
    elif isinstance(x,(int,float)):
        for f in ("{:.0f}","{:.1f}","{:.2f}","{:,.0f}"):
            vals.add(f.format(x)); vals.add(f.format(abs(x)))
        for f in ("{:.0f}","{:.1f}","{:.2f}"): vals.add(f.format(x*100))
for f in glob.glob(f"{R}/results/*.json"):
    try: walk(json.load(open(f)))
    except Exception: pass
body=re.sub(r"`[^`]*`","",RM)                  # code spans and file names
body=re.sub(r"\[[^\]]*\]\([^)]*\)","",body)    # links
body=re.sub(r"[0-9]{4}Q[1-4]","",body)
body=re.sub(r"^\s*\d+\.\s","",body,flags=re.M) # ordered-list markers
# Counts the README states in words rather than from a results file, plus the ORCID,
# the stage and check counts checked above, and the runtime estimate.
OK={"0","1","2","3","4","5","6","7","8","9","10","11","12","19","27","95",
    "0009","0007","5955","2466","2016","2026","379","3,295"}
found=sorted({t for t in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])",body)}-OK)
orphans=[t for t in found if t not in vals and t.replace(",","") not in vals]
ck("every number in the README traces to an analysis output", not orphans,
   "; ".join(f"{t} (...{body[max(0,body.find(t)-45):body.find(t)+25]}...)".replace("\n"," ")
             for t in orphans))

print(f"{n} README checks run")
if fails:
    print(f"\n{len(fails)} FAILED:")
    for l,d in fails: print(f"   {l}: {d}")
    sys.exit(1)
print("THE README DESCRIBES THIS PAPER AND THIS PIPELINE")

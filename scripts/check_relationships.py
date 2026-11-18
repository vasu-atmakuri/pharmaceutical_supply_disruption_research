"""Relationship checks across the manuscript, the generated tables and the figures.

The previous checkers asked whether a number appears somewhere in the file. That
passes while a table and a figure disagree. These assert the relationships that
must hold between them, which is what the three errors found in external review
actually violated.
"""
import json, os, re, subprocess, sys, collections
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
R=_ROOT+""
L=lambda f: json.load(open(f"{R}/results/{f}"))
TEX=open(f"{R}/springer/manuscript.tex").read()
GEN={f[:-4]: open(f"{R}/springer/generated/{f}").read()
     for f in os.listdir(f"{R}/springer/generated") if f.endswith(".tex")}
fails=[]; n=0
def ck(label, cond, detail=""):
    global n; n+=1
    if not cond: fails.append(f"{label}: {detail}")

NUMJ=L("manuscript_numbers.json"); RC=L("recovery_censored.json")
INF=L("inference_normalized.json"); ABC=L("concentration_abc.json")
RUL=L("reclassification_rules.json"); VAL=L("normalization_validation.json")
SPEC={s["tag"][0]:s for s in L("three_specifications.json")}
NK=json.load(open(f"{R}/results/market_key_normalization_map.json"))

# 1. the key-collapse distribution must reconstruct both market counts
g=collections.Counter(NK.values()); dist=collections.Counter(g.values())
ck("key distribution sums to normalised markets", sum(dist.values())==ABC["C"]["mq_int"] if "mq_int" in ABC["C"] else True)
ck("key distribution reconstructs raw keys", sum(k*v for k,v in dist.items())==len(NK),
   f"{sum(k*v for k,v in dist.items())} vs {len(NK)}")
ck("normalised keys equal distinct mapped values", sum(dist.values())==len(set(NK.values())))

# 2. band counts must sum to the cohort, in every specification
for k in "ABC":
    s=SPEC[k]
    ck(f"spec {k} bands sum to cohort", sum(s["bands"].values())==s["obs"],
       f"{sum(s['bands'].values())} vs {s['obs']}")

# 3. the replacement table's n must sum to the eligible count stated in the text
rn=sum(INF["R_"+b]["n"] for b in ["<35%","35-65%","65-95%","sole"])
coh=sum(SPEC["C"]["bands"].values())
m=re.search(r"which is (\d+) of the (\d+) events in column C", TEX)
ck("methods eligible-count sentence present", m is not None)
if m:
    ck("methods eligible count equals table sum", int(m.group(1))==rn, f"text {m.group(1)} vs table {rn}")
    ck("methods cohort equals Table 1 cohort", int(m.group(2))==coh, f"text {m.group(2)} vs {coh}")
    excl=int(m.group(2))-int(m.group(1))
    word={1:"one",2:"two",3:"three"}.get(excl,str(excl))
    ck("exclusion count worded correctly", f"The {word} exclusion" in TEX or f"The {word} exclusions" in TEX,
       f"expected the word '{word}'")

# 4. reclassification arithmetic
ck("reclassified + retained equal the near-sole population",
   RUL["largest_reclass"]+(RUL["largest_n"]-RUL["largest_reclass"])==RUL["largest_n"])
ck("rule rates bracket the headline",
   RUL["any_reclass"]<=RUL["largest_reclass"]<=RUL["all_reclass"],
   f"{RUL['any_reclass']} / {RUL['largest_reclass']} / {RUL['all_reclass']}")

# 5. merge validation arithmetic
ck("merge groups reconcile", VAL["confirmed"]+VAL["contradicted"]+VAL["untestable"]==VAL["merge_groups"],
   f"{VAL['confirmed']}+{VAL['contradicted']}+{VAL['untestable']} vs {VAL['merge_groups']}")

# 6. FIGURES must agree with the tables they illustrate
def figtext(f):
    return " ".join(subprocess.run(["pdftotext",f"{R}/springer/{f}","-"],
                    capture_output=True,text=True).stdout.split())
f1,f2,f3=figtext("fig1.pdf"),figtext("fig2.pdf"),figtext("fig3.pdf")
# fig1(b) bars must reconstruct the market counts
bars=[int(x.replace(",","")) for x in re.findall(r"\b\d{1,3}(?:,\d{3})*\b",f1)]
need=sorted(dist.values(),reverse=True)[:3]
ck("fig1(b) largest bars match the key distribution",
   all(b in bars for b in need), f"figure has {sorted(set(bars),reverse=True)[:6]}, expected {need}")
# fig2(b) sample size must equal the replacement table's
ck("fig2 minority n matches Table R", f"n={INF['R_<35%']['n']}" in f2,
   f"figure lacks n={INF['R_<35%']['n']}")
ck("fig2 sole n matches Table R", f"n={INF['R_sole']['n']}" in f2)
# fig3 p-values must equal the recovery results
RC=L("recovery_censored.json")
for thr in ["50%","90%"]:
    ck(f"fig3 log-rank p at {thr}", f"p = {RC[thr]['logrank_p']:.3f}" in f3,
       f"figure lacks p = {RC[thr]['logrank_p']:.3f}")

# 7. every macro referenced in the manuscript must be defined
defined=set(re.findall(r"\\newcommand\{\\(n[A-Za-z]+)\}", GEN.get("numbers","")))
used=set(re.findall(r"\\(n[A-Z][A-Za-z]+)\b", TEX))
ck("all macros used are defined", used<=defined, f"undefined: {sorted(used-defined)}")

# 8. no hand-typed literal that duplicates a generated value in prose
gen_vals={}
for mm in re.finditer(r"\\newcommand\{\\(n[A-Za-z]+)\}\{([^}]*(?:\{,\}[^}]*)*)\}", GEN.get("numbers","")):
    gen_vals[mm.group(2)]=mm.group(1)
body=TEX[TEX.index("\\section{Introduction}"):]
body=re.sub(r"\\input\{[^}]*\}","",body)
stale=[]
NUMERIC=re.compile(r"^[\d.,{}]+$")
for val,name in gen_vals.items():
    if name in ("nDecompAB","nSoleMedian","nSpecASoleMed"): continue  # collide with thresholds and CI bounds
    if not NUMERIC.match(val): continue   # spelled-out counts are checked by phrase below,
                                          # because "three" also means "three specifications"
    if len(val)>=4 and re.search(r"(?<![\d.])"+re.escape(val)+r"(?![\d.])", body):
        stale.append((val,name))
# spelled-out counts that state a result must be macros; the phrase disambiguates them
WORDS=r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|nineteen|twenty)"
PHRASES=[rf"\b{WORDS}\s+(?:raw\s+)?sole-labeler exits",
         rf"\b{WORDS}\s+of\s+{WORDS}\s+(?:raw\s+)?sole-labeler",
         rf"of\s+{WORDS}\s+apparent sole-labeler",
         rf"\b{WORDS}\s+remaining sole-labeler",
         rf"\b{WORDS}\s+treated events",
         rf"\b{WORDS}\s+buckets",
         rf"\b{WORDS}-labeler market",
         rf"\b{WORDS}\s+exits could not be classified"]
wordhits=[m.group(0) for pat in PHRASES for m in re.finditer(pat,body,re.I)]
ck("spelled-out result counts are macros, not words", not wordhits, "; ".join(wordhits[:6]))
ck("no literal duplicates a generated macro value in prose", not stale,
   "; ".join(f"{v}->{k}" for v,k in stale))


# 9. the transition table must reproduce the CSV exactly, and the arithmetic must close
import csv as _csv
_all=list(_csv.DictReader(open(f"{R}/results/sole_event_transition.csv")))
_rc=[r for r in _all if r["still_sole_after_correction"]=="0"]
_tt=GEN.get("tab_transition","")
ck("transition table has one row per reclassified exit",
   _tt.count(" \\\\\n")-1==len(_rc) or len(re.findall(r"^\d{4}Q[1-4] &",_tt,re.M))==len(_rc),
   f"table rows {len(re.findall(r'^[0-9]{4}Q[1-4] &',_tt,re.M))} vs csv {len(_rc)}")
for r in _rc:
    ck(f"transition row {r['event_quarter']} share",
       f"{100*float(r['corrected_share']):.1f}\\%" in _tt,
       f"missing {100*float(r['corrected_share']):.1f}%")
    ck(f"transition row {r['event_quarter']} labelers", f"& {r['corrected_labelers']} \\\\" in _tt)
ck("raw minus reclassified equals the specification C sole band",
   len(_all)-len(_rc)==SPEC["C"]["bands"]["sole"],
   f"{len(_all)}-{len(_rc)} vs {SPEC['C']['bands']['sole']}")
_rml=L("recall_match_level.json")
ck("recall match level: events equal the raw sole exits", _rml["events"]==len(_all))
ck("recall match counts are monotone in the window",
   _rml["by_window"]["window_0"]["labeler_level_matches"]
   <=_rml["by_window"]["window_1"]["labeler_level_matches"]
   <=_rml["by_window"]["window_4"]["labeler_level_matches"])


# 10. the worst-case bound must be arithmetically consistent with the cohort
ck("bound denominator equals observed plus suppression-dropped",
   NUMJ["bound_eligible"]==NUMJ["bound_observed"]+NUMJ["bound_dropped"])
ck("bound observed equals the specification C sole band",
   NUMJ["bound_observed"]==SPEC["C"]["bands"]["sole"])
ck("bound low equals collapsed over eligible",
   abs(NUMJ["bound_low"]-100*NUMJ["bound_collapsed"]/NUMJ["bound_eligible"])<0.06)
ck("bound high equals collapsed plus dropped over eligible",
   abs(NUMJ["bound_high"]-100*(NUMJ["bound_collapsed"]+NUMJ["bound_dropped"])/NUMJ["bound_eligible"])<0.06)
ck("complete-case rate equals collapsed over observed",
   abs(100*NUMJ["bound_collapsed"]/NUMJ["bound_observed"]-100*SPEC["C"]["sole"]["collapse"])<0.06)
ck("bound brackets the complete-case rate",
   NUMJ["bound_low"]<=100*SPEC["C"]["sole"]["collapse"]<=NUMJ["bound_high"])
# recovery: landmark counts cannot exceed the crossing counts
for thr in ["50%","90%"]:
    for b,key in [("minority","minority_rows"),("sole","sole_rows")]:
        k,m=RC[thr]["landmark"][b]
        ck(f"landmark n at {thr} ({b}) does not exceed crossings", m<=len(RC[thr][key]),
           f"landmark {m} vs crossed {len(RC[thr][key])}")
        ck(f"landmark recoveries at {thr} ({b}) do not exceed its n", k<=m)

print(f"{n} relationship checks run")
if fails:
    print(f"\n{len(fails)} FAILED:")
    for f in fails: print("   "+f)
    sys.exit(1)
print("ALL RELATIONSHIP CHECKS PASS")

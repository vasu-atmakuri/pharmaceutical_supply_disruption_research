"""How many raw sole-labeler exits carry a contemporaneous recall, at each matching level.

The manuscript reports the ingredient-level count as an artefact of matching on a
shared ingredient rather than on the departing firm. That number is therefore a
result and is computed here rather than asserted in the text.

Window: a recall initiated within four quarters either side of the exit quarter,
which is the window used for the labeler-level classification.
"""
import json, os, csv, re
R=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results")
ENF=os.path.expanduser("~/mnt/Research/enforcement/drug-enforcement-0001-of-0001.json")

def tq(year,month):                      # panel epoch: tq=1 is 1991Q1
    return (year-1991)*4 + (month-1)//3 + 1
def parse_q(label):                      # "2024Q2" -> tq
    y,q=label.split("Q"); return (int(y)-1991)*4+int(q)

recs=json.load(open(ENF,encoding="utf-8",errors="replace"))["results"]
R4=[]
for r in recs:
    of=r.get("openfda") or {}
    d=str(r.get("recall_initiation_date") or r.get("report_date") or "")
    if len(d)!=8: continue
    t=tq(int(d[:4]),int(d[4:6]))
    labs={n.split("-")[0].zfill(5) for n in (of.get("product_ndc") or []) if "-" in n}
    ing=set()
    for f in ("substance_name","generic_name"):
        for v in (of.get(f) or []):
            ing |= {w for w in re.split(r"[^A-Z]+",v.upper()) if len(w)>3}
    R4.append((t,labs,ing))
print(f"{len(R4)} recall records with a usable date")

STOP={"HYDROCHLORIDE","SODIUM","SULFATE","TARTRATE","MALEATE","MESYLATE","ACETATE",
      "CHLORIDE","POTASSIUM","CALCIUM","PHOSPHATE","CITRATE","BROMIDE","SUCCINATE",
      "FUMARATE","BESYLATE","TOSYLATE","OXALATE","NITRATE","CARBONATE","GLUCONATE"}
rows=list(csv.DictReader(open(f"{R}/sole_event_transition.csv")))
# The comparison that matters holds the window fixed and varies only the matching
# key. A wide window makes the labeler level look permissive for a reason that has
# nothing to do with matching level: large generic labelers have recalls in most
# quarters, so any window of several quarters matches nearly every exit.
res={}
for W in (0,1,4):
    ing_hit=lab_hit=both=0; detail=[]
    for r in rows:
        t=parse_q(r["event_quarter"]); lab=r["departing_labeler"].zfill(5)
        key=r["corrected_market"].split(" | ")[0]
        ings={w for w in re.split(r"[^A-Z]+",key.upper()) if len(w)>3} - STOP
        win=[x for x in R4 if abs(x[0]-t)<=W]
        L=any(lab in x[1] for x in win)
        I=any(ings & x[2] for x in win) if ings else False
        lab_hit+=L; ing_hit+=I; both+= (L and I)
        detail.append(dict(event=r["event_quarter"],market=key,
                           labeler_level=int(L),ingredient_level=int(I)))
    res[f"window_{W}"]=dict(window_quarters=W,ingredient_level_matches=ing_hit,
                            labeler_level_matches=lab_hit,both=both,detail=detail)
    print(f"  window +/-{W}q: ingredient-level {ing_hit:2d}, labeler-level {lab_hit:2d}")
out=dict(events=len(rows),by_window=res,
         ingredient_level_matches=res["window_0"]["ingredient_level_matches"],
         labeler_level_matches=res["window_0"]["labeler_level_matches"])
json.dump(out,open(f"{R}/recall_match_level.json","w"),indent=1)
print(f"\nheadline (same-quarter match, of {len(rows)} raw sole-labeler exits): "
      f"ingredient-level {out['ingredient_level_matches']}, "
      f"labeler-level {out['labeler_level_matches']}")

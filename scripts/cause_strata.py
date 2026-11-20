import duckdb, numpy as np, json, os, csv
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
MQ={}; LMQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_v2.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
for l,m,t,r in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_v2.parquet')").fetchall(): LMQ.setdefault((m,l),{})[t]=r
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_v2.parquet')").fetchall()
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"
inwin={m:v for m,v in first.items() if LO<=v[0]<HI}
OBS=[m for m,v in inwin.items() if basec(m,v[0]) is not None
     and any(MQ[m].get(v[0]+k) is not None for k in range(1,7))]
sole=sorted([m for m in OBS if inwin[m][1]>=.95],key=lambda m:inwin[m][0])
# Classification from public records, graded by how well the cause is established
# rather than by whether the cause is a supply failure. The eight classes and what
# each requires are documented in exit_causes.py, which is the single place they are
# declared; display_names.py holds their table labels. An Rx-to-OTC switch does not
# by itself end Medicaid coverage, so a switch that overlaps an exit is recorded as
# an alternative explanation, not a verified one.
# See results/event_cause_classification.csv for the per-event evidence.
# Classification lives in exit_causes.py, keyed on the exact event, and the
# successor-labeler signal comes from exit_evidence_audit.py. Matching on an
# ingredient substring here once gave Assertio's diclofenac the evidence from Teva's,
# and a growing cohort makes that failure mode certain rather than possible.
from exit_causes import classify, declared_keys, record
import json as _json
_aud={}
_ap=_ROOT+"/results/exit_evidence_audit.json"
if os.path.exists(_ap):
    for x in _json.load(open(_ap)):
        _aud[(x["market"],x["event_quarter"],x["departing_labeler"])]=x
CLS={}
for m in sole:
    t,s_,lab=inwin[m]; k=(m,cal(t),lab)
    CLS[m]=classify(m,cal(t),lab,
                    new_labeler_appears=_aud.get(k,{}).get("new_labeler_appears",False))
REC={}
for m in sole:
    t,s_,lab=inwin[m]; k=(m,cal(t),lab)
    REC[m]=record(m,cal(t),lab,
                  new_labeler_appears=_aud.get(k,{}).get("new_labeler_appears",False))
_present={(m,cal(inwin[m][0]),inwin[m][2]) for m in sole}
_drifted=declared_keys()-_present
if _drifted:
    raise SystemExit("exit_causes.py declares events that are no longer in the cohort, "
                     "so its evidence would go unreported:\n  " +
                     "\n  ".join(repr(x) for x in sorted(_drifted)))
def R(m):
    t,s,dl=inwin[m]
    db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
    if db<=0: return None
    ob=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
    return (op-ob)/db
rows=[]
for m in sole:
    t,s,lab=inwin[m]; bl=basec(m,t)
    rows.append(dict(market=m,event_quarter=cal(t),departing_labeler=lab,baseline_rx=round(bl,1),
                     post_over_base=round(np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)])/bl,4),
                     replacement_ratio=round(R(m),4),cause_class=CLS[m][0],cause_evidence=CLS[m][1],
                     record_short=REC[m][0],evidence_link=REC[m][1],record_source=REC[m][2]))
out=_ROOT+"/results/event_cause_classification.csv"
with open(out,"w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
def rep(tag,sel):
    v=np.array([R(m) for m in sel])
    bw=np.array([basec(m,inwin[m][0]) for m in sel])
    print(f"{tag:<46}n={len(v):>3}  median R={np.median(v):>5.2f}  P(R<0.02)={np.mean(v<.02):>5.1%}  "
          f"vol-wtd R={np.sum(v*bw)/np.sum(bw):>5.2f}")
print()
rep("ALL near-sole (normalized)",sole)
# The strata now follow the eight classes. The primary contrast is between exits a
# supply-chain reading can claim and exits explained by regulation, labeler identity,
# coverage or a measurement error.
_NOT_SUPPLY=("withdrawal","transition","coverage","transfer","artefact")
rep("  excluding everything not a supply failure  [PRIMARY]",
    [m for m in sole if CLS[m][0] not in _NOT_SUPPLY])
rep("  documented product-and-firm supply only",[m for m in sole if CLS[m][0]=="supply"])
rep("  market-wide regulatory withdrawal only",[m for m in sole if CLS[m][0]=="withdrawal"])
rep("  regulatory transitions only",[m for m in sole if CLS[m][0]=="transition"])
rep("  Medicaid coverage withdrawal only",[m for m in sole if CLS[m][0]=="coverage"])
rep("  marketing-rights transfer only",[m for m in sole if CLS[m][0]=="transfer"])
rep("  measurement artefact (misspelled key) only",[m for m in sole if CLS[m][0]=="artefact"])
rep("  supply continued by another labeler",[m for m in sole if CLS[m][0]=="continued"])
rep("  undetermined cause only",[m for m in sole if CLS[m][0]=="undetermined"])
print()
for m in sole:
    print(f"  {CLS[m][0]:<13} R={R(m):>5.2f}  {cal(inwin[m][0])}  {m.split(' | ')[0][:44]}")
import json as _j, collections as _c
_cnt=_c.Counter(CLS[m][0] for m in sole)
def _st(sel):
    if not sel: return None
    v=np.array([R(m) for m in sel]); bw=np.array([basec(m,inwin[m][0]) for m in sel])
    return dict(n=int(len(v)),median=float(np.median(v)),p_lt_002=float(np.mean(v<.02)),
                volwtd=float(np.sum(v*bw)/np.sum(bw)))
_out=dict(counts=dict(_cnt), total=len(sole),
  all=_st(sole),
  ex_not_supply=_st([m for m in sole if CLS[m][0] not in
                     ("withdrawal","transition","coverage","transfer","artefact")]),
  supply=_st([m for m in sole if CLS[m][0]=="supply"]),
  withdrawal=_st([m for m in sole if CLS[m][0]=="withdrawal"]),
  transition=_st([m for m in sole if CLS[m][0]=="transition"]),
  coverage=_st([m for m in sole if CLS[m][0]=="coverage"]),
  transfer=_st([m for m in sole if CLS[m][0]=="transfer"]),
  artefact=_st([m for m in sole if CLS[m][0]=="artefact"]),
  continued=_st([m for m in sole if CLS[m][0]=="continued"]),
  undetermined=_st([m for m in sole if CLS[m][0]=="undetermined"]),
  )
if sum(_cnt.values())!=len(sole):
    raise SystemExit("cause classification does not cover every event")
_j.dump(_out,open(_ROOT+"/results/cause_strata.json","w"),indent=1)
print("wrote results/cause_strata.json  counts:",dict(_cnt))
print("\nwrote results/event_cause_classification.csv")

# ---- collapse by class, not only replacement by class ----
# The reviewer's point, and it is correct: the pooled collapse rate answers a
# different question from the per-class one. A collapse in a market the regulator
# emptied, or in a market whose key is a misspelling, is not evidence about supply
# resilience. This records which classes the collapses actually fall in.
def _coll(m):
    t=inwin[m][0]; bl=basec(m,t)
    post=[MQ[m].get(t+k) for k in range(1,7)]
    if all(v is None for v in post): return None
    return 1 if np.mean([0.0 if v is None else v for v in post])<0.02*bl else 0
CL={}
for cls in sorted({CLS[m][0] for m in sole}):
    sel=[m for m in sole if CLS[m][0]==cls]
    cv=[_coll(m) for m in sel]; cv=[x for x in cv if x is not None]
    CL[cls]={"n":len(sel),"n_collapse_obs":len(cv),"collapsed":int(sum(cv)),
             "rate":(float(np.mean(cv)) if cv else None)}
_all=[_coll(m) for m in sole]; _all=[x for x in _all if x is not None]
_expl={"withdrawal","transition","coverage","transfer","artefact"}
_rem=[m for m in sole if CLS[m][0] not in _expl]
_rv=[_coll(m) for m in _rem]; _rv=[x for x in _rv if x is not None]
_sup=[m for m in sole if CLS[m][0]=="supply"]
_sv=[_coll(m) for m in _sup]; _sv=[x for x in _sv if x is not None]
OUTC={"by_class":CL,
      "pooled":{"n":len(_all),"collapsed":int(sum(_all)),"rate":float(np.mean(_all))},
      "excluding_explained":{"n":len(_rv),"collapsed":int(sum(_rv)),
                             "rate":float(np.mean(_rv))},
      "documented_supply":{"n":len(_sv),"collapsed":int(sum(_sv)),
                           "rate":(float(np.mean(_sv)) if _sv else None)},
      "note":("Three populations, not three estimates of one thing. The pooled rate is "
              "every observed near-sole exit. The second excludes the classes an outside "
              "record explains as something other than a supply failure. The third is the "
              "documented supply disruptions alone, and it is two events from one episode.")}
json.dump(OUTC,open(_ROOT+"/results/cause_collapse.json","w"),indent=1,sort_keys=True)
print("\ncollapse by class:")
for cls in sorted(CL,key=lambda k:-CL[k]["collapsed"]):
    d=CL[cls]
    print(f"  {cls:<14}{d['collapsed']:>2} of {d['n']:>2}" +
          (f"  {100*d['rate']:>5.1f}%" if d["rate"] is not None else "      ---"))
print(f"  pooled {OUTC['pooled']['collapsed']} of {OUTC['pooled']['n']}, "
      f"excluding explained {OUTC['excluding_explained']['collapsed']} of "
      f"{OUTC['excluding_explained']['n']}, documented supply "
      f"{OUTC['documented_supply']['collapsed']} of {OUTC['documented_supply']['n']}")
print("wrote results/cause_collapse.json")

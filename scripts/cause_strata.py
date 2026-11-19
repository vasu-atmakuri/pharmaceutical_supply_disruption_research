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
# Classification from public records, graded by the strength of the evidence rather
# than by whether the cause is a supply failure. Four levels:
#   supply      - a shortage or recall record naming this product AND this firm
#   withdrawal  - a documented market-wide regulatory action removing the product
#   transition  - a documented regulatory action overlapping the exit, but the records
#                 do not establish that THIS firm left because of it (ingredient-level
#                 evidence only). An Rx-to-OTC switch does not by itself end Medicaid
#                 coverage, so this is an alternative explanation, not a verified one.
#   undetermined- no record found for this firm and period
# See results/event_cause_classification.csv for the per-event evidence.
CLS={}
for m in sole:
    k=m.upper()
    if "RANITIDINE" in k: CLS[m]=("withdrawal","FDA requested withdrawal of all ranitidine, 1 Apr 2020 (NDMA); market-wide and firm-independent")
    elif "ALCAFTADINE" in k: CLS[m]=("transition","Rx-to-OTC switch approved for the brand Dec 2021, retail Mar 2022; no firm-level record of why this labeler left")
    elif "OLOPATADINE" in k: CLS[m]=("transition","Rx-to-OTC switch for the brand from Feb 2020; no firm-level record of why this labeler left")
    elif "VARENICLINE" in k: CLS[m]=("supply","Pfizer nitrosamine recall 2021; FDA recorded a varenicline shortage")
    elif "DICLOFENAC" in k: CLS[m]=("supply","ASHP shortage Feb 2019 to Aug 2020; Teva named, no reason given")
    elif "DORZOLAMIDE" in k: CLS[m]=("supply","ASHP dorzolamide shortage lists Leading; no reason given")
    else: CLS[m]=("undetermined","no shortage, withdrawal, recall or switch record found for this firm and period")
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
                     replacement_ratio=round(R(m),4),cause_class=CLS[m][0],cause_evidence=CLS[m][1]))
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
# The primary stratum removes only the documented market-wide withdrawal, which is the
# one event whose absence of replacement is certainly the intended regulatory outcome.
rep("  excluding documented withdrawal  [PRIMARY]",[m for m in sole if CLS[m][0]!="withdrawal"])
rep("  excluding withdrawal and transitions",[m for m in sole if CLS[m][0] not in ("withdrawal","transition")])
rep("  documented product-and-firm supply only",[m for m in sole if CLS[m][0]=="supply"])
rep("  documented market-wide withdrawal only",[m for m in sole if CLS[m][0]=="withdrawal"])
rep("  regulatory-transition-associated only",[m for m in sole if CLS[m][0]=="transition"])
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
  ex_withdrawal=_st([m for m in sole if CLS[m][0]!="withdrawal"]),
  ex_withdrawal_transition=_st([m for m in sole if CLS[m][0] not in ("withdrawal","transition")]),
  supply=_st([m for m in sole if CLS[m][0]=="supply"]),
  withdrawal=_st([m for m in sole if CLS[m][0]=="withdrawal"]),
  transition=_st([m for m in sole if CLS[m][0]=="transition"]),
  undetermined=_st([m for m in sole if CLS[m][0]=="undetermined"]))
if sum(_cnt.values())!=len(sole):
    raise SystemExit("cause classification does not cover every event")
_j.dump(_out,open(_ROOT+"/results/cause_strata.json","w"),indent=1)
print("wrote results/cause_strata.json  counts:",dict(_cnt))
print("\nwrote results/event_cause_classification.csv")

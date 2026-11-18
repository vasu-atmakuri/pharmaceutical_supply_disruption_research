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
# Verified classification from public records (see results/event_cause_classification.csv)
CLS={}
for m in sole:
    k=m.upper()
    if "RANITIDINE" in k: CLS[m]=("non-supply","FDA requested withdrawal of all ranitidine, 1 Apr 2020 (NDMA)")
    elif "ALCAFTADINE" in k: CLS[m]=("non-supply","Rx-to-OTC switch: OTC approved Dec 2021, retail Mar 2022")
    elif "OLOPATADINE" in k: CLS[m]=("non-supply","Rx-to-OTC switch: Pataday OTC from Feb 2020")
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
rep("ALL sole (normalized)",sole)
rep("  excluding verified non-supply  [PRIMARY]",[m for m in sole if CLS[m][0]!="non-supply"])
rep("  verified supply-side only",[m for m in sole if CLS[m][0]=="supply"])
rep("  undetermined cause only",[m for m in sole if CLS[m][0]=="undetermined"])
rep("  verified non-supply only",[m for m in sole if CLS[m][0]=="non-supply"])
print()
for m in sole:
    print(f"  {CLS[m][0]:<13} R={R(m):>5.2f}  {cal(inwin[m][0])}  {m.split(' | ')[0][:44]}")
print("\nwrote results/event_cause_classification.csv")

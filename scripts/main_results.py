import duckdb, numpy as np, collections, json, os, csv
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
MQ={}; LMQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_norm.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
for l,m,t,r in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_norm.parquet')").fetchall(): LMQ.setdefault((m,l),{})[t]=r
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_norm.parquet')").fetchall()
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
first={}
for m,l,t,s in sorted(SL,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"
inwin={m:v for m,v in first.items() if LO<=v[0]<HI}
COH=[m for m,v in inwin.items() if basec(m,v[0]) is not None]
OBS=[m for m in COH if any(MQ[m].get(inwin[m][0]+k) is not None for k in range(1,7))]
band=lambda s:"<35%" if s<.35 else ("35-65%" if s<.65 else ("65-95%" if s<.95 else "sole"))
print(f"baseline-complete={len(COH)}  with post obs={len(OBS)}")
print("bands:",dict(collections.Counter(band(inwin[m][1]) for m in OBS)))
def R(m):
    t,s,dl=inwin[m]
    db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
    if db<=0: return None
    ob=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
    return (op-ob)/db
print(f"\n{'band':<10}{'n':>5}{'median R':>11}{'mean R':>10}{'P(R>=0.5)':>11}{'P(R<0.02)':>11}")
for b in ["<35%","35-65%","65-95%","sole"]:
    v=[R(m) for m in OBS if band(inwin[m][1])==b]; v=np.array([x for x in v if x is not None])
    if len(v): print(f"{b:<10}{len(v):>5}{np.median(v):>11.2f}{np.mean(v):>10.2f}{np.mean(v>=.5):>10.1%}{np.mean(v<.02):>11.1%}")
print("\n=== SOLE EVENTS, normalized panel ===")
sole=sorted([m for m in OBS if inwin[m][1]>=.95],key=lambda m:inwin[m][0])
for m in sole:
    t,s,lab=inwin[m]; bl=basec(m,t)
    post=np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)])
    print(f"{cal(t)} lab={lab} base={bl:>9.0f} post/base={post/bl:>5.2f} R={R(m):>6.2f} :: {m[:66]}")
json.dump({"cohort_baseline":len(COH),"cohort_obs":len(OBS),
           "sole":[{"market":m,"t":cal(inwin[m][0]),"lab":inwin[m][2],
                    "base":round(basec(m,inwin[m][0]),1),"R":round(R(m),4)} for m in sole]},
    open(os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/normalized_main_results.json"),"w"),indent=2)

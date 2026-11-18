import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
LMQ={}
for m,l,t,r in con.execute("SELECT mkt,lab,tq,rx FROM read_parquet('/tmp/lmq_nat.parquet')").fetchall(): LMQ.setdefault((m,l),{})[t]=r
S={}
for (m,l),d in LMQ.items():
    for t,v in d.items():
        if v and v>0: S.setdefault((m,t),set()).add(l)
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def band(s): return "under 35%" if s<.35 else ("35 to 95%" if s<.95 else "sole >=95%")
LOr=YMIN-B0+2
ev=[(m,v[0],v[1],v[2]) for m,v in first.items() if v[0]>=LOr and basec(m,v[0]) is not None]
print(f"events with any post-event follow-up: {len(ev)}",flush=True)
# ---------- C2: FIXED HORIZONS with numbers at risk ----------
print("\n=== C2  FIXED-HORIZON RECOVERY, only events with that much follow-up ===",flush=True)
print(f"  {'horizon':>8}  {'band':<14}{'at risk':>9}{'any entry':>11}{'regain 50%':>12}{'regain 90%':>12}",flush=True)
FH={}
for H in (4,8,12):
    for b in ["under 35%","35 to 95%","sole >=95%"]:
        sel=[(m,t,s,l) for m,t,s,l in ev if band(s)==b and t+H<=TMAX]
        if not sel: continue
        ent=sum(1 for m,t,s,l in sel if any(S.get((m,t+k),set())-S.get((m,t-1),set()) for k in range(0,H+1)))
        r50=sum(1 for m,t,s,l in sel if any((MQ[m].get(t+k) or 0)>=0.5*basec(m,t) for k in range(1,H+1)))
        r90=sum(1 for m,t,s,l in sel if any((MQ[m].get(t+k) or 0)>=0.9*basec(m,t) for k in range(1,H+1)))
        FH[f"{H}q_{b}"]=dict(n=len(sel),entry=ent/len(sel),r50=r50/len(sel),r90=r90/len(sel))
        print(f"  {H:>6}q  {b:<14}{len(sel):>9}{ent/len(sel):>11.0%}{r50/len(sel):>12.0%}{r90/len(sel):>12.0%}",flush=True)
    print(flush=True)
# ---------- C3: AT-RISK DEFINITION ----------
print("=== C3  RESTRICTED TO MARKETS THAT ACTUALLY FELL BELOW THE THRESHOLD ===",flush=True)
print("   a market 'recovers' only if it first dropped below 50% (resp. 90%) of baseline\n",flush=True)
print(f"  {'horizon':>8}  {'band':<14}{'fell<50%':>10}{'of those regained':>19}{'fell<90%':>10}{'regained':>10}",flush=True)
AR={}
for H in (4,8,12):
    for b in ["under 35%","35 to 95%","sole >=95%"]:
        sel=[(m,t,s,l) for m,t,s,l in ev if band(s)==b and t+H<=TMAX]
        if not sel: continue
        f50=[];f90=[]
        for m,t,s,l in sel:
            bl=basec(m,t)
            drop50=next((k for k in range(1,H+1) if (MQ[m].get(t+k) or 0)<0.5*bl),None)
            if drop50 is not None:
                back=any((MQ[m].get(t+k) or 0)>=0.5*bl for k in range(drop50+1,H+1)); f50.append(back)
            drop90=next((k for k in range(1,H+1) if (MQ[m].get(t+k) or 0)<0.9*bl),None)
            if drop90 is not None:
                back=any((MQ[m].get(t+k) or 0)>=0.9*bl for k in range(drop90+1,H+1)); f90.append(back)
        AR[f"{H}q_{b}"]=dict(n50=len(f50),rec50=float(np.mean(f50)) if f50 else None,
                             n90=len(f90),rec90=float(np.mean(f90)) if f90 else None)
        s50=f"{np.mean(f50):.0%}" if f50 else "n/a"; s90=f"{np.mean(f90):.0%}" if f90 else "n/a"
        print(f"  {H:>6}q  {b:<14}{len(f50):>10}{s50:>19}{len(f90):>10}{s90:>10}",flush=True)
    print(flush=True)
# ---------- C5: DEFICIT SPLIT ----------
print("=== C5  CUMULATIVE DEFICIT SPLIT: detection window vs after it ===",flush=True)
print("   detection window is t+0..t+3 (part of the event definition); t+4.. is not\n",flush=True)
print(f"  {'band':<14}{'n (12q)':>9}{'deficit t+0..t+3':>19}{'deficit t+4..t+11':>20}{'share after':>13}",flush=True)
DS={}
for b in ["under 35%","35 to 95%","sole >=95%"]:
    sel=[(m,t,s,l) for m,t,s,l in ev if band(s)==b and t+11<=TMAX]
    if not sel: continue
    d1=[];d2=[]
    for m,t,s,l in sel:
        bl=basec(m,t)
        a=sum(max(bl-(MQ[m].get(t+k) or 0.0),0) for k in range(0,4))/bl
        c=sum(max(bl-(MQ[m].get(t+k) or 0.0),0) for k in range(4,12))/bl
        d1.append(a); d2.append(c)
    DS[b]=dict(n=len(sel),det=float(np.median(d1)),after=float(np.median(d2)))
    tot=np.median(d1)+np.median(d2)
    print(f"  {b:<14}{len(sel):>9}{np.median(d1):>18.1f}q{np.median(d2):>19.1f}q{np.median(d2)/tot if tot else 0:>12.0%}",flush=True)
# ---------- C9: bootstrap CI on volume-weighted R ----------
print("\n=== C9  VOLUME-WEIGHTED REPLACEMENT RATIO with bootstrap CI and leave-one-out ===",flush=True)
LO,HI=YMIN-B0+2,TMAX-6
ev6=[(m,v[0],v[1],v[2]) for m,v in first.items() if LO<=v[0]<=HI and basec(m,v[0]) is not None
     and any(MQ[m].get(v[0]+k) is not None for k in range(1,7))]
def pair(m,t,dl):
    db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
    ob=np.mean([(MQ[m][t+k] or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
    return (db,op-ob) if db>0 else None
rng=np.random.default_rng(55)
print(f"  {'band':<14}{'n':>4}{'vol-wtd R':>11}{'95% CI (bootstrap)':>24}{'leave-one-out range':>24}",flush=True)
VW={}
for b in ["under 35%","35 to 95%","sole >=95%"]:
    ps=[pair(m,t,l) for m,t,s,l in ev6 if band(s)==b]; ps=[p for p in ps if p]
    if len(ps)<3: continue
    A=np.array(ps); vw=A[:,1].sum()/A[:,0].sum()
    bs=[]
    for _ in range(20000):
        i=rng.integers(0,len(A),len(A)); bs.append(A[i,1].sum()/A[i,0].sum())
    loo=[ (np.delete(A[:,1],i).sum()/np.delete(A[:,0],i).sum()) for i in range(len(A))]
    VW[b]=dict(n=len(A),vw=float(vw),ci=[float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))],
               loo=[float(min(loo)),float(max(loo))])
    print(f"  {b:<14}{len(A):>4}{vw:>11.2f}   [{np.percentile(bs,2.5):>6.2f}, {np.percentile(bs,97.5):>6.2f}]"
          f"   [{min(loo):>6.2f}, {max(loo):>6.2f}]",flush=True)
json.dump(dict(fixed_horizon=FH,at_risk=AR,deficit_split=DS,volweighted=VW),
  open(os.path.expanduser("~/mnt/Research/RESULTS_round5.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_round5.json",flush=True)

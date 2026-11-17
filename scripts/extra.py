import duckdb, numpy as np, json, os
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}; SP={}
for m,t,v in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_mf.parquet')").fetchall(): MQ.setdefault(m,{})[t]=v
try:
    for m,t,v in con.execute("SELECT mol,tq,amt FROM read_parquet('/tmp/molq_mf.parquet')").fetchall(): SP.setdefault(m,{})[t]=v
except Exception as e: print("no spend col:",e,flush=True)
S={}
for m,l,t in con.execute("SELECT mol,lab,tq FROM read_parquet('/tmp/lmq_mf.parquet') WHERE rx>0").fetchall(): S.setdefault((m,t),set()).add(l)
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; LO,HI=YMIN+8,TMAX-6
SL=[(m,t,s) for m,t,s in con.execute("SELECT mol,t,shr FROM read_parquet('/tmp/sl_mf.parquet')").fetchall() if LO<=t<=HI]
first={}
for m,t,s in sorted(SL,key=lambda x:x[1]):
    if m not in first: first[m]=(t,s)
treated=set(first)
ctl=[m for m in MQ if m not in treated and len([t for t in MQ[m] if MQ[m][t] and MQ[m][t]>0 and t>=YMIN])>=34
     and np.mean([v for v in MQ[m].values() if v])>=400]
rng=np.random.default_rng(31); td=[t for t,_ in first.values()]
def feat(sel,getT,src=MQ,thr=0.02):
    z=[];l=[]
    for m in sel:
        t=getT(m); s=src.get(m,{})
        if not (LO<=t<=HI): continue
        pre=[s.get(t+k) for k in range(-8,-4)]
        if any(v is None or v<=0 for v in pre): continue
        post=[s.get(t+k) for k in range(1,7)]
        if all(v is None for v in post): continue
        post=[0.0 if v is None else v for v in post]
        z.append(1.0 if np.mean(post)<=thr*np.mean(pre) else 0.0); l.append(np.mean(np.log1p(post))-np.mean(np.log1p(pre)))
    return np.array(z),np.array(l)
sole=[m for m in first if first[m][1]>=.95]
print("\n=== 1. CESSATION THRESHOLD SENSITIVITY (sole band) ===",flush=True)
print("  threshold   n   treated   control",flush=True)
for thr in (0.01,0.02,0.05,0.10,0.20):
    z,l=feat(sole,lambda m:first[m][0],thr=thr); cz,_=feat(ctl,lambda m:int(rng.choice(td)),thr=thr)
    print(f"   <= {thr:>4.0%}    {len(l):>3}    {z.mean():>5.1%}    {cz.mean():>5.1%}",flush=True)
print("\n=== 2. REMAINING SUPPLIER COUNT AFTER THE LOSS ===",flush=True)
_,cl=feat(ctl,lambda m:int(rng.choice(td)))
print("  remaining at t+1    n   cessation   intensive",flush=True)
rem={}
for lo,hi,nm in [(0,1,"0"),(1,2,"1"),(2,4,"2 to 3"),(4,99,"4 or more")]:
    sel=[m for m in first if lo<=len(S.get((m,first[m][0]+1),set()))<hi]
    z,l=feat(sel,lambda m:first[m][0])
    if len(l)<3: continue
    rem[nm]=dict(n=int(len(l)),collapse=float(z.mean()),pct=float(100*(np.exp(l.mean()-cl.mean())-1)))
    print(f"  {nm:<18}{len(l):>4}    {z.mean():>5.1%}    {100*(np.exp(l.mean()-cl.mean())-1):>+7.1f}%",flush=True)
print("\n=== 3. SPENDING vs VOLUME (price check) ===",flush=True)
if SP and any(v for d in SP.values() for v in d.values()):
    for nm,sel in [("sole >=95%",sole),("minor <35%",[m for m in first if first[m][1]<.35])]:
        _,lv=feat(sel,lambda m:first[m][0]); _,ls=feat(sel,lambda m:first[m][0],src=SP)
        _,cv=feat(ctl,lambda m:int(rng.choice(td))); _,cs=feat(ctl,lambda m:int(rng.choice(td)),src=SP)
        print(f"  {nm:<12} volume {100*(np.exp(lv.mean()-cv.mean())-1):>+7.1f}%   spending {100*(np.exp(ls.mean()-cs.mean())-1):>+7.1f}%   n={len(lv)}",flush=True)
else: print("  spending column not in panel, rebuilding needed",flush=True)
print("\n=== 4. MDE / POWER, sole band ===",flush=True)
ph=[]
for _ in range(1500):
    s2=list(rng.choice(ctl,size=24,replace=False)); _,b=feat(s2,lambda m:int(rng.choice(td)))
    if len(b)>5: ph.append(b.mean())
ph=np.array(ph); sd=ph.std()
print(f"  placebo SD at n=24: {sd:.4f} log points",flush=True)
print(f"  MDE (2.80 x SD):    {100*(np.exp(2.80*sd)-1):+.1f}%",flush=True)
print(f"  observed effect:    -98.9%  => {abs(np.log(0.011))/sd:.1f} x SD",flush=True)
json.dump(dict(remaining=rem,placebo_sd=float(sd)),open(os.path.expanduser("~/mnt/Research/firm_exit_FINAL_robustness.json"),'w'),indent=2)
print("\nwrote Research/firm_exit_FINAL_robustness.json",flush=True)

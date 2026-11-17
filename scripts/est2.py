import duckdb, os, numpy as np, json, glob
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
MQ={}
for m,t,v in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq.parquet')").fetchall(): MQ.setdefault(m,{})[t]=v
TMAX=max(t for d in MQ.values() for t in d)
YMIN=(2017-1991)*4+1
LO,HI=YMIN+6, TMAX-6          # events must have full pre AND post inside the data
print(f"panel max tq={TMAX} ({1991+(TMAX-1)//4}Q{(TMAX-1)%4+1}); usable event window tq {LO}..{HI}",flush=True)
SL=[(m,t,s) for m,t,s in con.execute("SELECT mol,t,shr FROM read_parquet('/tmp/sl.parquet')").fetchall() if LO<=t<=HI]
first={}
for m,t,s in sorted(SL,key=lambda x:x[1]):
    if m not in first: first[m]=(t,s)
print(f"events after edge exclusion: {len(first)}",flush=True)
treated=set(first)
ctl=[m for m in MQ if m not in treated and len([t for t in MQ[m] if MQ[m][t] and MQ[m][t]>0 and t>=YMIN])>=34
     and np.mean([v for v in MQ[m].values() if v])>=400]
print(f"control molecules: {len(ctl)}",flush=True)
rng=np.random.default_rng(7); td=[t for t,_ in first.values()]
def feat(sel,getT):
    z=[];l=[]
    for m in sel:
        t=getT(m); s=MQ.get(m,{})
        if not (LO<=t<=HI): continue
        pre=[s.get(t+k) for k in range(-6,0)]
        if any(v is None or v<=0 for v in pre): continue
        post=[s.get(t+k) for k in range(1,7)]
        if all(v is None for v in post): continue        # no data at all: drop, not zero
        post=[0.0 if v is None else v for v in post]
        z.append(1.0 if np.mean(post)<=0.02*np.mean(pre) else 0.0)
        l.append(np.mean(np.log1p(post))-np.mean(np.log1p(pre)))
    return np.array(z),np.array(l)
cz,cl=feat(ctl,lambda m:int(rng.choice(td)))
print(f"\ncontrol: n={len(cl)}  collapse={cz.mean():.1%}  mean change={100*(np.exp(cl.mean())-1):+.1f}%",flush=True)
print("\n  band           n    collapse  ctrl     change      perm p   collapse p",flush=True)
out={}
for lo,hi,nm in [(0,.35,"minor <35%"),(.35,.65,"35-65%"),(.65,.95,"65-95%"),(.95,1.01,"sole >=95%"),(0,1.01,"all")]:
    sel=[m for m in first if lo<=first[m][1]<hi]
    z,l=feat(sel,lambda m:first[m][0])
    if len(l)<3: continue
    d=l.mean()-cl.mean(); dz=z.mean()-cz.mean(); ph=[];pz=[]
    for _ in range(500):
        s2=list(rng.choice(ctl,size=min(max(len(l),30),len(ctl)),replace=False))
        a,b=feat(s2,lambda m:int(rng.choice(td)))
        if len(b)>5: ph.append(b.mean()-cl.mean()); pz.append(a.mean()-cz.mean())
    ph=np.array(ph);pz=np.array(pz)
    p=(np.sum(np.abs(ph)>=abs(d))+1)/(len(ph)+1); pz_=(np.sum(np.abs(pz)>=abs(dz))+1)/(len(pz)+1)
    out[nm]=dict(n=int(len(l)),collapse=float(z.mean()),ctrl_collapse=float(cz.mean()),
                 pct=float(100*(np.exp(d)-1)),p=float(p),collapse_p=float(pz_))
    print(f"  {nm:<14}{len(l):>4}    {z.mean():>5.1%}  {cz.mean():>5.1%}   {100*(np.exp(d)-1):>+7.1f}%    {p:.4f}   {pz_:.4f}",flush=True)
print("\n=== event-time, sole band, edge-safe ===",flush=True)
sole=[m for m in first if first[m][1]>=.95]
for k in range(-6,7):
    v=[np.log1p(MQ[m].get(first[m][0]+k,0) or 0.0)-np.log1p(MQ[m][first[m][0]-1]) for m in sole
       if MQ.get(m,{}).get(first[m][0]-1,0)>0 and (first[m][0]+k)<=TMAX]
    print(f"   t{k:+d}: {np.mean(v):+.3f} (n={len(v)})",flush=True)
json.dump(out,open(os.path.expanduser("~/mnt/Research/firm_exit_results_FINAL.json"),'w'),indent=2)
print("\nwrote Research/firm_exit_results_FINAL.json",flush=True)

import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1
SLall=con.execute("SELECT mol,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
res={}
for B0,B1,nm in [(-8,-4,"t-8..t-5"),(-6,-2,"t-6..t-3"),(-4,0,"t-4..t-1 (contaminated)")]:
    LO,HI=YMIN-B0+2,TMAX-6
    SL=[(m,t,s) for m,t,s in SLall if LO<=t<=HI]
    first={}
    for m,t,s in sorted(SL,key=lambda x:x[1]):
        if m not in first: first[m]=(t,s)
    treated=set(first)
    ctl=[m for m in MQ if m not in treated and len([t for t in MQ[m] if MQ[m][t] and MQ[m][t]>0 and t>=YMIN])>=34
         and np.mean([v for v in MQ[m].values() if v])>=400]
    rng=np.random.default_rng(7); td=[t for t,_ in first.values()]
    def feat(sel,getT):
        z=[];l=[]
        for m in sel:
            t=getT(m); s=MQ.get(m,{})
            if not (LO<=t<=HI): continue
            pre=[s.get(t+k) for k in range(B0,B1)]
            if any(v is None or v<=0 for v in pre): continue
            post=[s.get(t+k) for k in range(1,7)]
            if all(v is None for v in post): continue
            post=[0.0 if v is None else v for v in post]
            z.append(1.0 if np.mean(post)<=0.02*np.mean(pre) else 0.0); l.append(np.mean(np.log1p(post))-np.mean(np.log1p(pre)))
        return np.array(z),np.array(l)
    cz,cl=feat(ctl,lambda m:int(rng.choice(td)))
    sole=[m for m in first if first[m][1]>=.95]; minor=[m for m in first if first[m][1]<.35]
    zs,ls=feat(sole,lambda m:first[m][0]); zm,lm=feat(minor,lambda m:first[m][0])
    d=ls.mean()-cl.mean(); ph=[];pz=[]
    for _ in range(800):
        s2=list(rng.choice(ctl,size=max(len(ls),30),replace=False)); a,b=feat(s2,lambda m:int(rng.choice(td)))
        if len(b)>5: ph.append(b.mean()-cl.mean()); pz.append(a.mean()-cz.mean())
    ph=np.array(ph);pz=np.array(pz)
    p=(np.sum(np.abs(ph)>=abs(d))+1)/(len(ph)+1)
    pz2=(np.sum(np.abs(pz)>=abs(zs.mean()-cz.mean()))+1)/(len(pz)+1)
    res[nm]=dict(n_sole=int(len(ls)),rate=float(zs.mean()),pct=float(100*(np.exp(d)-1)),p=float(p),p_rate=float(pz2),
                 n_minor=int(len(lm)),minor_rate=float(zm.mean()),ctrl=float(cz.mean()),n_ctrl=int(len(cl)))
    print(f"{nm:<24} sole n={len(ls):>3}  rate {zs.mean():>5.1%}  change {100*(np.exp(d)-1):>+7.1f}%  p={p:.4f}/{pz2:.4f}   minor n={len(lm):>3} rate {zm.mean():>5.1%}   ctrl {cz.mean():>4.1%} (n={len(cl)})",flush=True)
json.dump(res,open(os.path.expanduser("~/mnt/Research/RESULTS_baseline_choice.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_baseline_choice.json",flush=True)

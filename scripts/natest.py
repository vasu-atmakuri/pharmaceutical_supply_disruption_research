import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={};SP={}
for m,t,r,a in con.execute("SELECT mol,tq,rx,amt FROM read_parquet('/tmp/molq_nat.parquet')").fetchall():
    MQ.setdefault(m,{})[t]=r; SP.setdefault(m,{})[t]=a
META={r[0]:(r[1],r[2],r[3]) for r in con.execute("SELECT mol,gen,frm,epc FROM read_parquet('/tmp/meta_nat.parquet')").fetchall()}
S={}
for m,l,t in con.execute("SELECT mkt,lab,tq FROM read_parquet('/tmp/lmq_nat.parquet') WHERE rx>0").fetchall(): S.setdefault((m,t),set()).add(l)
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; LO,HI=YMIN+8,TMAX-6
print(f"panel {1991+(YMIN-1)//4}Q{(YMIN-1)%4+1} to {1991+(TMAX-1)//4}Q{(TMAX-1)%4+1}; event window tq {LO}..{HI}",flush=True)
SL=[(m,t,s) for m,t,s in con.execute("SELECT mol,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall() if LO<=t<=HI]
first={}
for m,t,s in sorted(SL,key=lambda x:x[1]):
    if m not in first: first[m]=(t,s)
treated=set(first)
ctl=[m for m in MQ if m not in treated and len([t for t in MQ[m] if MQ[m][t] and MQ[m][t]>0 and t>=YMIN])>=34
     and np.mean([v for v in MQ[m].values() if v])>=400]
rng=np.random.default_rng(101); td=[t for t,_ in first.values()]
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
cz,cl=feat(ctl,lambda m:int(rng.choice(td)))
print(f"events {len(first)}  controls n={len(cl)}  control collapse {cz.mean():.1%}  drift {100*(np.exp(cl.mean())-1):+.1f}%",flush=True)
print("\n  band           n   <=2% base  ctrl    change      p(chg)  p(rate)",flush=True)
out={}
for lo,hi,nm in [(0,.35,"minor <35%"),(.35,.65,"35-65%"),(.65,.95,"65-95%"),(.95,1.01,"sole >=95%"),(0,1.01,"all")]:
    sel=[m for m in first if lo<=first[m][1]<hi]
    z,l=feat(sel,lambda m:first[m][0])
    if len(l)<3: continue
    d=l.mean()-cl.mean(); dz=z.mean()-cz.mean(); ph=[];pz=[]
    for _ in range(800):
        s2=list(rng.choice(ctl,size=min(max(len(l),30),len(ctl)),replace=False))
        a,b=feat(s2,lambda m:int(rng.choice(td)))
        if len(b)>5: ph.append(b.mean()-cl.mean()); pz.append(a.mean()-cz.mean())
    ph=np.array(ph);pz=np.array(pz)
    p=(np.sum(np.abs(ph)>=abs(d))+1)/(len(ph)+1); pzz=(np.sum(np.abs(pz)>=abs(dz))+1)/(len(pz)+1)
    out[nm]=dict(n=int(len(l)),rate=float(z.mean()),ctrl=float(cz.mean()),pct=float(100*(np.exp(d)-1)),p=float(p),p_rate=float(pzz))
    print(f"  {nm:<14}{len(l):>3}    {z.mean():>6.1%} {cz.mean():>5.1%}  {100*(np.exp(d)-1):>+7.1f}%    {p:.4f}  {pzz:.4f}",flush=True)
sole=[m for m in first if first[m][1]>=.95]
print("\n=== event time, sole band ===",flush=True)
ET={}
for k in range(-8,7):
    v=[np.log1p(MQ[m].get(first[m][0]+k,0) or 0.0)-np.mean([np.log1p(MQ[m][first[m][0]+j]) for j in range(-8,-4)])
       for m in sole if all(MQ[m].get(first[m][0]+j) for j in range(-8,-4))]
    ET[k]=float(np.mean(v)); print(f"   t{k:+d}: {np.mean(v):+.3f} (n={len(v)})",flush=True)
print("\n=== threshold sensitivity, sole band ===",flush=True)
TH={}
for thr in (0.01,0.02,0.05,0.10,0.20):
    z,l=feat(sole,lambda m:first[m][0],thr=thr); c2,_=feat(ctl,lambda m:int(rng.choice(td)),thr=thr)
    TH[thr]=[float(z.mean()),float(c2.mean())]; print(f"   <={thr:>4.0%}  treated {z.mean():>5.1%}  control {c2.mean():>5.1%}",flush=True)
print("\n=== entry ===",flush=True)
ENT={}
for lo,hi,nm in [(0,.35,"minor <35%"),(.35,.95,"mid"),(.95,1.01,"sole >=95%")]:
    r=[]
    for m in [x for x in first if lo<=first[x][1]<hi]:
        t=first[m][0]
        if (m,t-1) not in S: continue
        pre=S[(m,t-1)]; new=set()
        for k in range(0,7): new|=(S.get((m,t+k),set())-pre)
        r.append((len(pre),len(S.get((m,t+6),set())),len(new)))
    if len(r)<3: continue
    A=np.array(r); ENT[nm]=dict(n=len(r),pre=float(A[:,0].mean()),t6=float(A[:,1].mean()),pct=float((A[:,2]>0).mean()))
    print(f"  {nm:<13}n={len(r):>4}  suppliers {A[:,0].mean():.2f} -> {A[:,1].mean():.2f}   any entry {100*(A[:,2]>0).mean():.0f}%",flush=True)
print("\n=== substitution within EPC class ===",flush=True)
EPC={m:META[m][2] for m in META if META[m][2]}
CL={}
for m,d in MQ.items():
    e=EPC.get(m)
    if e:
        for t,v in d.items(): CL.setdefault((e,t),{})[m]=v
SUB={}
for lo,hi,nm in [(0,.35,"minor <35%"),(.95,1.01,"sole >=95%")]:
    sel=[m for m in first if lo<=first[m][1]<hi and m in EPC]; o=[]
    for k in (0,2,4,6):
        v=[]
        for m in sel:
            t=first[m][0]; e=EPC[m]
            a=sum(x for mm,x in CL.get((e,t+k),{}).items() if mm!=m); b=sum(x for mm,x in CL.get((e,t-1),{}).items() if mm!=m)
            if a>0 and b>0: v.append(np.log(a)-np.log(b))
        o.append(float(np.mean(v)) if v else None)
    SUB[nm]=o; print(f"  {nm:<13}"+"  ".join(f"t+{k}: {a:+.3f}" for k,a in zip((0,2,4,6),o)),flush=True)
print("\n=== spending vs volume ===",flush=True)
SPD={}
def ch(sel,getT,src):
    l=[]
    for m in sel:
        t=getT(m); s=src.get(m,{}); g=MQ.get(m,{})
        if not (LO<=t<=HI): continue
        pre=[g.get(t+k) for k in range(-8,-4)]; pr=[s.get(t+k) for k in range(-8,-4)]
        if any(v is None or v<=0 for v in pre) or any(v is None or v<=0 for v in pr): continue
        if all(g.get(t+k) is None for k in range(1,7)): continue
        l.append(np.mean(np.log1p([0.0 if s.get(t+k) is None else s.get(t+k) for k in range(1,7)]))-np.mean(np.log1p(pr)))
    return np.array(l)
cvv=ch(ctl,lambda m:int(rng.choice(td)),MQ); css=ch(ctl,lambda m:int(rng.choice(td)),SP)
for lo,hi,nm in [(0,.35,"minor <35%"),(.95,1.01,"sole >=95%")]:
    sel=[m for m in first if lo<=first[m][1]<hi]
    lv=ch(sel,lambda m:first[m][0],MQ); ls=ch(sel,lambda m:first[m][0],SP)
    v=100*(np.exp(lv.mean()-cvv.mean())-1); s=100*(np.exp(ls.mean()-css.mean())-1)
    SPD[nm]=dict(volume=float(v),spending=float(s))
    print(f"  {nm:<13}volume {v:>+7.1f}%   spending {s:>+7.1f}%",flush=True)
print("\n=== power ===",flush=True)
ph=[]
for _ in range(1500):
    s2=list(rng.choice(ctl,size=len(sole),replace=False)); _,b=feat(s2,lambda m:int(rng.choice(td)))
    if len(b)>5: ph.append(b.mean())
sd=float(np.array(ph).std())
print(f"  placebo SD n={len(sole)}: {sd:.4f};  MDE {100*(np.exp(2.80*sd)-1):+.1f}%",flush=True)
json.dump(dict(main=out,event_time=ET,thresholds=TH,entry=ENT,substitution=SUB,spending=SPD,placebo_sd=sd),
  open(os.path.expanduser("~/mnt/Research/RESULTS_national_panel.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_national_panel.json",flush=True)

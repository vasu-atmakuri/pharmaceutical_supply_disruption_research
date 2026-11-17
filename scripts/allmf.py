import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,v in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_mf.parquet')").fetchall(): MQ.setdefault(m,{})[t]=v
META={r[0]:(r[1],r[2],r[3]) for r in con.execute("SELECT mol,gen,frm,epc FROM read_parquet('/tmp/mktmeta.parquet')").fetchall()}
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
rng=np.random.default_rng(13); td=[t for t,_ in first.values()]
# BASELINE t-8..t-5 : avoids the wind-down quarters
def feat(sel,getT):
    z=[];l=[]
    for m in sel:
        t=getT(m); s=MQ.get(m,{})
        if not (LO<=t<=HI): continue
        pre=[s.get(t+k) for k in range(-8,-4)]
        if any(v is None or v<=0 for v in pre): continue
        post=[s.get(t+k) for k in range(1,7)]
        if all(v is None for v in post): continue
        post=[0.0 if v is None else v for v in post]
        z.append(1.0 if np.mean(post)<=0.02*np.mean(pre) else 0.0)
        l.append(np.mean(np.log1p(post))-np.mean(np.log1p(pre)))
    return np.array(z),np.array(l)
cz,cl=feat(ctl,lambda m:int(rng.choice(td)))
print(f"=== BASELINE t-8..t-5 (pre-windown), events={len(first)}, controls n={len(cl)} ===",flush=True)
print(f"  control collapse={cz.mean():.1%}  drift={100*(np.exp(cl.mean())-1):+.1f}%",flush=True)
print("\n  band           n    collapse  ctrl    change      p(chg)  p(coll)",flush=True)
out={}
for lo,hi,nm in [(0,.35,"minor <35%"),(.35,.65,"35-65%"),(.65,.95,"65-95%"),(.95,1.01,"sole >=95%"),(0,1.01,"all")]:
    sel=[m for m in first if lo<=first[m][1]<hi]
    z,l=feat(sel,lambda m:first[m][0])
    if len(l)<3: continue
    d=l.mean()-cl.mean(); dz=z.mean()-cz.mean(); ph=[];pz=[]
    for _ in range(600):
        s2=list(rng.choice(ctl,size=min(max(len(l),30),len(ctl)),replace=False))
        a,b=feat(s2,lambda m:int(rng.choice(td)))
        if len(b)>5: ph.append(b.mean()-cl.mean()); pz.append(a.mean()-cz.mean())
    ph=np.array(ph);pz=np.array(pz)
    p=(np.sum(np.abs(ph)>=abs(d))+1)/(len(ph)+1); pzz=(np.sum(np.abs(pz)>=abs(dz))+1)/(len(pz)+1)
    out[nm]=dict(n=int(len(l)),collapse=float(z.mean()),ctrl=float(cz.mean()),pct=float(100*(np.exp(d)-1)),p=float(p),p_collapse=float(pzz))
    print(f"  {nm:<14}{len(l):>4}    {z.mean():>5.1%} {cz.mean():>5.1%}  {100*(np.exp(d)-1):>+7.1f}%    {p:.4f}  {pzz:.4f}",flush=True)
print("\n=== ENTRY ===",flush=True)
print("  band          n   sup t-1   t+4   t+6   new by t+6   % any entry",flush=True)
ent={}
for lo,hi,nm in [(0,.35,"minor <35%"),(.35,.95,"mid"),(.95,1.01,"sole >=95%")]:
    r=[]
    for m in [x for x in first if lo<=first[x][1]<hi]:
        t=first[m][0]
        if (m,t-1) not in S: continue
        pre=S[(m,t-1)]; new=set()
        for k in range(0,7): new|=(S.get((m,t+k),set())-pre)
        r.append((len(pre),len(S.get((m,t+4),set())),len(S.get((m,t+6),set())),len(new)))
    if len(r)<3: continue
    A=np.array(r); ent[nm]=dict(n=len(r),sup_pre=float(A[:,0].mean()),sup_t6=float(A[:,2].mean()),pct_entry=float((A[:,3]>0).mean()))
    print(f"  {nm:<13}{len(r):>3}    {A[:,0].mean():.2f}  {A[:,1].mean():.2f}  {A[:,2].mean():.2f}      {A[:,3].mean():.2f}        {100*(A[:,3]>0).mean():.0f}%",flush=True)
print("\n=== THERAPEUTIC SUBSTITUTION (other markets, same EPC class) ===",flush=True)
EPC={m:META[m][2] for m in META if META[m][2]}
CL={}
for m,d in MQ.items():
    e=EPC.get(m)
    if e:
        for t,v in d.items(): CL.setdefault((e,t),{})[m]=v
print("  band          n     t+0     t+2     t+4     t+6",flush=True)
sub={}
for lo,hi,nm in [(0,.35,"minor <35%"),(.95,1.01,"sole >=95%")]:
    sel=[m for m in first if lo<=first[m][1]<hi and m in EPC]; o=[]
    for k in (0,2,4,6):
        v=[]
        for m in sel:
            t=first[m][0]; e=EPC[m]
            a=sum(x for mm,x in CL.get((e,t+k),{}).items() if mm!=m)
            b=sum(x for mm,x in CL.get((e,t-1),{}).items() if mm!=m)
            if a>0 and b>0: v.append(np.log(a)-np.log(b))
        o.append((np.mean(v) if v else np.nan,len(v)))
    sub[nm]=[float(a) for a,_ in o]
    print(f"  {nm:<13}{o[0][1]:>3}  "+"  ".join(f"{a:+.3f}" for a,_ in o),flush=True)
print("\n=== AFFECTED SOLE-SUPPLIER MARKETS (top 20 by volume) ===",flush=True)
rows=[]
for m in [x for x in first if first[x][1]>=.95]:
    t=first[m][0]; pre=np.mean([MQ[m][t+k] for k in range(-8,-4) if MQ[m].get(t+k)])
    post=np.mean([MQ[m].get(t+k) or 0 for k in range(1,7)])
    rows.append((m,f"{1991+(t-1)//4}Q{(t-1)%4+1}",pre,post,len(S.get((m,t+6),set()))))
rows.sort(key=lambda r:-r[2])
for r in rows[:20]: print(f"  {r[0][:52]:<54}{r[1]:<8}{r[2]:>10,.0f} ->{r[3]:>9,.0f}  suppliers after: {r[4]}",flush=True)
print(f"\n  total volume at risk: {sum(r[2] for r in rows):,.0f} rx/qtr across {len(rows)} markets",flush=True)
json.dump(dict(main=out,entry=ent,substitution=sub),open(os.path.expanduser("~/mnt/Research/firm_exit_FINAL_all.json"),'w'),indent=2)
print("\nwrote Research/firm_exit_FINAL_all.json",flush=True)

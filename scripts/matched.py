import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
S={}
for m,l,t,r in con.execute("SELECT mkt,lab,tq,rx FROM read_parquet('/tmp/lmq_nat.parquet') WHERE rx>0").fetchall():
    S.setdefault((m,t),set()).add(l)
FRM={r[0]:r[1] for r in con.execute("SELECT mol,frm FROM read_parquet('/tmp/meta_nat.parquet')").fetchall()}
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SLall=con.execute("SELECT mol,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
ever={m for m,_,_ in SLall}
first={}
for m,t,s in sorted([x for x in SLall if LO<=x[1]<=HI],key=lambda x:x[1]):
    if m not in first: first[m]=(t,s)
def base(m,t): return np.mean([MQ[m][t+k] for k in range(B0,B1)])
def post(m,t): return np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)])
def ok(m,t):
    s=MQ.get(m,{})
    if any(s.get(t+k) is None or (s.get(t+k) or 0)<=0 for k in range(B0,B1)): return False
    if all(s.get(t+k) is None for k in range(1,7)): return False
    return True
EV=[m for m in first if ok(m,first[m][0])]
# RISK-SET MATCHING: controls are NEVER-exposed markets, matched on pre-event
# supplier count, volume (factor of 2), dosage form, and the SAME calendar quarter.
# No survival requirement of any kind.
pool=[m for m in MQ if m not in ever]
print(f"never-exposed pool: {len(pool)}   treated eligible: {len(EV)}",flush=True)
rng=np.random.default_rng(2026)
def matches(m,t,K=20):
    nb=len(S.get((m,t-1),set())); vb=base(m,t); f=FRM.get(m)
    out=[]
    for c in pool:
        if not ok(c,t): continue
        if len(S.get((c,t-1),set()))!=nb: continue
        if FRM.get(c)!=f: continue
        vc=base(c,t)
        if vc<vb/2 or vc>vb*2: continue
        out.append(c)
    if len(out)>K: out=list(rng.choice(out,size=K,replace=False))
    return out
print("\n=== MATCHED COMPARISON (same supplier count, dosage form, calendar quarter, volume within 2x) ===",flush=True)
print(f"  {'band':<14}{'n tx':>5}{'matched':>9}{'tx below2%':>12}{'ctl below2%':>13}{'tx dlog':>10}{'ctl dlog':>10}",flush=True)
OUT={}
for lo,hi,nm in [(0,.35,"under 35%"),(.35,.95,"35 to 95%"),(.95,1.01,"95% or above")]:
    sel=[m for m in EV if lo<=first[m][1]<hi]
    tz=[];tl=[];cz=[];cl=[];nm_=0;used=0
    for m in sel:
        t=first[m][0]; cs=matches(m,t)
        if not cs: continue
        used+=1; nm_+=len(cs)
        tz.append(1.0 if post(m,t)<=0.02*base(m,t) else 0.0)
        tl.append(np.log1p(post(m,t))-np.log1p(base(m,t)))
        for c in cs:
            cz.append(1.0 if post(c,t)<=0.02*base(c,t) else 0.0)
            cl.append(np.log1p(post(c,t))-np.log1p(base(c,t)))
    if not tz: continue
    tz,tl,cz,cl=map(np.array,(tz,tl,cz,cl))
    OUT[nm]=dict(n_tx=int(used),n_ctl=int(nm_),tx_rate=float(tz.mean()),ctl_rate=float(cz.mean()),
                 tx_dlog=float(tl.mean()),ctl_dlog=float(cl.mean()),
                 diff_pct=float(100*(np.exp(tl.mean()-cl.mean())-1)))
    print(f"  {nm:<14}{used:>5}{nm_:>9}{tz.mean():>12.1%}{cz.mean():>13.1%}{tl.mean():>10.3f}{cl.mean():>10.3f}",flush=True)
print("\n  net of matched controls:",flush=True)
for nm,d in OUT.items():
    print(f"    {nm:<14} below-2% gap {100*(d['tx_rate']-d['ctl_rate']):>+6.1f} pts    dispensing {d['diff_pct']:>+7.1f}%",flush=True)
# sole-source specific: 1-supplier markets that lost it vs 1-supplier markets that did not
print("\n=== SOLE-SOURCE SPECIFIC: single-supplier markets, lost vs not lost ===",flush=True)
sole=[m for m in EV if first[m][1]>=.95]
tz=[];cz=[];tl=[];cl=[];nc=0
for m in sole:
    t=first[m][0]
    cs=[c for c in pool if ok(c,t) and len(S.get((c,t-1),set()))==1
        and base(c,t)>=base(m,t)/3 and base(c,t)<=base(m,t)*3]
    if not cs: continue
    if len(cs)>25: cs=list(rng.choice(cs,size=25,replace=False))
    nc+=len(cs)
    tz.append(1.0 if post(m,t)<=0.02*base(m,t) else 0.0); tl.append(np.log1p(post(m,t))-np.log1p(base(m,t)))
    for c in cs:
        cz.append(1.0 if post(c,t)<=0.02*base(c,t) else 0.0); cl.append(np.log1p(post(c,t))-np.log1p(base(c,t)))
tz,cz,tl,cl=map(np.array,(tz,cz,tl,cl))
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
a=wil(int(tz.sum()),len(tz)); b=wil(int(cz.sum()),len(cz))
print(f"  treated single-supplier markets that lost supplier: n={len(tz)}  below 2%: {tz.mean():.1%}  CI [{a[0]:.1%}, {a[1]:.1%}]",flush=True)
print(f"  matched single-supplier markets that did not:       n={len(cz)}  below 2%: {cz.mean():.1%}  CI [{b[0]:.1%}, {b[1]:.1%}]",flush=True)
print(f"  dispensing change: treated {100*(np.exp(tl.mean())-1):+.1f}%   control {100*(np.exp(cl.mean())-1):+.1f}%",flush=True)
# permutation on matched controls, 20000 draws
d0=tz.mean()-cz.mean(); cnt=0; N=20000
for _ in range(N):
    s=rng.choice(cz,size=len(tz),replace=False) if len(cz)>=len(tz) else rng.choice(cz,size=len(tz),replace=True)
    if abs(s.mean()-cz.mean())>=abs(d0): cnt+=1
print(f"  permutation p ({N:,} draws): {(cnt+1)/(N+1):.5f}",flush=True)
OUT['sole_vs_sole']=dict(n_tx=len(tz),n_ctl=len(cz),tx=float(tz.mean()),ctl=float(cz.mean()),
                         tx_ci=list(a),ctl_ci=list(b),p=float((cnt+1)/(N+1)))
json.dump(OUT,open(os.path.expanduser("~/mnt/Research/RESULTS_matched_controls.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_matched_controls.json",flush=True)

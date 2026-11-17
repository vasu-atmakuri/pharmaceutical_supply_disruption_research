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
FRM={r[0]:r[1] for r in con.execute("SELECT mol,frm FROM read_parquet('/tmp/meta_nat.parquet')").fetchall()}
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2
SLall=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SLall,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def band(s): return "under 35%" if s<.35 else ("35 to 95%" if s<.95 else "sole >=95%")
# ---------- A. RECOVERY DYNAMICS, horizon as long as the panel allows ----------
print("=== RECOVERY DYNAMICS (censored at panel end, not forced to 6 quarters) ===",flush=True)
LOr,HIr=YMIN-B0+2,TMAX-2
ev=[(m,v[0],v[1],v[2]) for m,v in first.items() if LOr<=v[0]<=HIr and basec(m,v[0]) is not None]
print(f"  events with >=2 post quarters: {len(ev)}",flush=True)
def recov(m,t,b,frac):
    """first quarter k>=1 at which dispensing reaches frac*baseline; None if never within panel"""
    for k in range(1,TMAX-t+1):
        v=MQ[m].get(t+k)
        if v is not None and v>=frac*b: return k
    return None
print(f"\n  {'band':<14}{'n':>4}{'med entry q':>13}{'any entry':>11}{'reach 50%':>11}{'reach 90%':>11}{'cum deficit':>14}",flush=True)
OUT={}
for b_ in ["under 35%","35 to 95%","sole >=95%"]:
    sel=[(m,t,s,l) for m,t,s,l in ev if band(s)==b_]
    ent=[];r50=[];r90=[];defi=[];horizon=[]
    for m,t,s,l in sel:
        bl=basec(m,t); pre=S.get((m,t-1),set())
        H=min(12,TMAX-t)
        e=None
        for k in range(0,H+1):
            if S.get((m,t+k),set())-pre: e=k; break
        ent.append(e)
        r50.append(recov(m,t,bl,0.5)); r90.append(recov(m,t,bl,0.9))
        d=sum(max(bl-(MQ[m].get(t+k) or 0.0),0) for k in range(1,H+1))
        defi.append(d/bl if bl>0 else np.nan); horizon.append(H)
    n=len(sel); ae=[x for x in ent if x is not None]
    f50=[x for x in r50 if x is not None]; f90=[x for x in r90 if x is not None]
    OUT[b_]=dict(n=n,any_entry=len(ae)/n,med_entry=float(np.median(ae)) if ae else None,
                 p50=len(f50)/n,p90=len(f90)/n,
                 med50=float(np.median(f50)) if f50 else None,
                 cum_deficit_q=float(np.median(defi)),med_horizon=float(np.median(horizon)))
    print(f"  {b_:<14}{n:>4}{(np.median(ae) if ae else float('nan')):>13.1f}{len(ae)/n:>10.0%}"
          f"{len(f50)/n:>11.0%}{len(f90)/n:>11.0%}{np.median(defi):>13.1f}q",flush=True)
print("\n  cum deficit = quarters of baseline volume lost, summed over the observed horizon",flush=True)
print("\n=== SOLE BAND, event-level recovery ===",flush=True)
sel=[(m,t,s,l) for m,t,s,l in ev if band(s)=="sole >=95%"]
print(f"  {'market':<40}{'base':>9}{'entry q':>9}{'50% q':>8}{'90% q':>8}{'deficit':>9}",flush=True)
for m,t,s,l in sorted(sel,key=lambda x:-basec(x[0],x[1]))[:14]:
    bl=basec(m,t); pre=S.get((m,t-1),set()); H=min(12,TMAX-t)
    e=next((k for k in range(0,H+1) if S.get((m,t+k),set())-pre),None)
    a=recov(m,t,bl,0.5); c=recov(m,t,bl,0.9)
    d=sum(max(bl-(MQ[m].get(t+k) or 0.0),0) for k in range(1,H+1))/bl
    print(f"  {m[:38]:<40}{bl:>9,.0f}{(str(e) if e is not None else '-'):>9}"
          f"{(str(a) if a else '-'):>8}{(str(c) if c else '-'):>8}{d:>8.1f}q",flush=True)
# ---------- B. ADDITIONAL ESTIMANDS ----------
print("\n=== ADDITIONAL REPLACEMENT ESTIMANDS (6-quarter window) ===",flush=True)
LO,HI=YMIN-B0+2,TMAX-6
ev6=[(m,v[0],v[1],v[2]) for m,v in first.items() if LO<=v[0]<=HI and basec(m,v[0]) is not None
     and any(MQ[m].get(v[0]+k) is not None for k in range(1,7))]
def R(m,t,dl):
    db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
    ob=np.mean([(MQ[m][t+k] or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
    return (db,(op-ob)) if db>0 else None
print(f"  {'band':<14}{'n':>4}{'median R':>10}{'vol-weighted R':>16}{'P(R>0)':>9}{'P(R>=0.5)':>11}{'P(R>=1)':>10}",flush=True)
EST={}
for b_ in ["under 35%","35 to 95%","sole >=95%"]:
    sel=[(m,t,s,l) for m,t,s,l in ev6 if band(s)==b_]
    num=0;den=0;rs=[]
    for m,t,s,l in sel:
        r=R(m,t,l)
        if r is None: continue
        den+=r[0]; num+=r[1]; rs.append(r[1]/r[0])
    if not rs: continue
    rs=np.array(rs)
    EST[b_]=dict(n=len(rs),median=float(np.median(rs)),vw=float(num/den),
                 p_any=float((rs>1e-9).mean()),p50=float((rs>=0.5).mean()),p100=float((rs>=1).mean()))
    print(f"  {b_:<14}{len(rs):>4}{np.median(rs):>10.2f}{num/den:>16.2f}{(rs>1e-9).mean():>9.0%}"
          f"{(rs>=0.5).mean():>11.0%}{(rs>=1).mean():>10.0%}",flush=True)
sole_r=[R(m,t,l)[1]/R(m,t,l)[0] for m,t,s,l in ev6 if band(s)=="sole >=95%" and R(m,t,l)]
pos=[x for x in sole_r if x>1e-9]
print(f"\n  sole band exact values: {', '.join(f'{x:.4f}' for x in sorted(sole_r))}",flush=True)
print(f"  positive ones: {len(pos)}  mean of all: {np.mean(sole_r):.4f}  (matches reported 0.06)",flush=True)
# ---------- C. RISK-SET CONTROLS ----------
print("\n=== RISK-SET CONTROLS (not-yet-exposed at t, rather than never-exposed) ===",flush=True)
evt_time={m:v[0] for m,v in first.items()}
rng=np.random.default_rng(31)
def wil(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
def post(m,t): return float(np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)]))
sole=[(m,t,s,l) for m,t,s,l in ev6 if band(s)=="sole >=95%"]
tk=sum(1 for m,t,s,l in sole if post(m,t)<=0.02*basec(m,t))
ck=0;cn=0;uq=set();bysetk=[]
for m,t,s,l in sole:
    bm=basec(m,t)
    cand=[c for c in MQ if basec(c,t) and len(S.get((c,t-1),set()))==1
          and bm/3<=basec(c,t)<=bm*3 and evt_time.get(c,10**9)>t]   # not yet exposed at t
    if len(cand)>25: cand=list(rng.choice(cand,25,False))
    k=sum(1 for c in cand if post(c,t)<=0.02*basec(c,t))
    ck+=k; cn+=len(cand); uq|=set(cand); bysetk.append((k,len(cand)))
a=wil(tk,len(sole)); b=wil(ck,cn)
print(f"  treated  n={len(sole)}  below2% {tk}/{len(sole)} = {tk/len(sole):.1%}  CI [{a[0]:.1%},{a[1]:.1%}]",flush=True)
print(f"  risk-set controls n={cn} ({len(uq)} unique)  below2% {ck}/{cn} = {ck/cn:.2%}  CI [{b[0]:.2%},{b[1]:.2%}]",flush=True)
# cluster-aware: resample matched sets
d0=tk/len(sole)-ck/cn; cnt=0; N=20000
rates=[k/n for k,n in bysetk if n>0]
for _ in range(N):
    s=rng.choice(len(rates),len(rates),True)
    if abs(np.mean([rates[i] for i in s])-ck/cn)>=abs(d0): cnt+=1
print(f"  matched-set cluster bootstrap p: {(cnt+1)/(N+1):.5f}",flush=True)
json.dump(dict(recovery=OUT,estimands=EST,riskset=dict(treated=tk,n_tx=len(sole),ctl_k=ck,ctl_n=cn,
          unique=len(uq),p=float((cnt+1)/(N+1)))),
  open(os.path.expanduser("~/mnt/Research/RESULTS_round4.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_round4.json",flush=True)

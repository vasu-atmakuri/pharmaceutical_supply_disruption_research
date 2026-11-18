import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
# generic flag per labeler-product
con.execute("""CREATE OR REPLACE TABLE cat AS SELECT lab,pcode,mktcat,
  CASE WHEN mktcat IN ('ANDA','NDA AUTHORIZED GENERIC') THEN 1 ELSE 0 END isgen
  FROM read_parquet('/tmp/xcat.parquet')""")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
LMQ={}
for m,l,t,r in con.execute("SELECT mkt,lab,tq,rx FROM read_parquet('/tmp/lmq_nat.parquet')").fetchall():
    LMQ.setdefault((m,l),{})[t]=r
S={}
for (m,l),d in LMQ.items():
    for t,v in d.items():
        if v and v>0: S.setdefault((m,t),set()).add(l)
META={r[0]:r[1] for r in con.execute("SELECT mol,epc FROM read_parquet('/tmp/meta_nat.parquet') WHERE epc IS NOT NULL").fetchall()}
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1
B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SL=[(m,l,t,s) for m,l,t,s in con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall() if LO<=t<=HI]
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
def base(m,t):  return np.mean([MQ[m][t+k] for k in range(B0,B1)])
def post(m,t):  return np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)])
def eligible(m):
    t=first[m][0]; s=MQ.get(m,{})
    if any(s.get(t+k) is None or (s.get(t+k) or 0)<=0 for k in range(B0,B1)): return False
    if all(s.get(t+k) is None for k in range(1,7)): return False
    return True
EV=[m for m in first if eligible(m)]
print(f"eligible events: {len(EV)}",flush=True)
def wilson(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (max(0,c-h),min(1,c+h))
BANDS=[(0,.35,"under 35%"),(.35,.65,"35 to 65%"),(.65,.95,"65 to 95%"),(.95,1.01,"95% or above")]
print("\n=== TABLE 1 REBUILT, single specification (baseline t-6..t-3) ===",flush=True)
print(f"  {'band':<14}{'n':>4}{'below2%':>9}{'rate':>8}   95% CI (Wilson)",flush=True)
T1={}; tn=0; tk=0
for lo,hi,nm in BANDS:
    sel=[m for m in EV if lo<=first[m][1]<hi]
    k=sum(1 for m in sel if post(m,first[m][0])<=0.02*base(m,first[m][0]))
    lo_,hi_=wilson(k,len(sel)); tn+=len(sel); tk+=k
    T1[nm]=dict(n=len(sel),k=k,rate=k/len(sel) if sel else 0,ci=[lo_,hi_])
    print(f"  {nm:<14}{len(sel):>4}{k:>9}{k/len(sel) if sel else 0:>8.1%}   [{lo_:.1%}, {hi_:.1%}]",flush=True)
lo_,hi_=wilson(tk,tn)
print(f"  {'ALL':<14}{tn:>4}{tk:>9}{tk/tn:>8.1%}   [{lo_:.1%}, {hi_:.1%}]",flush=True)
print(f"  strata sum = {tn}  (reconciles)",flush=True)
print("\n=== REPLACEMENT RATIO: volume picked up by OTHER suppliers, as a fraction",flush=True)
print("    of the departing supplier's baseline volume. Removes the mechanical component. ===",flush=True)
print(f"  {'band':<14}{'n':>4}{'dep base':>10}{'oth base':>10}{'oth post':>10}{'R mean':>9}{'R median':>10}",flush=True)
RR={}
for lo,hi,nm in BANDS:
    sel=[m for m in EV if lo<=first[m][1]<hi]; rows=[]
    for m in sel:
        t,sh,dl=first[m]
        dep_b=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
        oth_b=np.mean([ (MQ[m][t+k] or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
        oth_p=np.mean([ (MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
        if dep_b<=0: continue
        rows.append((dep_b,oth_b,oth_p,(oth_p-oth_b)/dep_b))
    if not rows: continue
    A=np.array(rows)
    RR[nm]=dict(n=len(rows),dep_base=float(A[:,0].mean()),oth_base=float(A[:,1].mean()),
                oth_post=float(A[:,2].mean()),R_mean=float(A[:,3].mean()),R_med=float(np.median(A[:,3])))
    print(f"  {nm:<14}{len(rows):>4}{A[:,0].mean():>10,.0f}{A[:,1].mean():>10,.0f}{A[:,2].mean():>10,.0f}{A[:,3].mean():>9.2f}{np.median(A[:,3]):>10.2f}",flush=True)
print("\n=== SUBSTITUTION IN ABSOLUTE VOLUME (common denominator) ===",flush=True)
CL={}
for m,d in MQ.items():
    e=META.get(m)
    if e:
        for t,v in d.items(): CL.setdefault((e,t),{})[m]=v
print(f"  {'band':<14}{'n':>4}{'mkt lost':>11}{'class gain':>12}{'gain/lost':>11}",flush=True)
SUB={}
for lo,hi,nm in [(0,.35,"under 35%"),(.95,1.01,"95% or above")]:
    sel=[m for m in EV if lo<=first[m][1]<hi and m in META]; L=[];G=[]
    for m in sel:
        t=first[m][0]; e=META[m]
        mb=base(m,t); mp=post(m,t)
        cb=np.mean([sum(x for mm,x in CL.get((e,t+k),{}).items() if mm!=m and x) for k in range(B0,B1)])
        cp=np.mean([sum(x for mm,x in CL.get((e,t+k),{}).items() if mm!=m and x) for k in range(1,7)])
        L.append(mb-mp); G.append(cp-cb)
    if not L: continue
    L=np.array(L);G=np.array(G); tot=L.sum()
    SUB[nm]=dict(n=len(L),lost=float(tot),gain=float(G.sum()),frac=float(G.sum()/tot) if tot else None)
    print(f"  {nm:<14}{len(L):>4}{tot:>11,.0f}{G.sum():>12,.0f}{G.sum()/tot if tot else 0:>11.2f}",flush=True)
print("\n=== GENERIC COMPOSITION OF THE SAMPLE ===",flush=True)
con.execute(f"""CREATE OR REPLACE TABLE lg AS
 SELECT l.mkt,l.lab,SUM(l.rx) rx, MAX(c.isgen) anygen
 FROM read_parquet('/tmp/lmq_nat.parquet') l
 LEFT JOIN cat c ON c.lab=lpad(l.lab,5,'0') GROUP BY 1,2""")
g=con.execute("SELECT SUM(CASE WHEN anygen=1 THEN rx ELSE 0 END)/SUM(rx) FROM lg").fetchone()[0]
print(f"  share of panel prescriptions from ANDA / authorized-generic labelers: {g:.1%}",flush=True)
GEN={r[0] for r in con.execute("SELECT DISTINCT lpad(lab,5,'0') FROM cat WHERE isgen=1").fetchall()}
sole=[m for m in EV if first[m][1]>=.95]
ng=sum(1 for m in sole if first[m][2].zfill(5) in GEN)
print(f"  sole-supplier events whose departing labeler is ANDA/authorized generic: {ng} of {len(sole)}",flush=True)
json.dump(dict(table1=T1,replacement=RR,substitution_abs=SUB,generic_share=float(g),
               sole_generic=f"{ng}/{len(sole)}"),
  open(os.path.expanduser("~/mnt/Research/RESULTS_revision_v2.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_revision_v2.json",flush=True)

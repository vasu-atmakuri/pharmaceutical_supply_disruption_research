import duckdb, os, numpy as np, json
from math import comb
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def postobs(m,t,H): return any(MQ[m].get(t+k) is not None for k in range(1,H+1))
def band(s): return "under 35%" if s<.35 else ("35 to 95%" if s<.95 else "sole >=95%")
LOr=YMIN-B0+2
COH=[(m,v[0],v[1]) for m,v in first.items() if v[0]>=LOr and v[0]+11<=TMAX
     and basec(m,v[0]) is not None and postobs(m,v[0],12)]
import collections
print(f"=== CONSISTENT 12q COHORT (same three conditions as the primary rule) n={len(COH)} ===",flush=True)
print("  ",dict(collections.Counter(band(s) for _,_,s in COH)),flush=True)
def wil(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
def fisher(a,b,c,d):
    n=a+b+c+d
    def p(x): return comb(a+b,x)*comb(c+d,a+c-x)/comb(n,a+c)
    lo=max(0,a+c-(c+d)); hi=min(a+b,a+c); p0=p(a); tot=0.0
    for x in range(lo,hi+1):
        px=p(x)
        if px<=p0*(1+1e-9): tot+=px
    return min(1.0,tot)
OUT={}
for thr,lbl in [(0.5,"50%"),(0.9,"90%")]:
    print(f"\n  threshold {lbl}",flush=True)
    print(f"    {'H':>3}  {'band':<14}{'at risk':>9}{'regained':>10}{'rate':>8}{'95% CI':>20}{'Fisher p':>11}",flush=True)
    for H in (4,8,12):
        row={}
        for b in ["under 35%","sole >=95%"]:
            sel=[(m,t) for m,t,s in COH if band(s)==b]
            ar=0;rc=0
            for m,t in sel:
                bl=basec(m,t)
                d=next((k for k in range(1,H+1) if (MQ[m].get(t+k) or 0)<thr*bl),None)
                if d is None: continue
                ar+=1
                if any((MQ[m].get(t+k) or 0)>=thr*bl for k in range(d+1,H+1)): rc+=1
            row[b]=(ar,rc); c=wil(rc,ar)
            print(f"    {H:>3}  {b:<14}{ar:>9}{rc:>10}{rc/ar if ar else 0:>8.1%}   [{c[0]:>5.1%}, {c[1]:>5.1%}]",end="",flush=True)
            if b=="sole >=95%":
                a=row["under 35%"]; s_=row["sole >=95%"]
                p=fisher(a[1],a[0]-a[1],s_[1],s_[0]-s_[1]) if (a[0] and s_[0]) else None
                OUT[f"{lbl}_{H}q"]=dict(minor=list(a),sole=list(s_),p=float(p) if p else None)
                print(f"{p:>11.3f}",flush=True)
            else: print("",flush=True)
print("\n=== UNCONDITIONAL: share ever falling below each threshold ===",flush=True)
for thr,lbl in [(0.5,"50%"),(0.9,"90%")]:
    for b in ["under 35%","sole >=95%"]:
        sel=[(m,t) for m,t,s in COH if band(s)==b]
        k=sum(1 for m,t in sel if any((MQ[m].get(t+j) or 0)<thr*basec(m,t) for j in range(1,13)))
        print(f"  {lbl} {b:<14}{k}/{len(sel)} = {k/len(sel):.1%}",flush=True)
json.dump(dict(cohort=len(COH),bands=dict(collections.Counter(band(s) for _,_,s in COH)),recovery=OUT),
  open(os.path.expanduser("~/mnt/Research/RESULTS_round7.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_round7.json",flush=True)

import duckdb, os, numpy as np, json
from math import comb
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
S={}
for m,l,t in con.execute("SELECT mkt,lab,tq FROM read_parquet('/tmp/lmq_nat.parquet') WHERE rx>0").fetchall(): S.setdefault((m,t),set()).add(l)
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def band(s): return "under 35%" if s<.35 else ("35 to 95%" if s<.95 else "sole >=95%")
LOr=YMIN-B0+2
# ONE COHORT: events with a full 12 quarters t+0..t+11 inside the panel
COH=[(m,v[0],v[1]) for m,v in first.items() if v[0]>=LOr and v[0]+11<=TMAX and basec(m,v[0]) is not None]
print(f"=== SINGLE 12-QUARTER-ELIGIBLE COHORT: n={len(COH)} ===",flush=True)
import collections
print("  by band:",dict(collections.Counter(band(s) for _,_,s in COH)),flush=True)
def wil(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
def fisher(a,b,c,d):
    """two-sided Fisher exact on [[a,b],[c,d]]"""
    n=a+b+c+d
    def p(x):
        return comb(a+b,x)*comb(c+d,a+c-x)/comb(n,a+c)
    lo=max(0,a+c-(c+d)); hi=min(a+b,a+c)
    p0=p(a); tot=0.0
    for x in range(lo,hi+1):
        px=p(x)
        if px<=p0*(1+1e-9): tot+=px
    return min(1.0,tot)
print("\n=== RECOVERY ON THE SAME COHORT AT 4, 8, 12 QUARTERS ===",flush=True)
print("   conditional on first falling below the threshold\n",flush=True)
OUT={}
for thr,lbl in [(0.5,"50%"),(0.9,"90%")]:
    print(f"  threshold {lbl}",flush=True)
    print(f"    {'H':>3}  {'band':<14}{'at risk':>9}{'regained':>10}{'rate':>8}{'95% Wilson CI':>20}",flush=True)
    for H in (4,8,12):
        row={}
        for b in ["under 35%","sole >=95%"]:
            sel=[(m,t) for m,t,s in COH if band(s)==b]
            atrisk=0; rec=0
            for m,t in sel:
                bl=basec(m,t)
                drop=next((k for k in range(1,H+1) if (MQ[m].get(t+k) or 0)<thr*bl),None)
                if drop is None: continue
                atrisk+=1
                if any((MQ[m].get(t+k) or 0)>=thr*bl for k in range(drop+1,H+1)): rec+=1
            c=wil(rec,atrisk); row[b]=(atrisk,rec)
            print(f"    {H:>3}  {b:<14}{atrisk:>9}{rec:>10}{rec/atrisk if atrisk else 0:>8.1%}"
                  f"   [{c[0]:>5.1%}, {c[1]:>5.1%}]",flush=True)
        a=row["under 35%"]; s_=row["sole >=95%"]
        if a[0] and s_[0]:
            p=fisher(a[1],a[0]-a[1],s_[1],s_[0]-s_[1])
            OUT[f"{lbl}_{H}q"]=dict(minor=list(a),sole=list(s_),fisher_p=float(p))
            print(f"         Fisher exact two-sided p = {p:.4f}",flush=True)
    print(flush=True)
print("=== DEFICIT ON THE SAME COHORT, three estimands for the after-detection share ===",flush=True)
print(f"  {'band':<14}{'n':>4}{'t+0..t+3':>11}{'t+4..t+11':>12}{'median of':>12}{'ratio of':>11}{'aggregate':>11}",flush=True)
print(f"  {'':<14}{'':>4}{'median':>11}{'median':>12}{'ev shares':>12}{'medians':>11}{'volumes':>11}",flush=True)
DEF={}
for b in ["under 35%","35 to 95%","sole >=95%"]:
    sel=[(m,t) for m,t,s in COH if band(s)==b]
    d1=[];d2=[];sh=[];A1=0.0;A2=0.0
    for m,t in sel:
        bl=basec(m,t)
        a=sum(max(bl-(MQ[m].get(t+k) or 0.0),0) for k in range(0,4))/bl
        c=sum(max(bl-(MQ[m].get(t+k) or 0.0),0) for k in range(4,12))/bl
        d1.append(a); d2.append(c); A1+=a; A2+=c
        if a+c>0: sh.append(c/(a+c))
    if not d1: continue
    m1,m2=np.median(d1),np.median(d2)
    DEF[b]=dict(n=len(d1),det=float(m1),after=float(m2),
                med_share=float(np.median(sh)) if sh else None,
                ratio_med=float(m2/(m1+m2)) if (m1+m2)>0 else None,
                agg=float(A2/(A1+A2)) if (A1+A2)>0 else None,
                total=float(m1+m2))
    ms=f"{np.median(sh):.0%}" if sh else "n/a"
    rm=f"{m2/(m1+m2):.0%}" if (m1+m2)>0 else "n/a"
    ag=f"{A2/(A1+A2):.0%}" if (A1+A2)>0 else "n/a"
    print(f"  {b:<14}{len(d1):>4}{m1:>10.1f}q{m2:>11.1f}q{ms:>12}{rm:>11}{ag:>11}",flush=True)
print("\n  (the three right-hand columns are different estimands; the paper will report the",flush=True)
print("   aggregate-volume one, which is well defined even when component medians are zero)",flush=True)
json.dump(dict(cohort=len(COH),recovery=OUT,deficit=DEF),
  open(os.path.expanduser("~/mnt/Research/RESULTS_round6.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_round6.json",flush=True)

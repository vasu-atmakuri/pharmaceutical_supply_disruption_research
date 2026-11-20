"""Recovery measured from the FIRST observed threshold crossing, with censoring.

The previous fixed-horizon design let the at-risk denominator grow with the
horizon (markets whose first decline came late entered the comparison with
little chance to recover). Anchoring on the first crossing and censoring the
unrecovered fixes that.
"""
import duckdb, numpy as np, json, os, collections
from _stable_json import stable   # see _stable_json.py: reproducible float precision
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
rng=np.random.default_rng(20261117)
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_v2.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_v2.parquet')").fetchall()
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"
LOr=YMIN-B0+2; H=12
COH=[(m,v[0],v[1]) for m,v in first.items() if v[0]>=LOr and v[0]+H-1<=TMAX
     and basec(m,v[0]) is not None and any(MQ[m].get(v[0]+k) is not None for k in range(1,H+1))]
band=lambda s:"minority" if s<.35 else ("mid" if s<.95 else "sole")
print(f"12-quarter cohort n={len(COH)}  {dict(collections.Counter(band(s) for _,_,s in COH))}")
def km(rows):
    """rows: (time, event) with event=1 recovered, 0 censored. Returns S(t) steps."""
    ts=sorted(set(t for t,_ in rows)); n=len(rows); S=1.0; out=[]
    at=n
    for t in ts:
        d=sum(1 for tt,e in rows if tt==t and e==1)
        c=sum(1 for tt,e in rows if tt==t and e==0)
        if at>0 and d>0: S*=1-d/at
        out.append((t,S,at,d)); at-=(d+c)
    return out
def logrank(A,B):
    allr=[(t,e,0) for t,e in A]+[(t,e,1) for t,e in B]
    ts=sorted(set(t for t,e,_ in allr if e==1))
    O=E=V=0.0; nA=len(A); nB=len(B)
    for t in ts:
        rA=sum(1 for tt,e in A if tt>=t); rB=sum(1 for tt,e in B if tt>=t)
        r=rA+rB
        dA=sum(1 for tt,e in A if tt==t and e==1); dB=sum(1 for tt,e in B if tt==t and e==1)
        d=dA+dB
        if r<=1 or d==0: continue
        O+=dA; E+=d*rA/r
        V+=d*(rA/r)*(1-rA/r)*((r-d)/(r-1))
    if V<=0: return None,None
    z=(O-E)/np.sqrt(V)
    from math import erfc
    return float(z), float(erfc(abs(z)/np.sqrt(2)))
RES={}
for thr,lbl in [(0.5,"50%"),(0.9,"90%")]:
    print(f"\n===== threshold {lbl} of baseline =====")
    grp={}
    for b in ["minority","sole"]:
        rows=[]; detail=[]
        for m,t,s in COH:
            if band(s)!=b: continue
            bl=basec(m,t)
            d=next((k for k in range(1,H+1) if (MQ[m].get(t+k) or 0)<thr*bl),None)
            if d is None: continue               # never crossed: not at risk of recovery
            r=next((k for k in range(d+1,H+1) if (MQ[m].get(t+k) or 0)>=thr*bl),None)
            if r is None: rows.append((H-d,0)); detail.append((m,d,None))
            else:         rows.append((r-d,1)); detail.append((m,d,r))
        grp[b]=rows
        ev=sum(e for _,e in rows)
        med_cross=np.median([d for _,d,_ in detail]) if detail else float('nan')
        print(f"  {b:<9} crossed={len(rows):>3}  recovered={ev:>3}  censored={len(rows)-ev:>3}  "
              f"median quarter of first crossing={med_cross:.1f}")
        K=km(rows)
        print("     KM survival (share still below threshold) by quarters since crossing:")
        print("       "+"  ".join(f"q{t}:{S:.2f}" for t,S,_,_ in K))
    z,p=logrank(grp["minority"],grp["sole"])
    print(f"  log-rank z={z:+.2f}  p={p:.3f}" if z is not None else "  log-rank not estimable")
    # landmark: first crossing within 4 quarters, recovery by q12
    print("  LANDMARK (first crossing within 4 quarters of exit, restoration observed by q12):")
    lm={}
    for b in ["minority","sole"]:
        k=n=0
        for m,t,s in COH:
            if band(s)!=b: continue
            bl=basec(m,t)
            d=next((j for j in range(1,5) if (MQ[m].get(t+j) or 0)<thr*bl),None)
            if d is None: continue
            n+=1
            if any((MQ[m].get(t+j) or 0)>=thr*bl for j in range(d+1,H+1)): k+=1
        lm[b]=(k,n)
        print(f"     {b:<9} {k}/{n}" + (f" = {k/n:.1%}" if n else ""))
    # The stored statistics are rounded to twelve decimals. The panels are rebuilt by
    # a parallel aggregation whose float summation order is not fixed, so a rebuild can
    # move a sum by one unit in the last place; that propagated into the log-rank
    # p-value's sixteenth digit and made this artifact differ from a fresh run while
    # nothing meaningful had changed. Twelve decimals is nine orders of magnitude more
    # precision than the three the paper reports, so this cannot hide a real change.
    RES[lbl]=dict(minority_rows=grp["minority"],sole_rows=grp["sole"],
                  logrank_z=None if z is None else round(z,12),
                  logrank_p=None if p is None else round(p,12),
                  landmark=lm)
# Band sizes in THIS cohort. The recovery cohort requires twelve quarters of
# follow-up where the main cohort requires six, so it is not the same set of
# markets and its denominators are not the main cohort's. Writing them here stops
# the manuscript pairing a crossing count with a denominator from elsewhere.
RES["cohort"]={"n":len(COH),
               **{b:sum(1 for _,_,s in COH if band(s)==b) for b in ("minority","mid","sole")}}
json.dump(stable(RES),open(_ROOT+"/results/recovery_censored.json","w"),indent=2)
print("\nwrote results/recovery_censored.json")

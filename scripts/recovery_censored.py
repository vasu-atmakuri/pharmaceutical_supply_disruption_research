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
def horizon(t):
    """Quarters after an exit that the panel can actually show, at most H.

    The search for a threshold crossing used to run to t+12 for every market while
    eligibility only required t+11 to be inside the panel, and a quarter the panel does
    not reach read as zero dispensing. Markets whose exit left eleven observable
    quarters therefore recorded an artificial crossing in the twelfth. Sixteen rows of
    the released manifest, all 2023Q2 exits, were produced that way.

    Inside the panel an absent quarter is different: it means CMS withheld a count
    under eleven prescriptions, which against a baseline of 200 or more is genuinely
    below both thresholds, so it is read as a crossing. Outside the panel absence means
    no observation, and nothing may be inferred from it."""
    return min(H, TMAX-t)
COH=[(m,v[0],v[1]) for m,v in first.items() if v[0]>=LOr and v[0]+H-1<=TMAX
     and basec(m,v[0]) is not None and any(MQ[m].get(v[0]+k) is not None for k in range(1,H+1))]
band=lambda s:"minority" if s<.35 else ("mid" if s<.95 else "sole")
# The main analysis cohort's eligibility rule, recomputed here so the difference
# between the two cohorts is measured rather than described. The main cohort requires
# an observed market quarter within t+1..t+6, because its outcome is the mean over
# those six quarters. Recovery needs no such quarter: its outcome is the time from a
# market's first crossing to its first restoration, which can both fall later. So the
# recovery cohort is not a subset of the main one, and the released manifest says
# which markets differ and why.
HI_MAIN=TMAX-6
MAIN=set()
for m,v in first.items():
    t=v[0]
    if not (LOr<=t<HI_MAIN): continue
    if basec(m,t) is None: continue
    if not any(MQ[m].get(t+k) is not None for k in range(1,7)): continue
    MAIN.add(m)
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
            Hm=horizon(t)
            d=next((k for k in range(1,Hm+1) if (MQ[m].get(t+k) or 0)<thr*bl),None)
            if d is None: continue               # never crossed: not at risk of recovery
            r=next((k for k in range(d+1,Hm+1) if (MQ[m].get(t+k) or 0)>=thr*bl),None)
            if r is None: rows.append((Hm-d,0)); detail.append((m,d,None))
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
            if any((MQ[m].get(t+j) or 0)>=thr*bl
                   for j in range(d+1,horizon(t)+1)): k+=1
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
# One row per market in the recovery cohort, at both thresholds: the quarter of the
# exit, the quarter of first crossing, the quarter of restoration if there is one, the
# censoring indicator and the time at risk. This is the file needed to reproduce the
# log-rank tests and the Kaplan-Meier curves without rerunning the panel build, and it
# also serves as the crosswalk between this cohort and the main analysis cohort.
import csv as _csv
_rows=[]
for thr,lbl in [(0.5,"50%"),(0.9,"90%")]:
    for m,t,s_ in COH:
        bl=basec(m,t)
        Hm=horizon(t)
        d=next((k for k in range(1,Hm+1) if (MQ[m].get(t+k) or 0)<thr*bl),None)
        r=None if d is None else next((k for k in range(d+1,Hm+1)
                                       if (MQ[m].get(t+k) or 0)>=thr*bl),None)
        _rows.append(dict(threshold=lbl, market=m, event_quarter=cal(t), event_tq=t,
            departing_share=round(s_,4), band=band(s_),
            baseline_rx=round(bl,1),
            in_main_cohort=int(m in MAIN),
            crossed=int(d is not None),
            first_crossing_q=("" if d is None else d),
            restored_q=("" if r is None else r),
            event_observed=("" if d is None else int(r is not None)),
            horizon_quarters=Hm,
            horizon_truncated=int(Hm<H),
            time_at_risk=("" if d is None else (r-d if r is not None else Hm-d))))
_mf=_ROOT+"/results/recovery_event_manifest.csv"
with open(_mf,"w",newline="") as _fh:
    _w=_csv.DictWriter(_fh,fieldnames=list(_rows[0].keys())); _w.writeheader(); _w.writerows(_rows)
print(f"wrote results/recovery_event_manifest.csv ({len(_rows)} rows, "
      f"{len(COH)} markets at two thresholds)")

# 3. the comparability sensitivity: the same test on the markets this cohort shares
# with the main analysis cohort, so a reader can see whether the extra markets carry
# the result.
RES["cohort"]["in_main"]=sum(1 for m,_,_ in COH if m in MAIN)
RES["cohort"]["recovery_only"]=sum(1 for m,_,_ in COH if m not in MAIN)
RES["cohort"]["recovery_only_sole"]=sum(1 for m,_,s_ in COH if m not in MAIN and band(s_)=="sole")
# The other direction: markets in the main cohort that this one excludes, because the
# panel ends before their twelfth post-event quarter. Reporting both directions is what
# makes the two cohort sizes reconcilable instead of merely different.
_inrec={m for m,_,_ in COH}
_main_sole=[m for m in MAIN if first[m][1]>=0.95]
# Counts the figure caption states, read from the manifest rather than typed. The
# caption said two markets at each threshold were censored on the quarter they crossed;
# the manifest said eight and six, because the boundary defect put crossings in a
# quarter the panel does not have.
RES["censored_at_crossing"]={}
for thr in ("50%","90%"):
    RES["censored_at_crossing"][thr]={
      b:sum(1 for r in _rows if r["threshold"]==thr and r["band"]==b
            and r["time_at_risk"]==0) for b in ("minority","sole")}
RES["truncated_horizon_markets"]=sum(1 for m,t,_s in COH if horizon(t)<H)
RES["cohort"]["main_sole"]=len(_main_sole)
RES["cohort"]["shared_sole"]=sum(1 for m in _main_sole if m in _inrec)
RES["cohort"]["main_only_sole"]=sum(1 for m in _main_sole if m not in _inrec)
print(f"  near-sole: main {len(_main_sole)}, recovery {RES['cohort']['sole']}, "
      f"shared {RES['cohort']['shared_sole']}, main only {RES['cohort']['main_only_sole']}, "
      f"recovery only {RES['cohort']['recovery_only_sole']}")
for thr,lbl in [(0.5,"50%"),(0.9,"90%")]:
    g={}
    for b in ("minority","sole"):
        rr=[]
        for m,t,s_ in COH:
            if band(s_)!=b or m not in MAIN: continue
            bl=basec(m,t)
            Hm=horizon(t)
            d=next((k for k in range(1,Hm+1) if (MQ[m].get(t+k) or 0)<thr*bl),None)
            if d is None: continue
            r=next((k for k in range(d+1,Hm+1) if (MQ[m].get(t+k) or 0)>=thr*bl),None)
            rr.append((Hm-d,0) if r is None else (r-d,1))
        g[b]=rr
    z2,p2=logrank(g["minority"],g["sole"])
    RES[lbl]["shared_cohort"]={"minority_n":len(g["minority"]),"sole_n":len(g["sole"]),
        "logrank_z":None if z2 is None else round(z2,12),
        "logrank_p":None if p2 is None else round(p2,12)}
    print(f"  {lbl} restricted to the markets shared with the main cohort: "
          f"minority {len(g['minority'])}, near-sole {len(g['sole'])}, "
          f"p={'n/a' if p2 is None else f'{p2:.3f}'}")
json.dump(stable(RES),open(_ROOT+"/results/recovery_censored.json","w"),indent=2)
print("\nwrote results/recovery_censored.json")

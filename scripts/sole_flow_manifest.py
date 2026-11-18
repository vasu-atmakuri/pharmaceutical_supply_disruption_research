"""One row per detected near-sole exit, with the stage at which it leaves the cohort.

The event flow reported in the manuscript is four exclusion counts and a final
cohort. Those are reconcilable only if every detected event can be placed in exactly
one stage, so this emits that assignment rather than the counts alone.
"""
import duckdb, numpy as np, csv, json, os
import os as _os
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
MQ={}; LMQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_v2.parquet')").fetchall():
    MQ.setdefault(m,{})[t]=r
for l,m,t,r in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_v2.parquet')").fetchall():
    LMQ.setdefault((m,l),{})[t]=r
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_v2.parquet')").fetchall()
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1
B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"

rows=[]
for m in sorted(first):
    t,s,dl=first[m]
    if s<.95: continue
    if not (LO<=t<HI):                      stage="outside_window"
    elif basec(m,t) is None:                stage="failed_baseline"
    elif not any(MQ[m].get(t+k) is not None for k in range(1,7)):
                                            stage="all_post_suppressed"
    else:                                   stage="observed"
    bl=basec(m,t); R=coll=""
    if stage=="observed":
        db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
        ob=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
        op=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
        if db>0: R=round((op-ob)/db,4)
        post=[MQ[m].get(t+k) for k in range(1,7)]
        coll=1 if np.mean([0.0 if v is None else v for v in post])<0.02*bl else 0
    rows.append(dict(market=m,departing_labeler=dl,event_quarter=cal(t),event_tq=t,
                     departing_share=round(s,4),stage=stage,
                     baseline_rx=("" if bl is None else round(bl,1)),
                     replacement_ratio=R,collapsed=coll))
out=f"{_ROOT}/results/near_sole_event_flow.csv"
with open(out,"w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

import collections
c=collections.Counter(r["stage"] for r in rows)
spec={x["tag"][0]:x for x in json.load(open(f"{_ROOT}/results/three_specifications.json"))}["C"]
fl=spec["sole_flow"]
for k,v in [("detected",len(rows)),("outside_window",c["outside_window"]),
            ("failed_baseline",c["failed_baseline"]),
            ("all_post_suppressed",c["all_post_suppressed"]),("observed",c["observed"])]:
    assert fl[k]==v, f"manifest {k}={v} but three_specifications reports {fl[k]}"
# How many of the observed cohort had exactly one active labeler, which is what
# distinguishes the near-sole stratum from a true single-labeler stratum.
LQ={}
for l,m,t,r in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_v2.parquet')").fetchall():
    LQ.setdefault((m,t),{})[l]=r
_obs=[r for r in rows if r["stage"]=="observed"]
_exact=0
for r in _obs:
    t=int(r["event_tq"]); labs=set()
    for q in range(t-4,t):
        for l,v in LQ.get((r["market"],q),{}).items():
            if v: labs.add(l)
    if len(labs)==1: _exact+=1
_nf=f"{_ROOT}/results/manuscript_numbers.json"
_nd=json.load(open(_nf))
_nd["cohort_exactly_one_labeler"]=_exact
_nd["cohort_two_plus_labelers"]=len(_obs)-_exact
json.dump(_nd,open(_nf,"w"),indent=1)
print(f"of {len(_obs)} observed events, {_exact} had exactly one active labeler in t-4..t-1")
print(f"{len(rows)} detected near-sole exits written to results/near_sole_event_flow.csv")
for k in ("outside_window","failed_baseline","all_post_suppressed","observed"):
    print(f"  {k:<22}{c[k]:>3}")
print(f"  {'sum':<22}{sum(c.values()):>3}  (matches three_specifications)")

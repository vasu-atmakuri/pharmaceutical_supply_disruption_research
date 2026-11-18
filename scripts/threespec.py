import duckdb, numpy as np, collections, json, os
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
def spec(tag,mq,lq,sl):
    MQ={}; LMQ={}
    for m,t,r in con.execute(f"SELECT mol,tq,rx FROM read_parquet('{mq}')").fetchall(): MQ.setdefault(m,{})[t]=r
    for l,m,t,r in con.execute(f"SELECT lab,mkt,tq,rx FROM read_parquet('{lq}')").fetchall(): LMQ.setdefault((m,l),{})[t]=r
    SL=con.execute(f"SELECT mol,lab,t,shr FROM read_parquet('{sl}')").fetchall()
    nlmq=con.execute(f"SELECT COUNT(*) FROM read_parquet('{lq}')").fetchone()[0]
    TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
    first={}
    for m,l,t,s in sorted(SL,key=lambda x:x[2]):
        if m not in first: first[m]=(t,s,l)
    def basec(m,t):
        p=[MQ[m].get(t+k) for k in range(B0,B1)]
        return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
    inwin={m:v for m,v in first.items() if LO<=v[0]<HI}
    COH=[m for m,v in inwin.items() if basec(m,v[0]) is not None]
    OBS=[m for m in COH if any(MQ[m].get(inwin[m][0]+k) is not None for k in range(1,7))]
    band=lambda s:"<35%" if s<.35 else ("35-65%" if s<.65 else ("65-95%" if s<.95 else "sole"))
    bands=collections.Counter(band(inwin[m][1]) for m in OBS)
    def R(m):
        t,s,dl=inwin[m]
        db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
        if db<=0: return None
        ob=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
        op=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
        return (op-ob)/db
    def coll(m):
        t,_,_=inwin[m]; bl=basec(m,t)
        post=[MQ[m].get(t+k) for k in range(1,7)]
        if all(v is None for v in post): return None
        return 1 if np.mean([0.0 if v is None else v for v in post])<0.02*bl else 0
    out=dict(tag=tag,markets=len(MQ),lmq=nlmq,events=len(SL),ev_markets=len(set(x[0] for x in SL)),
             inwin=len(inwin),baseline=len(COH),obs=len(OBS),bands=dict(bands),
             # sole-labeler exits inside the calendar window WITH a complete baseline,
             # before dropping those whose every post-event quarter is suppressed.
             # This is the denominator of the worst-case bound on the collapse rate.
             sole_cal_eligible=sum(1 for m in COH if band(inwin[m][1])=="sole"),
             sole_observed=sum(1 for m in OBS if band(inwin[m][1])=="sole"))
    for b in ["<35%","sole"]:
        sel=[m for m in OBS if band(inwin[m][1])==b]
        v=[R(m) for m in sel]; v=np.array([x for x in v if x is not None])
        c=[coll(m) for m in sel]; c=np.array([x for x in c if x is not None])
        out[b]=dict(n_R=int(len(v)),median_R=float(np.median(v)),
                    R_lt_002=float(np.mean(v<.02)),
                    n_coll=int(len(c)),collapse=float(np.mean(c)))
    return out
specs=[spec("A raw ingredient string, form-based bucket","/tmp/molq_nat.parquet","/tmp/lmq_nat.parquet","/tmp/sl_nat.parquet"),
       spec("B route-and-form bucket, raw ingredient string","/tmp/molq_rt.parquet","/tmp/lmq_rt.parquet","/tmp/sl_rt.parquet"),
       spec("C route-and-form bucket, normalized key","/tmp/molq_v2.parquet","/tmp/lmq_v2.parquet","/tmp/sl_v2.parquet")]
for s in specs:
    print(f"\n### {s['tag']}")
    print(f"  markets={s['markets']}  lmq={s['lmq']:,}  events={s['events']} across {s['ev_markets']} markets")
    print(f"  in window={s['inwin']}  baseline-complete={s['baseline']}  +post obs={s['obs']}  bands={s['bands']}"
          f"  (sum={sum(s['bands'].values())})")
    for b in ["<35%","sole"]:
        d=s[b]; print(f"    {b:<6} n_R={d['n_R']:>3} medianR={d['median_R']:>5.2f}  R<0.02={d['R_lt_002']:>5.1%}"
                      f"   n_coll={d['n_coll']:>3} collapse={d['collapse']:>5.1%}")
json.dump(specs,open(_ROOT+"/results/three_specifications.json","w"),indent=2)

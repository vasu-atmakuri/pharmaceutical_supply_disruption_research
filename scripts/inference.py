"""Replacement ratios, cause strata, collapse bounds and a fully audited
matched-control comparison, all on the normalized panel."""
import duckdb, numpy as np, json, os, collections
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
rng=np.random.default_rng(20261117)
# Every array fed to a bootstrap below is built from a sorted iteration. A fixed
# seed is not sufficient on its own: the same draws index different elements if
# the array order changes, which made the matched-set CI move between runs.
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
MQ={}; LMQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_v2.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
for l,m,t,r in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_v2.parquet')").fetchall(): LMQ.setdefault((m,l),{})[t]=r
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_v2.parquet')").fetchall()
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
EVT={m:v[0] for m,v in first.items()}
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"
inwin={m:v for m,v in first.items() if LO<=v[0]<HI}
OBS=[m for m,v in inwin.items() if basec(m,v[0]) is not None
     and any(MQ[m].get(v[0]+k) is not None for k in range(1,7))]
band=lambda s:"<35%" if s<.35 else ("35-65%" if s<.65 else ("65-95%" if s<.95 else "sole"))
def R(m):
    t,s,dl=inwin[m]
    db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
    if db<=0: return None
    ob=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
    return (op-ob)/db
def boot_med(v,n=20000):
    v=np.asarray(v); d=rng.choice(v,size=(n,len(v)),replace=True)
    q=np.median(d,axis=1); return float(np.percentile(q,2.5)),float(np.percentile(q,97.5))
OUT={}
print("REPLACEMENT RATIO by pre-exit concentration band (normalized panel)")
print(f"{'band':<9}{'n':>4}{'median':>8}{'95% CI':>18}{'mean':>8}{'vol-wtd':>9}{'P(R>=.5)':>10}{'P(R<.02)':>10}")
for b in ["<35%","35-65%","65-95%","sole"]:
    sel=sorted(m for m in OBS if band(inwin[m][1])==b)   # sorted: array order fixes the bootstrap
    v=np.array([R(m) for m in sel if R(m) is not None])
    w=np.array([basec(m,inwin[m][0]) for m in sel if R(m) is not None])
    if not len(v): continue
    lo,hi=boot_med(v)
    print(f"{b:<9}{len(v):>4}{np.median(v):>8.2f}  [{lo:>5.2f}, {hi:>5.2f}]{np.mean(v):>8.2f}"
          f"{np.sum(v*w)/np.sum(w):>9.2f}{np.mean(v>=.5):>9.1%}{np.mean(v<.02):>10.1%}")
    OUT[f"R_{b}"]=dict(n=int(len(v)),median=float(np.median(v)),ci=[lo,hi],mean=float(np.mean(v)),
                       volwtd=float(np.sum(v*w)/np.sum(w)),p_ge_half=float(np.mean(v>=.5)),
                       p_lt_2pct=float(np.mean(v<.02)))
# ---- matched risk-set controls, audited ----
sole=sorted(m for m in OBS if inwin[m][1]>=.95)   # sorted: matched-set order fixes the bootstrap
def collapse(m,t):
    bl=basec(m,t)
    post=[MQ[m].get(t+k) for k in range(1,7)]
    if all(v is None for v in post): return None
    return 1 if np.mean([0.0 if v is None else v for v in post])<0.02*bl else 0
sets=[]; reuse=collections.Counter()
for m in sole:
    t,s,dl=inwin[m]
    cands=[]
    for c in sorted(MQ):
        if c==m: continue
        if c in EVT and EVT[c]<=t+6: continue          # risk set: not yet exposed
        if basec(c,t) is None: continue
        labs=sorted({l for (cc,l) in LMQ if cc==c})   # sorted: set order is not stable across runs
        best=None
        for l in labs:
            lb=np.mean([LMQ[(c,l)].get(t+k) or 0.0 for k in range(B0,B1)])
            if lb<=0: continue
            sh=lb/basec(c,t)
            if best is None or abs(sh-s)<abs(best[1]-s): best=(l,sh)
        if best is None: continue
        y=collapse(c,t)
        if y is None: continue
        cands.append((abs(best[1]-s),c,y))
    cands.sort()
    pick=cands[:25]
    for _,c,_ in pick: reuse[c]+=1
    yt=collapse(m,t)
    if yt is None or not pick: continue
    sets.append(dict(treated=m,t=t,y_t=yt,controls=[(c,y) for _,c,y in pick]))
nt=len(sets); yt=np.array([S["y_t"] for S in sets])
cm=np.array([np.mean([y for _,y in S["controls"]]) for S in sets])
rd=float(np.mean(yt-cm))
uniq=len(reuse); tot=sum(reuse.values())
print(f"\nMATCHED RISK-SET COMPARISON   treated sets={nt}   control observations={tot}   unique control markets={uniq}")
print(f"  control markets used once: {sum(1 for v in reuse.values() if v==1)}   max reuse: {max(reuse.values())}")
print(f"  treated collapse rate  = {yt.mean():.1%}  ({int(yt.sum())}/{nt})")
print(f"  control collapse rate  = {cm.mean():.2%}")
print(f"  matched risk difference= {rd:+.1%}")
def bs(cluster_by_control):
    out=[]
    for _ in range(20000):
        idx=rng.integers(0,nt,nt)
        if not cluster_by_control:
            d=[sets[i]["y_t"]-np.mean([y for _,y in sets[i]["controls"]]) for i in idx]
        else:
            d=[]
            for i in idx:
                cs=sets[i]["controls"]
                j=rng.integers(0,len(cs),len(cs))
                d.append(sets[i]["y_t"]-np.mean([cs[k][1] for k in j]))
        out.append(np.mean(d))
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))
a=bs(False); b2=bs(True)
print(f"  95% CI, resampling matched sets        : [{a[0]:+.1%}, {a[1]:+.1%}]")
print(f"  95% CI, also resampling within controls: [{b2[0]:+.1%}, {b2[1]:+.1%}]")
OUT["matched"]=dict(sets=nt,control_obs=tot,unique_controls=uniq,
    used_once=int(sum(1 for v in reuse.values() if v==1)),max_reuse=int(max(reuse.values())),
    treated_rate=float(yt.mean()),control_rate=float(cm.mean()),risk_diff=rd,
    ci_sets=list(a),ci_sets_and_controls=list(b2))
json.dump(OUT,open(_ROOT+"/results/inference_normalized.json","w"),indent=2)
print("\nwrote results/inference_normalized.json")

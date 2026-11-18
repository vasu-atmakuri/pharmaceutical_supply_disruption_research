import duckdb, numpy as np, json, os, collections
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
rng=np.random.default_rng(20261117)
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
MQ={}; LMQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_v2.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
for l,m,t,r in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_v2.parquet')").fetchall(): LMQ.setdefault(m,{}).setdefault(t,{})[l]=r
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_v2.parquet')").fetchall()
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2
first={}
for m,l,t,s in sorted(SL,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"
LOr=YMIN-B0+2; H=12
COH=[(m,v[0],v[1]) for m,v in first.items() if v[0]>=LOr and v[0]+H-1<=TMAX
     and basec(m,v[0]) is not None and any(MQ[m].get(v[0]+k) is not None for k in range(1,H+1))]
band=lambda s:"under 35%" if s<.35 else ("35-95%" if s<.95 else "at least 95%")
def bmed(v,n=20000):
    v=np.asarray(v); d=rng.choice(v,size=(n,len(v)),replace=True)
    q=np.median(d,axis=1); return float(np.percentile(q,2.5)),float(np.percentile(q,97.5))
print("CUMULATIVE UNREPLACED DISPENSING, in quarters of baseline volume (12-quarter cohort)")
print(f"{'departing share':<16}{'n':>4}{'post-detection (t+4..t+11)':>30}{'total 12q':>24}")
DEF={}
for b in ["under 35%","35-95%","at least 95%"]:
    sel=[(m,t) for m,t,s in COH if band(s)==b]
    if not sel: continue
    tot=[];post=[];rows=[]
    for m,t in sel:
        bl=basec(m,t)
        d=[max(bl-(MQ[m].get(t+k) or 0.0),0)/bl for k in range(0,H)]
        tot.append(sum(d)); post.append(sum(d[4:]))
        rows.append((m,round(sum(d[4:]),3),round(sum(d),3)))
    a=bmed(post); c=bmed(tot)
    print(f"{b:<16}{len(sel):>4}   {np.median(post):>6.1f} [{a[0]:>4.1f}, {a[1]:>4.1f}]"
          f"            {np.median(tot):>6.1f} [{c[0]:>4.1f}, {c[1]:>4.1f}]")
    loo=[np.median([post[j] for j in range(len(post)) if j!=i]) for i in range(len(post))]
    print(f"{'':<16}    leave-one-out range of the post-detection median: {min(loo):.1f} to {max(loo):.1f}")
    DEF[b]=dict(n=len(sel),post_median=float(np.median(post)),post_ci=list(a),
                total_median=float(np.median(tot)),total_ci=list(c),
                loo_min=float(min(loo)),loo_max=float(max(loo)),events=rows)
print("\nLABELER ENTRY after exit, by departing share (any new labeler dispensing by t+6)")
for b in ["under 35%","35-95%","at least 95%"]:
    sel=[(m,t) for m,t,s in COH if band(s)==b]
    k=0
    for m,t in sel:
        pre={l for q in range(t+B0,t) for l in LMQ.get(m,{}).get(q,{})}
        new={l for q in range(t+1,t+7) for l in LMQ.get(m,{}).get(q,{})}-pre
        if new: k+=1
    print(f"  {b:<16}{k}/{len(sel)}" + (f" = {k/len(sel):.1%}" if sel else ""))
    DEF.setdefault("entry",{})[b]=[k,len(sel)]
json.dump(DEF,open(_ROOT+"/results/deficit_entry_normalized.json","w"),indent=2)
print("\nwrote results/deficit_entry_normalized.json")

"""Every sole-labeler exit under the raw specification, and what becomes of it
under the corrected market definition."""
import duckdb, numpy as np, json, os, csv, re
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
NK=json.load(open(os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/market_key_normalization_map.json")))
def load(mq,lq,sl):
    MQ={}; LM={}
    for m,t,r in con.execute(f"SELECT mol,tq,rx FROM read_parquet('{mq}')").fetchall(): MQ.setdefault(m,{})[t]=r
    for l,m,t,r in con.execute(f"SELECT lab,mkt,tq,rx FROM read_parquet('{lq}')").fetchall(): LM.setdefault((m,t),{})[l]=r
    SL=con.execute(f"SELECT mol,lab,t,shr FROM read_parquet('{sl}')").fetchall()
    return MQ,LM,SL
MQa,LMa,SLa=load('/tmp/molq_nat.parquet','/tmp/lmq_nat.parquet','/tmp/sl_nat.parquet')
MQc,LMc,SLc=load('/tmp/molq_v2.parquet','/tmp/lmq_v2.parquet','/tmp/sl_v2.parquet')
# route-aware raw key for each old form-based key: go via product-level rebuild is costly;
# instead match on the ingredient string, which both keys share before the bucket.
rt_keys=set(k for k in MQa)  # placeholder
def firsts(SL):
    f={}
    for m,l,t,s in sorted(SL,key=lambda x:x[2]):
        if m not in f: f[m]=(t,s,l)
    return f
FA,FC=firsts(SLa),firsts(SLc)
def basec(MQ,m,t):
    p=[MQ[m].get(t+k) for k in range(-6,-2)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"
TMAX=max(t for d in MQa.values() for t in d); LO,HI=(2016-1991)*4+1+6+2,TMAX-6
soleA=[(m,v[0],v[1],v[2]) for m,v in FA.items() if LO<=v[0]<HI and v[1]>=.95
       and basec(MQa,m,v[0]) is not None and any(MQa[m].get(v[0]+k) is not None for k in range(1,7))]
soleA.sort(key=lambda x:x[1])
# normalized key for each: the ingredient string is the part before ' | '
def toks(x):
    return set(w for w in re.split(r"[^A-Z0-9]+",x.split(" | ")[0].upper()) if len(w)>2)
CKEYS=sorted(set(NK.values()))
rows=[]
for m,t,s,lab in soleA:
    A=toks(m); best=None
    for k in CKEYS:
        if lab not in LMc.get((k,t-1),{}): continue
        B=toks(k)
        j=len(A&B)/max(1,len(A|B))
        if best is None or j>best[0]: best=(j,k)
    nk=best[1] if best and best[0]>0.3 else None
    nlab=len(LMc.get((nk,t-1),{})) if nk else None
    d=LMc.get((nk,t-1),{}) if nk else {}
    nshr=((d.get(lab) or 0)/max(1e-9,sum(v or 0 for v in d.values()))) if d else None
    still = (nk in FC and FC[nk][0]==t and FC[nk][1]>=.95) if nk else False
    rows.append(dict(event_quarter=cal(t),departing_labeler=lab,
        raw_market=m, raw_share=round(s,4), raw_labelers=len(LMa.get((m,t-1),{})),
        corrected_market=nk or "(unmatched)",
        corrected_share=None if nshr is None else round(nshr,4),
        corrected_labelers=nlab,
        still_sole_after_correction=int(bool(still))))
out=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/sole_event_transition.csv")
with open(out,"w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"{len(rows)} sole-labeler exits under the raw specification\n")
print(f"{'quarter':<8}{'lab':<7}{'raw share':>10}{'raw n':>6}{'corr share':>12}{'corr n':>8}  {'sole?':<6} market")
for r in rows:
    cs = "  n/a " if r['corrected_share'] is None else f"{r['corrected_share']:>11.1%}"
    print(f"{r['event_quarter']:<8}{r['departing_labeler']:<7}{r['raw_share']:>9.0%}{r['raw_labelers']:>6}"
          f"{cs}{str(r['corrected_labelers']):>8}  {'yes' if r['still_sole_after_correction'] else 'NO':<6} "
          f"{r['raw_market'][:44]}")
print(f"\nstill sole after correction: {sum(r['still_sole_after_correction'] for r in rows)} of {len(rows)}")

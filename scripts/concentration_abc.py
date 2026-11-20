"""Concentration across all market-quarters under each of the three specifications,
so that the contribution of route correction and of ingredient normalisation can be
separated, and so the direction of the route effect is measured rather than asserted."""
import duckdb, json, os, collections, numpy as np
from _stable_json import stable   # see _stable_json.py: reproducible float precision
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
def conc(lq):
    d=collections.defaultdict(dict)
    for lab,m,t,rx in con.execute(f"SELECT lab,mkt,tq,rx FROM read_parquet('{lq}')").fetchall():
        if rx: d[(m,t)][lab]=d[(m,t)].get(lab,0)+rx
    out={}
    for k,v in d.items():
        tot=sum(v.values())
        if tot<=0: continue
        sh=sorted((x/tot for x in v.values()),reverse=True)
        out[k]=dict(n=len(v),top=sh[0],hhi=sum(s*s for s in sh),rx=tot)
    return out
S={"A raw string, form bucket":conc('/tmp/lmq_nat.parquet'),
   "B route-and-form, raw string":conc('/tmp/lmq_rt.parquet'),
   "C route-and-form, normalised":conc('/tmp/lmq_v2.parquet')}
OUT={}
hdr=f"{'specification':<30}{'mkt-qtrs':>10}{'1 labeler':>11}{'vol':>8}{'top>=95%':>10}{'vol':>8}{'meanHHI':>9}"
print(hdr); print("-"*len(hdr))
for tag,X in S.items():
    tot=sum(v['rx'] for v in X.values())
    one=[v for v in X.values() if v['n']==1]; sole=[v for v in X.values() if v['top']>=.95]
    r=dict(mq=len(X), one=len(one), one_sh=len(one)/len(X), one_vol=sum(v['rx'] for v in one)/tot,
           sole=len(sole), sole_sh=len(sole)/len(X), sole_vol=sum(v['rx'] for v in sole)/tot,
           mean_hhi=float(np.mean([v['hhi'] for v in X.values()])),
           vw_hhi=sum(v['hhi']*v['rx'] for v in X.values())/tot)
    OUT[tag[0]]=r
    print(f"{tag:<30}{r['mq']:>10,}{r['one_sh']:>10.1%}{r['one_vol']:>8.2%}"
          f"{r['sole_sh']:>10.1%}{r['sole_vol']:>8.2%}{r['mean_hhi']:>9.3f}")
print("\nDecomposition of the change in the single-labeler volume share:")
a,b,c=OUT['A'],OUT['B'],OUT['C']
print(f"   A -> B  (route correction alone)        {a['one_vol']:.2%} -> {b['one_vol']:.2%}  "
      f"({(b['one_vol']-a['one_vol'])*100:+.2f} pp)")
print(f"   B -> C  (ingredient normalisation)      {b['one_vol']:.2%} -> {c['one_vol']:.2%}  "
      f"({(c['one_vol']-b['one_vol'])*100:+.2f} pp)")
print("\nSame, for the share of market-quarters with one labeler:")
print(f"   A -> B  {a['one_sh']:.1%} -> {b['one_sh']:.1%}   ({(b['one_sh']-a['one_sh'])*100:+.2f} pp)")
print(f"   B -> C  {b['one_sh']:.1%} -> {c['one_sh']:.1%}   ({(c['one_sh']-b['one_sh'])*100:+.2f} pp)")
# Does route splitting ever CREATE a single-labeler market-quarter?
A,B=S["A raw string, form bucket"],S["B route-and-form, raw string"]
created=sum(1 for k,v in B.items() if v['n']==1 and k not in A)
print(f"\nmarket-quarters that exist only under B (created by route splitting): "
      f"{sum(1 for k in B if k not in A):,}, of which single-labeler: {created:,}")
json.dump(stable(OUT),open(_ROOT+"/results/concentration_abc.json","w"),indent=2)

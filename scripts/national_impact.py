"""How much does the corrected market definition change the national picture of
supplier concentration? Computed for every market-quarter, raw versus corrected."""
import duckdb, json, os, collections, numpy as np
from _stable_json import stable   # see _stable_json.py: reproducible float precision
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
NK=json.load(open(_ROOT+"/results/market_key_normalization_map.json"))
def shares(lq):
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
RAW=shares('/tmp/lmq_nat.parquet')     # specification A: raw string, form bucket
COR=shares('/tmp/lmq_v2.parquet')      # specification C: route-and-form, normalised key
YMIN=(2016-1991)*4+1
def cal(t): return f"{1991+(t-1)//4}Q{(t-1)%4+1}"
TOT={}
def summarise(S,tag):
    tot_rx=sum(v['rx'] for v in S.values())
    sole=[v for v in S.values() if v['top']>=.95]
    near=[v for v in S.values() if v['top']>=.65]
    one=[v for v in S.values() if v['n']==1]
    print(f"{tag}")
    print(f"  market-quarters {len(S):,}   total prescriptions {tot_rx:,.0f}")
    TOT[tag]=float(tot_rx)
    print(f"  single-labeler market-quarters       {len(one):>7,} ({len(one)/len(S):6.1%})"
          f"   holding {sum(v['rx'] for v in one)/tot_rx:6.2%} of volume")
    print(f"  top share >= 95%                     {len(sole):>7,} ({len(sole)/len(S):6.1%})"
          f"   holding {sum(v['rx'] for v in sole)/tot_rx:6.2%} of volume")
    print(f"  top share >= 65%                     {len(near):>7,} ({len(near)/len(S):6.1%})"
          f"   holding {sum(v['rx'] for v in near)/tot_rx:6.2%} of volume")
    print(f"  mean HHI {np.mean([v['hhi'] for v in S.values()]):.3f}   "
          f"volume-weighted HHI {sum(v['hhi']*v['rx'] for v in S.values())/tot_rx:.3f}")
    return dict(mq=len(S),rx=tot_rx,single=len(one),sole=len(sole),near=len(near),
                single_vol=sum(v['rx'] for v in one)/tot_rx,
                sole_vol=sum(v['rx'] for v in sole)/tot_rx,
                mean_hhi=float(np.mean([v['hhi'] for v in S.values()])))
A=summarise(RAW,"SPECIFICATION A  raw ingredient string, dosage-form bucket")
print()
C=summarise(COR,"SPECIFICATION C  route-and-form bucket, normalised ingredient key")
# Reclassification: follow each raw sole-source market-quarter into its corrected market
print("\nRECLASSIFICATION of raw single-source market-quarters")
moved=kept=unmatched=0; moved_rx=kept_rx=0.0; examples=collections.Counter()
for (m,t),v in RAW.items():
    if v['top']<.95: continue
    nk=NK.get(m)
    if nk is None:
        # raw key is form-based; find its route-aware spelling by ingredient
        cand=[k for k in NK if k.split(" | ")[0]==m.split(" | ")[0]]
        nk=NK[cand[0]] if cand else None
    c=COR.get((nk,t)) if nk else None
    if c is None: unmatched+=1; continue
    if c['top']>=.95: kept+=1; kept_rx+=v['rx']
    else:
        moved+=1; moved_rx+=v['rx']; examples[m.split(" | ")[0][:46]]+=1
tot=moved+kept
print(f"  raw single-source market-quarters matched to a corrected market: {tot:,}  (unmatched {unmatched:,})")
print(f"  still single-source after correction : {kept:>7,} ({kept/tot:6.1%})")
print(f"  NOT single-source after correction   : {moved:>7,} ({moved/tot:6.1%})"
      f"   carrying {moved_rx/(moved_rx+kept_rx):.1%} of the volume in that group")
print("\n  ingredients most often reclassified out of single-source status:")
for k,n in examples.most_common(12): print(f"      {n:>4}  {k}")
json.dump(stable(dict(spec_A=A,spec_C=C,total_rx=TOT,reclassified=moved,retained=kept,
               unmatched=unmatched,
               reclassified_volume_share=moved_rx/(moved_rx+kept_rx) if tot else None)),
  open(_ROOT+"/results/national_impact.json","w"),indent=2)

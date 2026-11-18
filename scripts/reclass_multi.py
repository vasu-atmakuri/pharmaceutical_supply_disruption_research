"""Reclassification of raw near-sole market-quarters under three mapping rules.

A raw market can split into several corrected markets. Assigning it to the largest
component is one choice among several, so all three are reported.
"""
import duckdb, json, os, collections
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
NK=json.load(open(_ROOT+"/results/market_key_normalization_map.json"))
def conc(lq):
    d=collections.defaultdict(dict)
    for lab,m,t,rx in con.execute(f"SELECT lab,mkt,tq,rx FROM read_parquet('{lq}')").fetchall():
        if rx: d[(m,t)][lab]=d[(m,t)].get(lab,0)+rx
    out={}
    for k,v in d.items():
        tot=sum(v.values())
        if tot>0:
            sh=sorted((x/tot for x in v.values()),reverse=True)
            out[k]=dict(n=len(v),top=sh[0],rx=tot)
    return out
RAW=conc('/tmp/lmq_nat.parquet'); COR=conc('/tmp/lmq_v2.parquet')
ing2=collections.defaultdict(set)
for raw,norm in NK.items(): ing2[raw.split(" | ")[0]].add(norm)
R=dict(largest=collections.Counter(), anyc=collections.Counter(), allc=collections.Counter())
V=dict(flagged=0.0, in_nearsole=0.0, largest_rx_reclass=0.0)
ncomp=collections.Counter()
for (m,t),v in sorted(RAW.items()):
    if v['top']<.95: continue
    # sorted: the component list order decides which of two equal-volume components
    # max() returns, which moved the largest-component count between runs
    comps=sorted(((nk,COR[(nk,t)]) for nk in ing2.get(m.split(" | ")[0],()) if (nk,t) in COR),
                 key=lambda x: x[0])
    if not comps: continue
    ncomp[len(comps)]+=1
    V['flagged']+=v['rx']
    # rule 1: largest component
    big=max(comps,key=lambda x:(x[1]['rx'],x[0]))   # deterministic tie-break on the key
    _rc = big[1]['top']<.95
    R['largest']['reclass' if _rc else 'still']+=1
    # Volume of the raw market-quarters that THIS rule reclassifies. Conceptually
    # distinct from the allocation measure below: this counts whole raw markets whose
    # largest component is no longer near-sole; that one splits each raw market's
    # volume across its components. They need not be equal and are reported apart.
    V['largest_rx_reclass'] += v['rx'] if _rc else 0
    # rule 2: any component still near-sole
    R['anyc']['still' if any(c['top']>=.95 for _,c in comps) else 'reclass']+=1
    # rule 3: all components near-sole
    R['allc']['still' if all(c['top']>=.95 for _,c in comps) else 'reclass']+=1
    # volume allocation: how much of this raw market's dispensing lands in a near-sole corrected market
    tot=sum(c['rx'] for _,c in comps)
    if tot>0:
        near=sum(c['rx'] for _,c in comps if c['top']>=.95)
        V['in_nearsole']+=v['rx']*near/tot
print("raw near-sole market-quarters mapped:",sum(ncomp.values()))
print("components per raw market-quarter:",dict(sorted(ncomp.items())))
print()
for key,lab in [("largest","largest corrected component (manuscript rule)"),
                ("anyc","any corrected component still near-sole"),
                ("allc","every corrected component still near-sole")]:
    c=R[key]; n=c['still']+c['reclass']
    print(f"  {lab:<46} reclassified {c['reclass']:>6,} / {n:,} = {c['reclass']/n:.1%}")
print(f"\n  largest-component rule, by volume: {V['largest_rx_reclass']:,.0f} of {V['flagged']:,.0f} "
      f"flagged prescriptions = {V['largest_rx_reclass']/V['flagged']:.1%}")
print(f"\n  volume-allocation measure: of the {V['flagged']:,.0f} prescriptions flagged as near-sole")
print(f"  under the raw convention, {V['in_nearsole']/V['flagged']:.1%} land in a corrected market that")
print(f"  is still near-sole, so {1-V['in_nearsole']/V['flagged']:.1%} of flagged dispensing is reclassified.")
out=dict(components=dict(ncomp),
         largest_reclass=R['largest']['reclass'], largest_n=R['largest']['still']+R['largest']['reclass'],
         any_reclass=R['anyc']['reclass'], all_reclass=R['allc']['reclass'],
         flagged_rx=V['flagged'], vol_still_nearsole=V['in_nearsole']/V['flagged'],
         vol_reclassified=1-V['in_nearsole']/V['flagged'],
         largest_rx_reclass=V['largest_rx_reclass'],
         largest_vol_rate=V['largest_rx_reclass']/V['flagged'])
for k in ['largest','anyc','allc']:
    out[k+"_rate"]=R[k]['reclass']/(R[k]['still']+R[k]['reclass'])
json.dump(out,open(_ROOT+"/results/reclassification_rules.json","w"),indent=2)

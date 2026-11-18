import duckdb, json, os, collections, numpy as np, re, glob
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
OUT={}
# ---- 1. route coverage by year and by dispensing volume ----
px=sorted(glob.glob(os.path.expanduser("~/work/partsxx/*.parquet")))
q=f"""SELECT n.yr, SUM(n.rx) rx,
       SUM(CASE WHEN xw.route IS NOT NULL AND xw.route<>'' THEN n.rx ELSE 0 END) rx_route
      FROM read_parquet({px!r}) n
      JOIN read_parquet('/tmp/xw_route.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
      JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
      WHERE n.rx IS NOT NULL AND xw.generic<>'' AND pt.ptype='HUMAN PRESCRIPTION DRUG' AND n.yr>=2016
      GROUP BY 1 ORDER BY 1"""
print("route coverage by dispensing volume:")
cov={}
for yr,rx,rxr in con.execute(q).fetchall():
    cov[int(yr)]=round(rxr/rx*100,1); print(f"   {int(yr)}  {rxr/rx:6.1%}")
OUT["route_coverage_by_year"]=cov
OUT["route_coverage_volume_min"]=min(cov.values()); OUT["route_coverage_volume_max"]=max(cov.values())
# ---- 2. concentration under a strength-inclusive market definition ----
con.execute(f"""CREATE OR REPLACE TABLE js AS SELECT n.lab,(n.yr-1991)*4+n.qtr tq,n.rx,
   xw.generic||' | '||COALESCE(xw.route,'')||' | '||COALESCE(p.strength,'') mkt
  FROM read_parquet({px!r}) n
  JOIN read_parquet('/tmp/xw_route.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
  JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
  LEFT JOIN (SELECT lpad(split_part(PRODUCTNDC,'-',1),5,'0') lab, lpad(split_part(PRODUCTNDC,'-',2),4,'0') pcode,
                    any_value(ACTIVE_NUMERATOR_STRENGTH) strength
             FROM read_csv_auto('{os.path.expanduser("~/mnt/Research/crosswalk/product.txt")}',delim='\t',header=true,ignore_errors=true)
             GROUP BY 1,2) p ON p.lab=lpad(n.lab,5,'0') AND p.pcode=lpad(n.pcode,4,'0')
  WHERE n.rx IS NOT NULL AND xw.generic<>'' AND pt.ptype='HUMAN PRESCRIPTION DRUG'""")
rows=con.execute("SELECT mkt,tq,lab,SUM(rx) rx FROM js GROUP BY 1,2,3").fetchall()
d=collections.defaultdict(dict)
for m,t,l,rx in rows:
    if rx: d[(m,t)][l]=d[(m,t)].get(l,0)+rx
tot=0.0; one=0; near=0; onev=0.0; nearv=0.0
for k,v in d.items():
    s=sum(v.values())
    if s<=0: continue
    tot+=s; top=max(v.values())/s
    if len(v)==1: one+=1; onev+=s
    if top>=.95: near+=1; nearv+=s
OUT["strength_market_quarters"]=len(d)
OUT["strength_single_share"]=round(one/len(d)*100,1); OUT["strength_single_vol"]=round(onev/tot*100,2)
OUT["strength_nearsole_share"]=round(near/len(d)*100,1); OUT["strength_nearsole_vol"]=round(nearv/tot*100,2)
print(f"\nstrength-inclusive definition: {len(d):,} market-quarters")
print(f"   single-labeler {one/len(d):.1%}  (volume {onev/tot:.2%})")
print(f"   near-sole      {near/len(d):.1%}  (volume {nearv/tot:.2%})")
# ---- 3. influential observations in the minority replacement ratio ----
MQ={}; LMQ={}
for m,t,rx in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_v2.parquet')").fetchall(): MQ.setdefault(m,{})[t]=rx
for l,m,t,rx in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_v2.parquet')").fetchall(): LMQ.setdefault((m,l),{})[t]=rx
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_v2.parquet')").fetchall()
TMAX=max(t for dd in MQ.values() for t in dd); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
first={}
for m,l,t,s in sorted(SL,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
inwin={m:v for m,v in first.items() if LO<=v[0]<HI}
OBS=[m for m,v in inwin.items() if basec(m,v[0]) is not None and any(MQ[m].get(v[0]+k) is not None for k in range(1,7))]
def R(m):
    t,s,dl=inwin[m]
    db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
    if db<=0: return None
    ob=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
    return (op-ob)/db
sel=[(m,R(m),basec(m,inwin[m][0])) for m in OBS if inwin[m][1]<.35 and R(m) is not None]
sel.sort(key=lambda x:-x[1])
v=np.array([x[1] for x in sel]); w=np.array([x[2] for x in sel])
print(f"\nminority band n={len(v)}  median {np.median(v):.2f}  mean {np.mean(v):.2f}  vol-wtd {np.sum(v*w)/np.sum(w):.2f}")
for k in (1,3,5):
    vv=v[k:]; ww=w[k:]
    print(f"   excluding the {k} largest ratios: median {np.median(vv):.2f}  mean {np.mean(vv):.2f}  vol-wtd {np.sum(vv*ww)/np.sum(ww):.2f}")
    OUT[f"minority_excl{k}_median"]=round(float(np.median(vv)),2)
    OUT[f"minority_excl{k}_mean"]=round(float(np.mean(vv)),2)
    OUT[f"minority_excl{k}_volwtd"]=round(float(np.sum(vv*ww)/np.sum(ww)),2)
print("   largest ratios:", [f"{x[1]:.0f}" for x in sel[:5]])
OUT["minority_top_ratios"]=[round(float(x[1]),1) for x in sel[:5]]
json.dump(OUT,open(os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/sensitivities.json"),"w"),indent=2)
print("\nwrote results/sensitivities.json")

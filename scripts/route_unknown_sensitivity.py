"""Does pooling unknown-route products into OTHER distort measured concentration?

The route bucketing sends two different groups to OTHER: products whose FDA listing
records a route that maps to no named bucket, and products with no route at all whose
form string the fallback cascade cannot classify. Pooling them means products of the
same ingredient but genuinely different routes can share a market because neither
route is identified, which is the error this paper is about, applied to itself.

This rebuilds the national concentration figures with the two groups kept apart and
reports the difference. Unknown-route records keep their own bucket, so an ingredient
with both an unknown-route and a named-route product no longer pools them.
"""
import duckdb, glob, json, os
import os as _os
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
_PARTS=_os.environ.get("SDUD_PARTS") or (_DATA+"/sdud_parts/*.parquet")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
px=sorted(glob.glob(_PARTS))

# the production macro, verbatim from natpanel_route.py, so the two cannot drift
src=open(f"{_ROOT}/scripts/natpanel_route.py").read()
macro=src[src.index('con.execute("""CREATE OR REPLACE MACRO'):]
macro=macro[:macro.index('""")')+4]
exec(macro)
# the variant: route absent AND the form cascade fell through -> its own bucket
con.execute("""CREATE OR REPLACE MACRO rbucket2(rt,f) AS
 CASE WHEN (rt IS NULL OR rt='') AND rbucket(COALESCE(rt,''),COALESCE(f,''))='OTHER'
      THEN 'UNKNOWN ROUTE' ELSE rbucket(COALESCE(rt,''),COALESCE(f,'')) END""")

def build(macro_name, tag):
    con.execute(f"""CREATE OR REPLACE TABLE j_{tag} AS
      SELECT n.lab,(n.yr-1991)*4+n.qtr tq,n.rx,
             xw.generic||' | '||{macro_name}(COALESCE(xw.route,''),COALESCE(xw.form,'')) AS mkt
      FROM read_parquet({px!r}) n
      JOIN read_parquet('/tmp/xw_route.parquet') xw
        ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
      JOIN read_parquet('/tmp/ptype.parquet') pt
        ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
      WHERE n.rx IS NOT NULL AND xw.generic<>'' AND pt.ptype='HUMAN PRESCRIPTION DRUG'
        AND (n.yr-1991)*4+n.qtr >= (2016-1991)*4+1""")
    con.execute(f"""CREATE OR REPLACE TABLE lmq_{tag} AS
      SELECT lab,mkt,tq,SUM(rx) rx FROM j_{tag} GROUP BY 1,2,3""")
    r=con.execute(f"""
      WITH m AS (SELECT mkt,tq,SUM(rx) tot,COUNT(*) nlab,MAX(rx) top FROM lmq_{tag}
                 WHERE rx IS NOT NULL GROUP BY 1,2)
      SELECT COUNT(*) mq, COUNT(DISTINCT mkt) markets,
             SUM(CASE WHEN nlab=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) single_mq,
             SUM(CASE WHEN top>=0.95*tot THEN 1 ELSE 0 END)*100.0/COUNT(*) nearsole_mq,
             SUM(CASE WHEN nlab=1 THEN tot ELSE 0 END)*100.0/SUM(tot) single_vol,
             SUM(CASE WHEN top>=0.95*tot THEN tot ELSE 0 END)*100.0/SUM(tot) nearsole_vol
      FROM m WHERE tot>0""").fetchone()
    return dict(market_quarters=r[0], markets=r[1], single_mq_pct=round(r[2],2),
                nearsole_mq_pct=round(r[3],2), single_vol_pct=round(r[4],2),
                nearsole_vol_pct=round(r[5],2))

base=build("rbucket","base")
alt =build("rbucket2","alt")
# Variant 3: drop unknown-route records entirely. Renaming the bucket is nearly a
# no-op, because OTHER is almost all unknown-route records already; what bounds the
# concern is whether the national picture depends on them at all.
con.execute("""CREATE OR REPLACE TABLE lmq_drop AS
  SELECT lab,mkt,tq,SUM(rx) rx FROM j_alt WHERE mkt NOT LIKE '%| UNKNOWN ROUTE'
  GROUP BY 1,2,3""")
def stats(tbl):
    r=con.execute(f"""
      WITH m AS (SELECT mkt,tq,SUM(rx) tot,COUNT(*) nlab,MAX(rx) top FROM {tbl}
                 WHERE rx IS NOT NULL GROUP BY 1,2)
      SELECT COUNT(*), COUNT(DISTINCT mkt),
             SUM(CASE WHEN nlab=1 THEN 1 ELSE 0 END)*100.0/COUNT(*),
             SUM(CASE WHEN top>=0.95*tot THEN 1 ELSE 0 END)*100.0/COUNT(*),
             SUM(CASE WHEN nlab=1 THEN tot ELSE 0 END)*100.0/SUM(tot),
             SUM(CASE WHEN top>=0.95*tot THEN tot ELSE 0 END)*100.0/SUM(tot)
      FROM m WHERE tot>0""").fetchone()
    return dict(market_quarters=r[0], markets=r[1], single_mq_pct=round(r[2],2),
                nearsole_mq_pct=round(r[3],2), single_vol_pct=round(r[4],2),
                nearsole_vol_pct=round(r[5],2))
drop=stats("lmq_drop")
# how much of the near-sole population lives in the unknown bucket
ub=con.execute("""
  WITH m AS (SELECT mkt,tq,SUM(rx) tot,MAX(rx) top FROM lmq_alt WHERE rx IS NOT NULL GROUP BY 1,2)
  SELECT COUNT(*), SUM(CASE WHEN top>=0.95*tot THEN 1 ELSE 0 END), SUM(tot)
  FROM m WHERE mkt LIKE '%| UNKNOWN ROUTE' AND tot>0""").fetchone()
# how many OTHER-bucket records have a route that is actually populated
op=con.execute("""SELECT COUNT(*) FROM read_parquet('/tmp/xw_route.parquet')
  WHERE rbucket(COALESCE(route,''),COALESCE(form,''))='OTHER'
    AND route IS NOT NULL AND route<>''""").fetchone()[0]
nu=con.execute("""SELECT COUNT(*), SUM(rx) FROM lmq_alt WHERE mkt LIKE '%| UNKNOWN ROUTE'""").fetchone()
tot=con.execute("SELECT SUM(rx) FROM lmq_alt").fetchone()[0]
split=con.execute("""
  WITH u AS (SELECT DISTINCT split_part(mkt,' | ',1) g FROM lmq_alt WHERE mkt LIKE '%| UNKNOWN ROUTE'),
       o AS (SELECT DISTINCT split_part(mkt,' | ',1) g FROM lmq_alt WHERE mkt NOT LIKE '%| UNKNOWN ROUTE')
  SELECT COUNT(*) FROM u JOIN o USING (g)""").fetchone()[0]
# composition of the OTHER bucket, which is what the manuscript passage reports
_ob=con.execute("""
  WITH x AS (SELECT generic g,
                    CASE WHEN route IS NULL OR route='' THEN 'unknown' ELSE 'known' END k
             FROM read_parquet('/tmp/xw_route.parquet')
             WHERE rbucket(COALESCE(route,''),COALESCE(form,''))='OTHER' AND generic<>'')
  SELECT COUNT(DISTINCT g),
         COUNT(DISTINCT CASE WHEN g IN (SELECT g FROM x WHERE k='known')
                              AND g IN (SELECT g FROM x WHERE k='unknown') THEN g END)
  FROM x""").fetchone()
_ovol=con.execute("""SELECT SUM(CASE WHEN mkt LIKE '%| OTHER' THEN rx ELSE 0 END)*100.0/SUM(rx)
  FROM lmq_base WHERE rx IS NOT NULL""").fetchone()[0]
out=dict(other_bucket_composition=dict(
             other_bucket_ingredients=_ob[0],
             ingredients_mixing_known_and_unknown=_ob[1],
             other_bucket_vol_pct=round(_ovol,3)),
         delta_nearsole_vol=round(alt["nearsole_vol_pct"]-base["nearsole_vol_pct"],3),
         base=base, unknown_route_separate=alt, unknown_route_dropped=drop,
         other_bucket_route_present=op,
         unknown_bucket_mq=ub[0], unknown_bucket_nearsole_mq=ub[1],
         delta_drop_nearsole_vol_pp=round(drop["nearsole_vol_pct"]-base["nearsole_vol_pct"],3),
         delta_drop_nearsole_mq_pp=round(drop["nearsole_mq_pct"]-base["nearsole_mq_pct"],3),
         unknown_route_lmq=nu[0], unknown_route_rx=nu[1],
         unknown_route_vol_share=round(100*nu[1]/tot,3),
         ingredients_split_by_change=split,
         delta_nearsole_vol_pp=round(alt["nearsole_vol_pct"]-base["nearsole_vol_pct"],3),
         delta_nearsole_mq_pp=round(alt["nearsole_mq_pct"]-base["nearsole_mq_pct"],3),
         delta_single_vol_pp=round(alt["single_vol_pct"]-base["single_vol_pct"],3))
json.dump(out,open(f"{_ROOT}/results/route_unknown_sensitivity.json","w"),indent=1)
print("                           production   kept separate   dropped")
for k,lab in [("markets","markets"),("nearsole_mq_pct","near-sole % of MQ"),
              ("nearsole_vol_pct","near-sole % of volume"),
              ("single_mq_pct","single-lab % of MQ"),
              ("single_vol_pct","single-lab % of volume")]:
    print(f"  {lab:<24}{base[k]:>11}{alt[k]:>15}{drop[k]:>11}")
print(f"\n  OTHER-bucket records whose route IS populated: {op} "
      f"(irrigation, extracorporeal, urethral), so separating unknown-route products")
print(f"  from genuine OTHER changes the partition for {op} records only.")
print(f"  unknown-route market-quarters: {ub[0]:,}, of which near-sole: {ub[1]:,}")
print(f"  OTHER-bucket ingredients: {_ob[0]:,}; mixing known and unknown route: {_ob[1]:,}")
print(f"  OTHER bucket is {_ovol:.3f}% of dispensing volume")
print(f"  dropping them moves near-sole volume by {drop['nearsole_vol_pct']-base['nearsole_vol_pct']:+.3f} points")
print(f"\n  unknown-route labeler-market-quarters: {nu[0]:,} carrying {nu[1]:,.0f} prescriptions "
      f"({100*nu[1]/tot:.3f}% of volume)")
print(f"  ingredients holding both an unknown-route and a named-route market: {split:,}")
print(f"  change in near-sole share of volume: {out['delta_nearsole_vol_pp']:+.3f} points")

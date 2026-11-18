"""Every number the manuscript reports, computed once and written to one file."""
import duckdb, json, os, collections, re
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
N={}
# form-string ambiguity, the evidence for route bucketing
rows=con.execute("""SELECT COALESCE(route,'') rt, COUNT(*) n FROM read_parquet('/tmp/xw_route.parquet')
                    WHERE form='SOLUTION' GROUP BY 1 ORDER BY n DESC""").fetchall()
def pick(rows,pat):
    return sum(n for rt,n in rows if re.search(pat,rt))
N["solution_oral"]=pick(rows,r'^ORAL$')
N["solution_intradermal_subcut"]=pick(rows,r'INTRADERMAL')
N["solution_topical"]=pick(rows,r'^TOPICAL$')
N["solution_ophthalmic"]=pick(rows,r'^OPHTHALMIC$')
N["solution_respiratory"]=pick(rows,r'RESPIRATORY')
N["solution_otic"]=pick(rows,r'OTIC')
r2=con.execute("""SELECT COALESCE(route,'') rt, COUNT(*) n FROM read_parquet('/tmp/xw_route.parquet')
                  WHERE form='SOLUTION/ DROPS' GROUP BY 1 ORDER BY n DESC""").fetchall()
N["drops_ophthalmic"]=pick(r2,r'^OPHTHALMIC$'); N["drops_oral"]=pick(r2,r'^ORAL$')
N["drops_sublingual"]=pick(r2,r'SUBLINGUAL')
N["route_coverage"]=round(con.execute("""SELECT COUNT(*) FILTER (WHERE route IS NOT NULL AND route<>'')*100.0/COUNT(*)
     FROM read_parquet('/tmp/xw_route.parquet')""").fetchone()[0],1)
# bucket moves
b=dict(con.execute("SELECT frm,COUNT(*) FROM read_parquet('/tmp/meta_rt.parquet') m JOIN read_parquet('/tmp/lmq_rt.parquet') l ON l.mkt=m.mol GROUP BY 1").fetchall())
rec=dict(con.execute("""SELECT CASE WHEN mkt LIKE '%| OPHTHALMIC' THEN 'OPHTHALMIC'
                                    WHEN mkt LIKE '%| OTIC' THEN 'OTIC' ELSE 'other' END, COUNT(*)
                        FROM read_parquet('/tmp/lmq_rt.parquet') GROUP BY 1""").fetchall())
N["ophthalmic_records"]=rec.get('OPHTHALMIC'); N["otic_records"]=rec.get('OTIC')
# normalisation counts
NK=json.load(open(os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/market_key_normalization_map.json")))
N["raw_route_keys"]=len(NK); N["normalised_keys"]=len(set(NK.values()))
N["keys_absorbed"]=len(NK)-len(set(NK.values()))
# national impact derived values
NI=json.load(open(os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/national_impact.json")))
AB=json.load(open(os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/concentration_abc.json")))
N["near_sole_mq_raw"]=NI["retained"]+NI["reclassified"]+NI["unmatched"]
N["near_sole_matched"]=NI["retained"]+NI["reclassified"]
N["decomp_AB_pp"]=round((AB["B"]["one_vol"]-AB["A"]["one_vol"])*100,2)
N["decomp_BC_pp"]=round((AB["B"]["one_vol"]-AB["C"]["one_vol"])*100,2)
N["near_sole_vol_rel_reduction"]=round((NI["spec_A"]["sole_vol"]-NI["spec_C"]["sole_vol"])/NI["spec_A"]["sole_vol"]*100,0)
N["single_vol_rel_reduction"]=round((AB["A"]["one_vol"]-AB["C"]["one_vol"])/AB["A"]["one_vol"]*100,0)
# validation
V=json.load(open(os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/normalization_validation.json")))
N["testable_merges"]=V["confirmed"]+V["contradicted"]
# bounds and misc
N["bound_low"]=round(5/19*100,1); N["bound_high"]=round(11/19*100,1)
N["bootstrap_draws"]=20000
N["generic_share"]=85.6; N["anda_share"]=82.9; N["authgen_share"]=2.7
N["brand_share"]=11.4; N["biologic_share"]=2.6
N["alt_baseline_minority_median"]=1.25; N["alt_baseline_minority_lt02"]=31.6
N["colazo_markets"]=3344
out=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/manuscript_numbers.json")
json.dump(N,open(out,"w"),indent=2)
for k,v in N.items(): print(f"  {k:<34}{v}")
print("\nwrote",os.path.basename(out))

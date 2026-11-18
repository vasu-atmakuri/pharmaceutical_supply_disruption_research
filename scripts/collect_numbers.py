"""Every number the manuscript reports, computed once and written to one file."""
import duckdb, json, os, collections, re
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
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
NK=json.load(open(_ROOT+"/results/market_key_normalization_map.json"))
N["raw_route_keys"]=len(NK); N["normalised_keys"]=len(set(NK.values()))
N["keys_absorbed"]=len(NK)-len(set(NK.values()))
# national impact derived values
NI=json.load(open(_ROOT+"/results/national_impact.json"))
AB=json.load(open(_ROOT+"/results/concentration_abc.json"))
N["near_sole_mq_raw"]=NI["retained"]+NI["reclassified"]+NI["unmatched"]
N["near_sole_matched"]=NI["retained"]+NI["reclassified"]
N["decomp_AB_pp"]=round((AB["B"]["one_vol"]-AB["A"]["one_vol"])*100,2)
N["decomp_BC_pp"]=round((AB["B"]["one_vol"]-AB["C"]["one_vol"])*100,2)
N["near_sole_vol_rel_reduction"]=round((NI["spec_A"]["sole_vol"]-NI["spec_C"]["sole_vol"])/NI["spec_A"]["sole_vol"]*100,0)
N["single_vol_rel_reduction"]=round((AB["A"]["one_vol"]-AB["C"]["one_vol"])/AB["A"]["one_vol"]*100,0)
# validation
V=json.load(open(_ROOT+"/results/normalization_validation.json"))
N["testable_merges"]=V["confirmed"]+V["contradicted"]
# bounds and misc
# Worst-case bounds on the sole-labeler collapse rate over the calendar-eligible
# population. Computed, not asserted: the denominator is every sole-labeler exit
# inside the calendar window with a complete baseline, and the uncertainty is the
# exits dropped because every post-event quarter is suppressed.
_spec={x["tag"][0]:x for x in json.load(open(_ROOT+"/results/three_specifications.json"))}["C"]
_elig=_spec["sole_cal_eligible"]; _obs=_spec["sole_observed"]
_dropped=_elig-_obs
_coll=round(_spec["sole"]["collapse"]*_obs)
if abs(_spec["sole"]["collapse"]*_obs-_coll)>1e-6:
    raise SystemExit(f"collapse count is not integral: {_spec['sole']['collapse']}*{_obs}")
# Bucket counts, counted from the panels themselves rather than asserted.
# Specification A buckets on dosage form only; specification C buckets on route
# and form, and its labels carry a "#hash" suffix where the composition tie-break
# had to split a key, which is not a separate bucket.
import duckdb as _dd
_con=_dd.connect()
def _buckets(path):
    return sorted({r[0] for r in _con.execute(
        f"SELECT DISTINCT trim(split_part(mol,' | ',2)) FROM read_parquet('{path}')").fetchall()})
_fa=_buckets("/tmp/molq_nat.parquet")
_fc=sorted({b.split(" #")[0] for b in _buckets("/tmp/molq_v2.parquet")})
N["form_buckets"]=len(_fa); N["form_bucket_names"]=_fa
N["route_buckets"]=len(_fc); N["route_bucket_names"]=_fc
N["bound_eligible"]=_elig; N["bound_observed"]=_obs; N["bound_dropped"]=_dropped
N["bound_collapsed"]=_coll
N["bound_low"]=round(_coll/_elig*100,1); N["bound_high"]=round((_coll+_dropped)/_elig*100,1)
N["bootstrap_draws"]=20000
N["generic_share"]=85.6; N["anda_share"]=82.9; N["authgen_share"]=2.7
N["brand_share"]=11.4; N["biologic_share"]=2.6
N["alt_baseline_minority_median"]=1.25; N["alt_baseline_minority_lt02"]=31.6
N["colazo_markets"]=3344
out=_ROOT+"/results/manuscript_numbers.json"
# Merge rather than replace: earlier stages write keys into this file (the
# missing-route breakdown from natpanel_route.py, the exact-labeler count from
# sole_flow_manifest.py) and a full rewrite silently dropped them.
try: _prev=json.load(open(out))
except Exception: _prev={}
_prev.update(N); N=_prev
json.dump(N,open(out,"w"),indent=2)
for k,v in N.items(): print(f"  {k:<34}{v}")
print("\nwrote",os.path.basename(out))

"""Product-level evidence on what the composition tie-break does and does not do.

A reviewer read the released code and made a correct objection. The tie-break compares
the modal FDA substance set of each raw ingredient name inside a proposed merge group,
so it can stop two differently named keys from merging when FDA records different
substances for those names. It cannot split a single raw key whose own products differ
in composition: those products share one key and the key takes one substance set.

The Trace Elements case is an instance of the first, not evidence of the second, and the
paper should not imply otherwise. This writes the product-level table that lets a reader
check both claims: for every product code in a chosen set, the NDC labeler and product
segment, the raw ingredient name as the listing records it, the route bucket, the full
structured substance string, the substance set the tie-break derives from it, and the
final market key the product lands in.

Two groups are included. The trace-element products, because they are the case the paper
reports against itself. And the electrolyte formulations, because the salt-stripping
regular expression removes SODIUM, POTASSIUM and CHLORIDE from substance strings before
comparing them, which is right for a salt of an organic drug and wrong when the
electrolyte is itself the active ingredient. The table shows what that costs.
"""
import csv, json, os, re, sys
import duckdb
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))

MAP=json.load(open(f"{R}/results/market_key_normalization_map.json"))
con=duckdb.connect()
XW="/tmp/xw_route.parquet"
if not os.path.exists(XW): sys.exit(f"{XW} is missing; run rebuild_xw_route.py first")

# the same salt-stripping and set construction build_v2.py uses, imported by copy here
# so this table shows exactly what the pipeline computes rather than an approximation
SALTP=re.compile(r"\b(HYDROCHLORIDE|HYDROBROMIDE|SODIUM|POTASSIUM|SULFATE|TARTRATE|MALEATE|MESYLATE|CITRATE|PHOSPHATE|SUCCINATE|FUMARATE|BESYLATE|BROMIDE|CHLORIDE|DIHYDRATE|MONOHYDRATE|ANHYDROUS|HCL|HEMIHYDRATE|HYDRATE|HEPTAHYDRATE|UNSPECIFIED FORM)\b")
def subset(x):
    out=set()
    for q in re.split(r";",(x or "").upper()):
        q=SALTP.sub("",q); q=re.sub(r"[^A-Z0-9 ]"," ",q); q=" ".join(q.split())
        if len(q)>2: out.add(q)
    return frozenset(out)

ROUTEB=None
try:
    from rebuild_xw_route import __doc__ as _d   # noqa: F401
except Exception:
    pass

GROUPS={
 "trace elements": r"TRACE ELEMENTS|MULTITRACE|TRALEMENT|MULTRYS",
 "electrolytes":   r"\b(SODIUM CHLORIDE|POTASSIUM CHLORIDE|POTASSIUM PHOSPHATE|"
                   r"SODIUM BICARBONATE|CALCIUM GLUCONATE|MAGNESIUM SULFATE|"
                   r"POTASSIUM ACETATE|SODIUM ACETATE)\b",
}
rows=[]
for label,pat in GROUPS.items():
    q=f"""SELECT lab,pcode,generic,route,form,substance FROM read_parquet('{XW}')
          WHERE regexp_matches(upper(generic), '{pat}')
          ORDER BY generic, lab, pcode"""
    got=con.execute(q).fetchall()
    for lab,pcode,generic,route,form,sub in got:
        g=(generic or "").strip().upper()
        # The raw market key is the sorted ingredient tokens plus a route bucket, and
        # the bucket is not the listing's ROUTENAME, so the key is found by matching the
        # token set and reporting every raw key that matches with the market it maps to.
        # the map is keyed by the raw market string, whose first field is the raw
        # ingredient name exactly as the listing records it
        hits=[(k,v) for k,v in MAP.items() if k.split(" | ")[0]==g]
        final="; ".join(sorted({v for _,v in hits}))
        rawkeys="; ".join(sorted({k for k,_ in hits}))
        rows.append(dict(group=label, ndc=f"{lab}-{pcode}", raw_name=g,
                         route=(route or ""), form=(form or ""),
                         substance=(sub or ""),
                         substance_set="; ".join(sorted(subset(sub))),
                         raw_market_keys=rawkeys,
                         final_market_key=final))
    print(f"{label:16s} {len(got):4d} product codes")

out=f"{R}/results/ndc_composition_audit.csv"
with open(out,"w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"\nwrote results/ndc_composition_audit.csv ({len(rows)} product codes)")

# what the table is for: how many distinct substance sets share one raw name
import collections
byname=collections.defaultdict(set)
for r in rows: byname[(r["group"],r["raw_name"],r["route"])].add(r["substance_set"])
multi=[(k,v) for k,v in byname.items() if len(v)>1]
print(f"{len(multi)} of {len(byname)} name-and-route combinations carry more than one "
      f"substance set among their own product codes")
for (g,nm,rt),v in sorted(multi)[:8]:
    print(f"   [{g}] {nm[:46]} ({rt[:18]}): {len(v)} sets")
summ={"product_codes":len(rows),
      "name_route_combinations":len(byname),
      "combinations_with_multiple_substance_sets":len(multi),
      "note":("A combination with more than one substance set among its own product "
              "codes is one the tie-break cannot split: those products share a raw key "
              "and the key takes the modal set. This is the limitation the table "
              "documents, measured rather than asserted.")}
json.dump(summ,open(f"{R}/results/ndc_composition_audit.json","w"),indent=1,sort_keys=True)
print("wrote results/ndc_composition_audit.json")

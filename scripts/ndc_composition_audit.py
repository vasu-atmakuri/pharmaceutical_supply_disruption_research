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

# The route bucket is decided by a SQL CASE expression in natpanel_route.py. Rather
# than restate it here and risk the two drifting apart, the expression is read out of
# that file and used as written, so this audit buckets a product exactly as the panel
# does. If the panel's rule changes, this changes with it or fails loudly.
_np=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "natpanel_route.py")).read()
_i=_np.index(" CASE\n  WHEN rt LIKE '%OPHTHALMIC%'")
_j=_np.index("ELSE 'OTHER' END", _i)+len("ELSE 'OTHER' END")
BUCKET_SQL=_np[_i:_j]
if "ORAL TABLET" not in BUCKET_SQL:
    sys.exit("could not read the route-bucket rule out of natpanel_route.py")

GROUPS={
 "trace elements": r"TRACE ELEMENTS|MULTITRACE|TRALEMENT|MULTRYS",
 "electrolytes":   r"\b(SODIUM CHLORIDE|POTASSIUM CHLORIDE|POTASSIUM PHOSPHATE|"
                   r"SODIUM BICARBONATE|CALCIUM GLUCONATE|MAGNESIUM SULFATE|"
                   r"POTASSIUM ACETATE|SODIUM ACETATE)\b",
}
rows=[]
for label,pat in GROUPS.items():
    q=f"""SELECT lab,pcode,generic,rt route,f form,substance,{BUCKET_SQL} AS bucket
          FROM (SELECT lab,pcode,generic,substance,
                       upper(COALESCE(route,'')) rt, upper(COALESCE(form,'')) f
                FROM read_parquet('{XW}')
                WHERE regexp_matches(upper(generic), '{pat}'))
          ORDER BY generic, lab, pcode"""
    got=con.execute(q).fetchall()
    for lab,pcode,generic,route,form,sub,bucket in got:
        g=(generic or "").strip().upper()
        # The product's own market, not every market that shares its ingredient name.
        # A raw market key is the raw ingredient name plus the route bucket, so the
        # bucket has to be resolved for this product before the key can be looked up.
        # Matching on the name alone concatenated an injectable, an oral-liquid and a
        # topical key onto the same record for half the populated rows, which is what a
        # reviewer found: the audit was showing what a name could map to rather than
        # where the product went.
        rawkey=f"{g} | {bucket}"
        final=MAP.get(rawkey, "")
        rawkeys=rawkey if rawkey in MAP else ""
        if not final:
            # the product's market is not in the panel: not dispensed in Medicaid in
            # the window, or not a human prescription drug
            final=""
        rows.append(dict(group=label, ndc=f"{lab}-{pcode}", raw_name=g,
                         route=(route or ""), form=(form or ""),
                         substance=(sub or ""),
                         route_bucket=bucket,
                         substance_set="; ".join(sorted(subset(sub))),
                         raw_market_keys=rawkeys,
                         final_market_key=final))
    print(f"{label:16s} {len(got):4d} product codes")

out=f"{R}/results/ndc_composition_audit.csv"
with open(out,"w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"\nwrote results/ndc_composition_audit.csv ({len(rows)} product codes)")

# What the table is for, counted three ways rather than one. A reviewer showed that the
# single "more than one substance set" count treated a missing set as a different
# composition, so a group with fourteen records carrying no structured substances and
# eleven carrying the same set was reported as a composition conflict. It is not one.
# The unit is also the panel's own unit now: the raw name with the resolved route
# bucket, which is what a market key is built from.
import collections
byk=collections.defaultdict(list)
for r in rows: byk[(r["group"],r["raw_name"],r["route_bucket"])].append(r)
# Four mutually exclusive categories. The previous version put every group containing
# any missing substance set into one bucket and called it partially populated, so 47
# groups with no usable substance set for any member were reported as having some
# evidence. A reviewer regrouped the released records and found it.
pop_conflict=[]; mixed=[]; all_missing=[]; complete=[]
for k,v in byk.items():
    sets={r["substance_set"] for r in v if r["substance_set"]}
    nmiss=sum(1 for r in v if not r["substance_set"])
    if len(sets)>1:    pop_conflict.append((k,len(sets),nmiss,len(v)))
    elif not sets:     all_missing.append((k,len(v)))
    elif nmiss:        mixed.append((k,nmiss,len(v)))
    else:              complete.append(k)

# The audit covers the whole FDA listing for these families, but only some of those
# products are in a Medicaid-panel market. Validation coverage is about the latter, so
# the two populations are separated rather than pooled: a disagreement among products
# that never enter the panel says nothing about the markets the paper reports.
assigned=[r for r in rows if r["final_market_key"]]
unassigned=[r for r in rows if not r["final_market_key"]]
def regroup(rs):
    d=collections.defaultdict(list)
    for r in rs: d[(r["group"],r["raw_name"],r["route_bucket"])].append(r)
    return d
def conflicts(d):
    out=[]
    for k,v in d.items():
        sets={r["substance_set"] for r in v if r["substance_set"]}
        if len(sets)>1: out.append(k)
    return out
ga,gu=regroup(assigned),regroup(unassigned)
ca,cu=conflicts(ga),conflicts(gu)
keys=collections.defaultdict(list)
for r in assigned: keys[r["final_market_key"]].append(r)
keys_nosub=[k for k,v in keys.items() if not any(r["substance_set"] for r in v)]
withsub=sum(1 for r in assigned if r["substance_set"])
nokey=unassigned
multikey=[r for r in rows if ";" in r["final_market_key"]]
print(f"\n{len(byk)} name-and-bucket combinations in the whole sample")
print(f"  {len(pop_conflict):3d} with two or more different populated substance sets")
print(f"  {len(mixed):3d} with one populated set plus records whose set is missing")
print(f"  {len(all_missing):3d} with no usable substance set for any member")
print(f"  {len(complete):3d} fully populated and consistent")
print(f"\npanel-linked: {len(assigned)} product codes in {len(ga)} groups across "
      f"{len(keys)} market keys")
print(f"  {len(ca):3d} groups with conflicting populated sets")
print(f"  {withsub:3d} of {len(assigned)} assigned products have a usable substance set")
print(f"  {len(keys_nosub):3d} of {len(keys)} market keys have none for any member")
print(f"not panel-linked: {len(unassigned)} product codes in {len(gu)} groups, "
      f"{len(cu)} with conflicting populated sets")
print(f"  {len(multikey):3d} product codes resolve to more than one market key")
for k,n,nm,tot in sorted(pop_conflict)[:8]:
    _in="panel" if any(r["final_market_key"] for r in byk[k]) else "not in panel"
    print(f"     [{_in}] {k[1][:38]} ({k[2]}): {n} populated sets of {tot} records")
summ={"product_codes":len(rows),
      "name_bucket_combinations":len(byk),
      "combinations_with_conflicting_populated_sets":len(pop_conflict),
      "combinations_mixed_populated_and_missing":len(mixed),
      "combinations_with_no_usable_substance_set":len(all_missing),
      "combinations_fully_populated_and_consistent":len(complete),
      "product_codes_without_a_market_in_the_panel":len(nokey),
      "product_codes_resolving_to_more_than_one_market":len(multikey),
      "panel_linked":{"product_codes":len(assigned),"groups":len(ga),
         "market_keys":len(keys),"conflicting_groups":len(ca),
         "products_with_a_usable_substance_set":withsub,
         "market_keys_with_no_usable_substance_set":len(keys_nosub),
         "example_keys_without_substance_data":sorted(keys_nosub)[:6]},
      "not_panel_linked":{"product_codes":len(unassigned),"groups":len(gu),
         "conflicting_groups":len(cu)},
      "note":("Four mutually exclusive categories on the panel's own unit, the raw "
              "ingredient name with its resolved route bucket. The panel-linked split "
              "matters for validation coverage: a disagreement among product codes that "
              "never enter a Medicaid-panel market is a disagreement in the FDA listing, "
              "not in a market this paper reports. A blank substance set can also be the "
              "salt-stripping step erasing an electrolyte's own name, which is why the "
              "keys without any usable set are counted and named.")}
json.dump(summ,open(f"{R}/results/ndc_composition_audit.json","w"),indent=1,sort_keys=True)
print("wrote results/ndc_composition_audit.json")

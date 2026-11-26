import duckdb, os, csv, json, collections
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
C=_DATA+"/crosswalk"
rows=[]
with open(C+"/product.txt", encoding='latin-1') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        ndc=(r.get('PRODUCTNDC') or '').strip()
        if '-' not in ndc: continue
        lab,pc=ndc.split('-')[0],ndc.split('-')[1]
        rows.append((lab.zfill(5),pc.zfill(4),
            (r.get('NONPROPRIETARYNAME') or '').strip().upper(),
            (r.get('SUBSTANCENAME') or '').strip().upper(),
            (r.get('PHARM_CLASSES') or '').strip(),
            (r.get('DOSAGEFORMNAME') or '').strip().upper(),
            (r.get('ROUTENAME') or '').strip().upper(), 0))
print("product.txt rows:",len(rows))
n0=len(rows)
with open(C+"/drug-ndc-0001-of-0001.json", encoding='utf-8', errors='replace') as f: d=json.load(f)
for r in d.get('results',[]):
    ndc=(r.get('product_ndc') or '')
    if '-' not in ndc: continue
    lab,pc=ndc.split('-')[0],ndc.split('-')[1]
    rt=r.get('route') or []
    rows.append((lab.zfill(5),pc.zfill(4),
        (r.get('generic_name') or '').strip().upper(),
        "; ".join(x.get('name','') for x in (r.get('active_ingredients') or [])).upper(),
        "; ".join(r.get('pharm_class') or []),
        (r.get('dosage_form') or '').strip().upper(),
        "; ".join(rt).strip().upper(), 1))
print("openFDA added:",len(rows)-n0)
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
con.execute("CREATE TABLE t(lab VARCHAR,pcode VARCHAR,generic VARCHAR,substance VARCHAR,pclass VARCHAR,form VARCHAR,route VARCHAR,src INT)")
con.executemany("INSERT INTO t VALUES (?,?,?,?,?,?,?,?)",rows)
# One listing per product code, chosen by a total order rather than by any_value.
# any_value picks an arbitrary row, and with parallel aggregation the choice varied
# between runs: a product code listed twice with different routes could land in
# either market, which moved the raw-to-corrected match counts by tens of
# market-quarters from one build to the next. It never moved a published number, but
# it could have. The order prefers FDA's own NDC directory (src 0) over the openFDA
# listing, then breaks ties on every field, so the winner is fixed and all of its
# fields come from the same listing rather than being mixed across listings.
con.execute("""COPY (
  SELECT lab,pcode,generic,substance,pclass,form,route FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY lab,pcode
      ORDER BY src, generic, substance, pclass, form, route) rn
    FROM t WHERE generic<>'')
  WHERE rn=1) TO '/tmp/xw_route.parquet' (FORMAT PARQUET)""")
n=con.execute("SELECT COUNT(*),COUNT(route) FILTER (WHERE route<>'') FROM read_parquet('/tmp/xw_route.parquet')").fetchone()
print(f"crosswalk rows {n[0]:,}  with a route {n[1]:,} ({n[1]/n[0]:.1%})")
print("\n=== routes attached to the forms that were mis-bucketed ===")
q="""SELECT form, route, COUNT(*) n FROM read_parquet('/tmp/xw_route.parquet')
     WHERE form IN ('SOLUTION','SUSPENSION','SOLUTION/ DROPS','SUSPENSION/ DROPS',
                    'SOLUTION, GEL FORMING / DROPS','SHAMPOO, SUSPENSION','SPRAY, SUSPENSION')
     GROUP BY 1,2 ORDER BY form, n DESC"""
cur=None
for f,rt,c in con.execute(q).fetchall():
    if f!=cur: print(f"  {f}"); cur=f
    print(f"      {rt[:46]:<48}{c:>7,}")


# ---- product type, needed to restrict the panel to human prescription drugs ----
# This was previously built by an ad-hoc command and not by any script, so a clean
# machine could not run the pipeline: natpanel_route.py joins /tmp/ptype.parquet and
# failed with "No files found". It comes from the same two listings as the crosswalk.
_pt=[]
with open(C+"/product.txt", encoding='latin-1') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        ndc=(r.get('PRODUCTNDC') or '').strip()
        if '-' not in ndc: continue
        a,b=ndc.split('-')[0],ndc.split('-')[1]
        _pt.append((a.zfill(5),b.zfill(4),(r.get('PRODUCTTYPENAME') or '').strip().upper()))
with open(C+"/drug-ndc-0001-of-0001.json", encoding='utf-8', errors='replace') as f:
    _d=json.load(f)
for r in _d.get('results',[]):
    ndc=(r.get('product_ndc') or '')
    if '-' not in ndc: continue
    a,b=ndc.split('-')[0],ndc.split('-')[1]
    _pt.append((a.zfill(5),b.zfill(4),(r.get('product_type') or '').strip().upper()))
_seen={}
for a,b,t in _pt:
    if t and (a,b) not in _seen: _seen[(a,b)]=t
con.execute("CREATE OR REPLACE TABLE ptype(lab VARCHAR,pcode VARCHAR,ptype VARCHAR)")
con.executemany("INSERT INTO ptype VALUES (?,?,?)",
                [(a,b,t) for (a,b),t in sorted(_seen.items())])
con.execute("COPY (SELECT * FROM ptype) TO '/tmp/ptype.parquet' (FORMAT PARQUET)")
print(f"product types: {len(_seen):,} NDCs; "
      f"{sum(1 for t in _seen.values() if t=='HUMAN PRESCRIPTION DRUG'):,} human prescription drug")


# ---- labeler display names, from FDA's own LABELERNAME field ----
# display_names.py used a hand-maintained list, which stopped the build as soon as the
# event cohort grew. Deriving them means a new labeler never needs a code change.
_ln={}
with open(C+"/product.txt", encoding='latin-1') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        ndc=(r.get('PRODUCTNDC') or '').strip()
        if '-' not in ndc: continue
        lab=ndc.split('-')[0].zfill(5)
        nm=(r.get('LABELERNAME') or '').strip()
        if nm: _ln.setdefault(lab,collections.Counter())[nm]+=1
_names={k:v.most_common(1)[0][0] for k,v in _ln.items()}
json.dump(_names,open(_ROOT+"/results/labeler_names.json","w"),indent=1)
print(f"labeler names: {len(_names):,} codes written to results/labeler_names.json")

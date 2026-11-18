import duckdb, os, csv, json, collections
C=os.path.expanduser("~/mnt/Research/crosswalk")
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
            (r.get('ROUTENAME') or '').strip().upper()))
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
        "; ".join(rt).strip().upper()))
print("openFDA added:",len(rows)-n0)
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
con.execute("CREATE TABLE t(lab VARCHAR,pcode VARCHAR,generic VARCHAR,substance VARCHAR,pclass VARCHAR,form VARCHAR,route VARCHAR)")
con.executemany("INSERT INTO t VALUES (?,?,?,?,?,?,?)",rows)
con.execute("""COPY (SELECT lab,pcode,any_value(generic) generic,any_value(substance) substance,
  any_value(pclass) pclass, any_value(form) form, any_value(route) route
  FROM t WHERE generic<>'' GROUP BY 1,2) TO '/tmp/xw_route.parquet' (FORMAT PARQUET)""")
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

import duckdb, os, csv, json
C=os.path.expanduser("~/mnt/Research/crosswalk")
rows=[]
with open(C+"/product.txt", encoding='latin-1') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        ndc=(r.get('PRODUCTNDC') or '').strip()
        if '-' not in ndc: continue
        lab,pc=ndc.split('-')[0],ndc.split('-')[1]
        rows.append((lab.zfill(5),pc.zfill(4),
          (r.get('MARKETINGCATEGORYNAME') or '').strip().upper(),
          (r.get('LABELERNAME') or '').strip().upper()))
print("product.txt:",len(rows),flush=True)
n0=len(rows)
with open(C+"/drug-ndc-0001-of-0001.json", encoding='utf-8', errors='replace') as f: d=json.load(f)
for r in d.get('results',[]):
    ndc=(r.get('product_ndc') or '')
    if '-' not in ndc: continue
    lab,pc=ndc.split('-')[0],ndc.split('-')[1]
    rows.append((lab.zfill(5),pc.zfill(4),
      (r.get('marketing_category') or '').strip().upper(),
      (r.get('labeler_name') or '').strip().upper()))
print("openFDA added:",len(rows)-n0,flush=True)
con=duckdb.connect(); con.execute("SET memory_limit='1200MB'")
con.execute("CREATE TABLE t(lab VARCHAR,pcode VARCHAR,mktcat VARCHAR,labname VARCHAR)")
con.executemany("INSERT INTO t VALUES (?,?,?,?)",rows)
con.execute("""COPY (SELECT lab,pcode,any_value(mktcat) mktcat,any_value(labname) labname
  FROM t WHERE mktcat<>'' GROUP BY 1,2) TO '/tmp/xcat.parquet' (FORMAT PARQUET)""")
print("\n=== marketing categories in crosswalk ===",flush=True)
for r in con.execute("""SELECT any_value(mktcat) c,COUNT(*) n FROM t WHERE mktcat<>'' GROUP BY lower(mktcat)
  ORDER BY n DESC LIMIT 14""").fetchall(): print(f"  {r[0][:44]:<46}{r[1]:>8,}",flush=True)

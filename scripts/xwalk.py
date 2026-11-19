import os as _os
_ROOT=_os.environ.get("PSDR_ROOT") or __ROOT+""
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
_PARTS=_os.environ.get("SDUD_PARTS") or (_DATA+"/sdud_parts/*.parquet")
import duckdb, os, csv, json, re
C=_DATA+"/crosswalk"
con=duckdb.connect('/tmp/xw.duckdb'); con.execute("SET memory_limit='1200MB'")
rows=[]
with open(C+"/product.txt", encoding='latin-1') as f:
    rd=csv.DictReader(f, delimiter='\t')
    for r in rd:
        ndc=(r.get('PRODUCTNDC') or '').strip()
        if '-' not in ndc: continue
        lab,pc=ndc.split('-')[0],ndc.split('-')[1]
        rows.append((lab.zfill(5), pc.zfill(4),
          (r.get('NONPROPRIETARYNAME') or '').strip().upper(),
          (r.get('SUBSTANCENAME') or '').strip().upper(),
          (r.get('PHARM_CLASSES') or '').strip(),
          (r.get('DOSAGEFORMNAME') or '').strip().upper()))
print("product.txt rows parsed:", len(rows), flush=True)
# add discontinued products from openFDA bulk
extra=0
with open(C+"/drug-ndc-0001-of-0001.json", encoding='utf-8', errors='replace') as f:
    d=json.load(f)
for r in d.get('results',[]):
    ndc=(r.get('product_ndc') or '')
    if '-' not in ndc: continue
    lab,pc=ndc.split('-')[0],ndc.split('-')[1]
    pcl=r.get('pharm_class') or []
    rows.append((lab.zfill(5), pc.zfill(4),
      (r.get('generic_name') or '').strip().upper(),
      ",".join(s.get('name','') for s in (r.get('active_ingredients') or [])).upper(),
      "; ".join(pcl), (r.get('dosage_form') or '').strip().upper()))
    extra+=1
print("openFDA rows added:", extra, flush=True)
con.execute("DROP TABLE IF EXISTS xw")
con.execute("CREATE TABLE xw(lab VARCHAR,pcode VARCHAR,generic VARCHAR,substance VARCHAR,pclass VARCHAR,form VARCHAR)")
con.executemany("INSERT INTO xw VALUES (?,?,?,?,?,?)", rows)
con.execute("""CREATE OR REPLACE TABLE xw1 AS SELECT lab,pcode,
  any_value(generic) generic, any_value(substance) substance,
  any_value(NULLIF(pclass,'')) pclass, any_value(form) form
  FROM xw WHERE generic<>'' GROUP BY 1,2""")
print("unique labeler-product keys:", con.execute("SELECT COUNT(*) FROM xw1").fetchone()[0], flush=True)
# EPC class extraction
con.execute("""CREATE OR REPLACE TABLE xw2 AS SELECT *,
  CASE WHEN pclass IS NULL THEN NULL ELSE
    regexp_extract(pclass,'([^;,]*\\[EPC\\])',1) END AS epc FROM xw1""")
print("with EPC class:", con.execute("SELECT COUNT(*) FROM xw2 WHERE epc IS NOT NULL AND epc<>''").fetchone()[0], flush=True)
con.execute("COPY (SELECT * FROM xw2) TO '/tmp/xw.parquet' (FORMAT PARQUET)")
print("wrote /tmp/xw.parquet", flush=True)

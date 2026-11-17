import duckdb, os, csv, json, numpy as np
C=os.path.expanduser("~/mnt/Research/crosswalk")
rows=[]
with open(C+"/product.txt",encoding='latin-1') as f:
    for r in csv.DictReader(f,delimiter='\t'):
        ndc=(r.get('PRODUCTNDC') or '').strip()
        if '-' not in ndc: continue
        a,b=ndc.split('-')[0],ndc.split('-')[1]
        rows.append((a.zfill(5),b.zfill(4),(r.get('APPLICATIONNUMBER') or '').strip().upper(),(r.get('MARKETINGCATEGORYNAME') or '').strip().upper()))
n0=len(rows)
d=json.load(open(C+"/drug-ndc-0001-of-0001.json",encoding='utf-8',errors='replace'))
for r in d.get('results',[]):
    ndc=(r.get('product_ndc') or '')
    if '-' not in ndc: continue
    a,b=ndc.split('-')[0],ndc.split('-')[1]
    rows.append((a.zfill(5),b.zfill(4),(r.get('application_number') or '').strip().upper(),(r.get('marketing_category') or '').strip().upper()))
print(f"rows: {n0} product.txt + {len(rows)-n0} openFDA",flush=True)
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute("CREATE TABLE a(lab VARCHAR,pcode VARCHAR,app VARCHAR,cat VARCHAR)")
con.executemany("INSERT INTO a VALUES (?,?,?,?)",rows)
# application id: use the approval number where present, else fall back to labeler+product so
# unmatched products are never merged with anything
con.execute("""CREATE OR REPLACE TABLE app AS SELECT lab,pcode,
  COALESCE(NULLIF(any_value(app),''),'NOAPP:'||lab||'-'||pcode) appid,
  any_value(cat) cat FROM a GROUP BY 1,2""")
cov=con.execute("SELECT AVG(CASE WHEN appid NOT LIKE 'NOAPP:%' THEN 1.0 ELSE 0 END) FROM app").fetchone()[0]
print(f"products with a real application number: {cov:.1%}",flush=True)
print("rebuilding product-level panel with application ids",flush=True)
import glob
px=sorted(glob.glob(os.path.expanduser("~/work/partsxx/*.parquet")))
con.execute(f"""CREATE OR REPLACE TABLE pq AS
 SELECT xw.generic||' | '||CASE
   WHEN xw.form IS NULL THEN 'UNK'
   WHEN xw.form LIKE '%INJECT%' OR xw.form LIKE '%INFUSION%' THEN 'INJECTABLE'
   WHEN xw.form LIKE '%TABLET%' THEN 'TABLET' WHEN xw.form LIKE '%CAPSULE%' THEN 'CAPSULE'
   WHEN xw.form LIKE '%SOLUTION%' OR xw.form LIKE '%SUSPENSION%' OR xw.form LIKE '%SYRUP%' OR xw.form LIKE '%ELIXIR%' OR xw.form LIKE '%LIQUID%' THEN 'ORAL LIQUID'
   WHEN xw.form LIKE '%CREAM%' OR xw.form LIKE '%OINTMENT%' OR xw.form LIKE '%GEL%' OR xw.form LIKE '%LOTION%' OR xw.form LIKE '%PATCH%' OR xw.form LIKE '%FILM%' THEN 'TOPICAL'
   WHEN xw.form LIKE '%AEROSOL%' OR xw.form LIKE '%INHAL%' OR xw.form LIKE '%POWDER, METERED%' OR xw.form LIKE '%SPRAY%' THEN 'INHALED/SPRAY'
   WHEN xw.form LIKE '%SUPPOSITORY%' OR xw.form LIKE '%ENEMA%' THEN 'RECTAL'
   WHEN xw.form LIKE '%OPHTH%' OR xw.form LIKE '%DROP%' THEN 'DROPS' ELSE 'OTHER' END mkt,
  lpad(n.lab,5,'0') lab, ap.appid appid, (n.yr-1991)*4+n.qtr tq, SUM(n.rx) rx
 FROM read_parquet({px!r}) n
 JOIN read_parquet('/tmp/xw.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
 JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
 JOIN app ap ON ap.lab=lpad(n.lab,5,'0') AND ap.pcode=lpad(n.pcode,4,'0')
 WHERE n.rx IS NOT NULL AND xw.generic<>'' AND pt.ptype='HUMAN PRESCRIPTION DRUG'
 GROUP BY 1,2,3,4""")
print("rows:",con.execute("SELECT COUNT(*) FROM pq").fetchone()[0],flush=True)
con.execute("COPY (SELECT * FROM pq) TO '/tmp/pq_app.parquet' (FORMAT PARQUET)")
print("\n=== LABELERS vs DISTINCT APPROVALS PER MARKET-QUARTER ===",flush=True)
r=con.execute("""SELECT AVG(nl) a, AVG(na) b, AVG(CASE WHEN na<nl THEN 1.0 ELSE 0 END) c,
  AVG(CASE WHEN nl>1 AND na=1 THEN 1.0 ELSE 0 END) d, COUNT(*) n
 FROM (SELECT mkt,tq,COUNT(DISTINCT lab) nl,COUNT(DISTINCT appid) na FROM pq WHERE rx>0 GROUP BY 1,2)""").fetchone()
print(f"  mean labelers per market-quarter:  {r[0]:.2f}",flush=True)
print(f"  mean approvals per market-quarter: {r[1]:.2f}",flush=True)
print(f"  share where approvals < labelers:  {r[2]:.1%}",flush=True)
print(f"  share that look competitive by labeler (>1) but are single-approval: {r[3]:.1%}  of {r[4]:,} market-quarters",flush=True)
print("\n  distribution of labeler count vs approval count:",flush=True)
for row in con.execute("""SELECT nl,ROUND(AVG(na),2) avg_app,COUNT(*) n FROM
  (SELECT mkt,tq,COUNT(DISTINCT lab) nl,COUNT(DISTINCT appid) na FROM pq WHERE rx>0 GROUP BY 1,2)
  WHERE nl<=8 GROUP BY 1 ORDER BY 1""").fetchall():
    print(f"   {row[0]} labeler(s): mean {row[1]} approvals   ({row[2]:,} market-quarters)",flush=True)

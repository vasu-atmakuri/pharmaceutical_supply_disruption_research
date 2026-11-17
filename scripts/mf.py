import duckdb, glob, os, numpy as np, json
W=os.path.expanduser("~/work/parts3"); parts=sorted(glob.glob(W+"/*.parquet"))
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")
# normalise dosage form into coarse buckets so trivial label variants don't split markets
con.execute("""CREATE OR REPLACE MACRO fbucket(f) AS
 CASE WHEN f IS NULL THEN 'UNK'
  WHEN f LIKE '%INJECT%' OR f LIKE '%INFUSION%' THEN 'INJECTABLE'
  WHEN f LIKE '%TABLET%' THEN 'TABLET'
  WHEN f LIKE '%CAPSULE%' THEN 'CAPSULE'
  WHEN f LIKE '%SOLUTION%' OR f LIKE '%SUSPENSION%' OR f LIKE '%SYRUP%' OR f LIKE '%ELIXIR%' OR f LIKE '%LIQUID%' THEN 'ORAL LIQUID'
  WHEN f LIKE '%CREAM%' OR f LIKE '%OINTMENT%' OR f LIKE '%GEL%' OR f LIKE '%LOTION%' OR f LIKE '%PATCH%' OR f LIKE '%FILM%' THEN 'TOPICAL'
  WHEN f LIKE '%AEROSOL%' OR f LIKE '%INHAL%' OR f LIKE '%POWDER, METERED%' OR f LIKE '%SPRAY%' THEN 'INHALED/SPRAY'
  WHEN f LIKE '%SUPPOSITORY%' OR f LIKE '%ENEMA%' THEN 'RECTAL'
  WHEN f LIKE '%OPHTH%' OR f LIKE '%DROP%' THEN 'DROPS'
  ELSE 'OTHER' END""")
con.execute(f"""CREATE OR REPLACE TABLE j AS SELECT n.lab,(n.yr-1991)*4+n.qtr tq,n.rx,
 xw.generic||' | '||fbucket(xw.form) AS mkt, xw.generic gen, fbucket(xw.form) frm,
 NULLIF(trim(xw.epc),'') epc
 FROM read_parquet({parts!r}) n
 JOIN read_parquet('/tmp/xw.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
 JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
 WHERE n.rx IS NOT NULL AND xw.generic<>'' AND pt.ptype='HUMAN PRESCRIPTION DRUG' AND n.yr>=2016""")
con.execute("CREATE OR REPLACE TABLE lmq AS SELECT lab,mkt,tq,SUM(rx) rx FROM j GROUP BY 1,2,3")
con.execute("CREATE OR REPLACE TABLE molq AS SELECT mkt mol,tq,SUM(rx) rx FROM lmq GROUP BY 1,2")
print("markets (ingredient x form):",con.execute("SELECT COUNT(DISTINCT mol) FROM molq").fetchone()[0],flush=True)
print("labeler-market-quarters:",con.execute("SELECT COUNT(*) FROM lmq").fetchone()[0],flush=True)
con.execute("""CREATE OR REPLACE TABLE sl AS
WITH s AS (SELECT lab,mkt,tq,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq ROWS BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4 FROM lmq),
 e AS (SELECT lab,mkt,tq FROM s WHERE pre4>=200 AND post4<0.05*pre4),
 f AS (SELECT lab,mkt,MIN(tq) t FROM e GROUP BY 1,2),
 fr AS (SELECT f.lab,f.mkt,f.t,SUM(l.rx) firm_rx FROM f JOIN lmq l ON l.lab=f.lab AND l.mkt=f.mkt
        AND l.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2,3),
 tt AS (SELECT f.mkt,f.t,SUM(m.rx) mol_rx FROM f JOIN molq m ON m.mol=f.mkt AND m.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2)
SELECT fr.lab,fr.mkt mol,fr.t,fr.firm_rx,tt.mol_rx,fr.firm_rx/tt.mol_rx shr
FROM fr JOIN tt ON tt.mkt=fr.mkt AND tt.t=fr.t WHERE tt.mol_rx>0""")
print("\nsupplier-loss events:",con.execute("SELECT COUNT(*) FROM sl").fetchone()[0],flush=True)
for lo,hi,nm in [(0,.35,"minor <35%"),(.35,.65,"35-65%"),(.65,.95,"65-95%"),(.95,1.01,"sole >=95%")]:
    c=con.execute(f"SELECT COUNT(*),COUNT(DISTINCT mol) FROM sl WHERE shr>={lo} AND shr<{hi}").fetchone()
    print(f"  {nm:<12} events={c[0]:>6,}  distinct markets={c[1]:>5,}",flush=True)
con.execute("COPY (SELECT * FROM sl) TO '/tmp/sl_mf.parquet' (FORMAT PARQUET)")
con.execute("COPY (SELECT * FROM molq) TO '/tmp/molq_mf.parquet' (FORMAT PARQUET)")
con.execute("COPY (SELECT DISTINCT mkt mol,gen,frm,epc FROM j) TO '/tmp/mktmeta.parquet' (FORMAT PARQUET)")
con.execute("COPY (SELECT lab,mkt mol,tq,rx FROM lmq) TO '/tmp/lmq_mf.parquet' (FORMAT PARQUET)")
print("\nwrote market-form panels",flush=True)

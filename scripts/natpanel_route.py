import duckdb, glob, os, numpy as np
px=sorted(glob.glob(os.path.expanduser("~/work/partsxx/*.parquet")))
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")
# Route-primary bucket. Route decides where a product acts; dosage form only
# subdivides the oral and injectable routes. Falls back to form when route is
# missing, with the ophthalmic/otic test placed BEFORE the solution test.
con.execute("""CREATE OR REPLACE MACRO rbucket(rt,f) AS
 CASE
  WHEN rt LIKE '%OPHTHALMIC%' THEN 'OPHTHALMIC'
  WHEN rt LIKE '%OTIC%' OR rt LIKE '%AURICULAR%' THEN 'OTIC'
  WHEN rt LIKE '%NASAL%' THEN 'NASAL'
  WHEN rt LIKE '%INHALATION%' OR rt LIKE '%RESPIRATORY%' OR rt LIKE '%ENDOTRACHEAL%' THEN 'INHALED'
  WHEN rt LIKE '%VAGINAL%' THEN 'VAGINAL'
  WHEN rt LIKE '%INTRAVENOUS%' OR rt LIKE '%INTRAMUSCULAR%' OR rt LIKE '%SUBCUTANEOUS%'
       OR rt LIKE '%INTRA%' OR rt LIKE '%INFILTRATION%' OR rt LIKE '%EPIDURAL%'
       OR rt LIKE '%INTRADERMAL%' OR rt LIKE '%PARENTERAL%' OR rt LIKE '%IMPLANT%' THEN 'INJECTABLE'
  WHEN rt LIKE '%RECTAL%' THEN 'RECTAL'
  WHEN rt LIKE '%TRANSDERMAL%' THEN 'TRANSDERMAL'
  WHEN rt LIKE '%TOPICAL%' OR rt LIKE '%CUTANEOUS%' OR rt LIKE '%PERCUTANEOUS%' OR rt LIKE '%DENTAL%'
       OR rt LIKE '%PERIODONTAL%' OR rt LIKE '%SUBGINGIVAL%' THEN 'TOPICAL'
  WHEN rt LIKE '%INTRAVENOUS%' OR rt LIKE '%INTRAMUSCULAR%' OR rt LIKE '%SUBCUTANEOUS%'
       OR rt LIKE '%INTRA%' OR rt LIKE '%INFILTRATION%' OR rt LIKE '%EPIDURAL%'
       OR rt LIKE '%INTRADERMAL%' OR rt LIKE '%PARENTERAL%' THEN 'INJECTABLE'
  WHEN rt LIKE '%ORAL%' OR rt LIKE '%SUBLINGUAL%' OR rt LIKE '%BUCCAL%' THEN
     CASE WHEN f LIKE '%TABLET%' THEN 'ORAL TABLET'
          WHEN f LIKE '%CAPSULE%' THEN 'ORAL CAPSULE'
          WHEN f LIKE '%SOLUTION%' OR f LIKE '%SUSPENSION%' OR f LIKE '%SYRUP%'
            OR f LIKE '%ELIXIR%' OR f LIKE '%LIQUID%' THEN 'ORAL LIQUID'
          ELSE 'ORAL OTHER' END
  -- route missing: fall back to form, ophthalmic/otic tested first
  WHEN f LIKE '%OPHTH%' THEN 'OPHTHALMIC'
  WHEN f LIKE '%OTIC%' OR f LIKE '%AURICULAR%' THEN 'OTIC'
  WHEN f LIKE '%INJECT%' OR f LIKE '%INFUSION%' THEN 'INJECTABLE'
  WHEN f LIKE '%IMPLANT%' THEN 'INJECTABLE'
  WHEN f LIKE '%SUPPOSITORY%' OR f LIKE '%ENEMA%' THEN 'RECTAL'
  WHEN f LIKE '%SHAMPOO%' OR f LIKE '%CREAM%' OR f LIKE '%OINTMENT%' OR f LIKE '%LOTION%'
       OR f LIKE '%PATCH%' OR f LIKE '%GEL%' THEN 'TOPICAL'
  WHEN f LIKE '%AEROSOL%' OR f LIKE '%INHAL%' OR f LIKE '%SPRAY%' OR f LIKE '%POWDER, METERED%' THEN 'INHALED'
  WHEN f LIKE '%TABLET%' THEN 'ORAL TABLET'
  WHEN f LIKE '%CAPSULE%' THEN 'ORAL CAPSULE'
  WHEN f LIKE '%SOLUTION%' OR f LIKE '%SUSPENSION%' OR f LIKE '%SYRUP%' OR f LIKE '%ELIXIR%'
       OR f LIKE '%LIQUID%' THEN 'ORAL LIQUID'
  ELSE 'OTHER' END""")
con.execute(f"""CREATE OR REPLACE TABLE j AS SELECT n.lab,(n.yr-1991)*4+n.qtr tq,n.rx,n.amt,
 xw.generic||' | '||rbucket(COALESCE(xw.route,''),COALESCE(xw.form,'')) AS mkt,
 xw.generic gen, rbucket(COALESCE(xw.route,''),COALESCE(xw.form,'')) frm, NULLIF(trim(xw.pclass),'') epc
 FROM read_parquet({px!r}) n
 JOIN read_parquet('/tmp/xw_route.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
 JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
 WHERE n.rx IS NOT NULL AND xw.generic<>'' AND pt.ptype='HUMAN PRESCRIPTION DRUG'""")
print("bucket distribution:")
for b,c in con.execute("SELECT frm,COUNT(*) n FROM j GROUP BY 1 ORDER BY n DESC").fetchall():
    print(f"   {b:<16}{c:>10,}")
con.execute("CREATE OR REPLACE TABLE lmq AS SELECT lab,mkt,tq,SUM(rx) rx,SUM(amt) amt FROM j GROUP BY 1,2,3")
con.execute("CREATE OR REPLACE TABLE molq AS SELECT mkt mol,tq,SUM(rx) rx,SUM(amt) amt FROM lmq GROUP BY 1,2")
print("\nmarkets:",con.execute("SELECT COUNT(DISTINCT mol) FROM molq").fetchone()[0])
print("labeler-market-quarters:",con.execute("SELECT COUNT(*) FROM lmq").fetchone()[0])
for t,p in [("lmq","/tmp/lmq_rt.parquet"),("molq","/tmp/molq_rt.parquet")]:
    con.execute(f"COPY (SELECT * FROM {t}) TO '{p}' (FORMAT PARQUET)")
con.execute("COPY (SELECT DISTINCT mkt mol,gen,frm,epc FROM j) TO '/tmp/meta_rt.parquet' (FORMAT PARQUET)")
print("wrote route-aware panels")

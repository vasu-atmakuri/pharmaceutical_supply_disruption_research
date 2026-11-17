import duckdb, glob, os, numpy as np, json
W=os.path.expanduser("~/work/parts3"); parts=sorted(glob.glob(W+"/*.parquet"))
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")
con.execute(f"""CREATE OR REPLACE TABLE j AS SELECT n.lab,(n.yr-1991)*4+n.qtr tq,n.rx,
 xw.generic mol, NULLIF(trim(xw.epc),'') epc FROM read_parquet({parts!r}) n
 LEFT JOIN read_parquet('/tmp/xw.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
 LEFT JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
 WHERE n.rx IS NOT NULL AND xw.generic IS NOT NULL AND pt.ptype='HUMAN PRESCRIPTION DRUG'""")
print("years:",con.execute("SELECT MIN(1991+(tq-1)/4),MAX(1991+(tq-1)/4) FROM j").fetchone(),flush=True)
con.execute("CREATE OR REPLACE TABLE lmq AS SELECT lab,mol,tq,SUM(rx) rx FROM j GROUP BY 1,2,3")
con.execute("CREATE OR REPLACE TABLE molq AS SELECT mol,tq,SUM(rx) rx FROM lmq GROUP BY 1,2")
print("labeler-molecule-quarters:",con.execute("SELECT COUNT(*) FROM lmq").fetchone()[0],flush=True)
print("molecules:",con.execute("SELECT COUNT(DISTINCT mol) FROM molq").fetchone()[0],flush=True)
# TREATMENT: a labeler-molecule pair with sustained supply that stops, and the labeler's share was high
con.execute("""CREATE OR REPLACE TABLE sl AS
WITH s AS (SELECT lab,mol,tq,
   AVG(rx) OVER (PARTITION BY lab,mol ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
   AVG(rx) OVER (PARTITION BY lab,mol ORDER BY tq ROWS BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4
 FROM lmq),
 e AS (SELECT lab,mol,tq FROM s WHERE pre4>=200 AND post4<0.05*pre4),
 f AS (SELECT lab,mol,MIN(tq) t FROM e GROUP BY 1,2),
 fr AS (SELECT f.lab,f.mol,f.t,SUM(l.rx) firm_rx FROM f JOIN lmq l ON l.lab=f.lab AND l.mol=f.mol
        AND l.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2,3),
 tt AS (SELECT f.mol,f.t,SUM(m.rx) mol_rx FROM f JOIN molq m ON m.mol=f.mol AND m.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2)
SELECT fr.lab,fr.mol,fr.t,fr.firm_rx,tt.mol_rx,fr.firm_rx/tt.mol_rx shr
FROM fr JOIN tt ON tt.mol=fr.mol AND tt.t=fr.t WHERE tt.mol_rx>0""")
n=con.execute("SELECT COUNT(*) FROM sl").fetchone()[0]
print(f"\nSUPPLIER-LOSS EVENTS: {n:,}",flush=True)
for lo,hi,nm in [(0,.35,"minor <35%"),(.35,.65,"35-65%"),(.65,.95,"65-95%"),(.95,1.01,"sole >=95%")]:
    c=con.execute(f"SELECT COUNT(*),COUNT(DISTINCT mol) FROM sl WHERE shr>={lo} AND shr<{hi}").fetchone()
    print(f"  {nm:<12} events={c[0]:>6,}  distinct molecules={c[1]:>5,}",flush=True)
con.execute("COPY (SELECT * FROM sl) TO '/tmp/sl.parquet' (FORMAT PARQUET)")
con.execute("COPY (SELECT * FROM molq) TO '/tmp/molq.parquet' (FORMAT PARQUET)")
print("\nwrote /tmp/sl.parquet and /tmp/molq.parquet",flush=True)

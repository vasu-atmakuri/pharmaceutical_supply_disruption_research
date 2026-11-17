import duckdb, glob, os, numpy as np
W=os.path.expanduser("~/work/parts3"); parts=sorted(glob.glob(W+"/*.parquet"))
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute(f"CREATE VIEW n AS SELECT * FROM read_parquet({parts!r})")
con.execute("""CREATE OR REPLACE TABLE lq AS SELECT lab,(yr-2014)*4+qtr tq,
 SUM(rx) rx, COUNT(DISTINCT pcode) nprod, COUNT(DISTINCT product) nmol
 FROM n WHERE yr BETWEEN 2014 AND 2025 GROUP BY 1,2""")
print("labeler-quarters:", con.execute("SELECT COUNT(*) FROM lq").fetchone()[0], flush=True)
print("distinct labelers:", con.execute("SELECT COUNT(DISTINCT lab) FROM lq").fetchone()[0], flush=True)
# abrupt exit: labeler with >=X rx/qtr sustained, then ~0 for >=4 consecutive quarters
con.execute("""CREATE OR REPLACE TABLE ex AS
WITH s AS (SELECT lab,tq,rx,nprod,
   AVG(rx) OVER (PARTITION BY lab ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
   AVG(rx) OVER (PARTITION BY lab ORDER BY tq ROWS BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4,
   MAX(nprod) OVER (PARTITION BY lab ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) preprod
 FROM lq)
SELECT lab,tq,pre4,post4,preprod FROM s
WHERE pre4 IS NOT NULL AND post4 IS NOT NULL AND pre4>=20000 AND post4 < 0.10*pre4 AND tq BETWEEN 9 AND 44""")
print("\n=== ABRUPT LABELER EXITS DETECTED (pre >=20k rx/qtr, post <10% of pre, sustained 4q) ===",flush=True)
r=con.execute("""SELECT COUNT(*) FROM (SELECT lab, MIN(tq) t FROM ex GROUP BY 1)""").fetchone()[0]
print(f"distinct exiting labelers: {r}",flush=True)
print("\n  labeler  exit_qtr   pre_rx/qtr   post_rx/qtr   products_before",flush=True)
for row in con.execute("""WITH f AS (SELECT lab,MIN(tq) t FROM ex GROUP BY 1)
 SELECT f.lab, f.t, e.pre4, e.post4, e.preprod FROM f JOIN ex e ON e.lab=f.lab AND e.tq=f.t
 ORDER BY e.pre4 DESC LIMIT 25""").fetchall():
    yq=f"{2014+(row[1]-1)//4}Q{(row[1]-1)%4+1}"
    print(f"   {row[0]}    {yq}    {row[2]:>10,.0f}   {row[3]:>10,.0f}   {row[4]:>8}",flush=True)
print("\n=== scale of the treated set ===",flush=True)
agg=con.execute("""WITH f AS (SELECT lab,MIN(tq) t FROM ex GROUP BY 1)
 SELECT COUNT(*), SUM(e.preprod), AVG(e.preprod), SUM(e.pre4)
 FROM f JOIN ex e ON e.lab=f.lab AND e.tq=f.t""").fetchone()
print(f"  exits={agg[0]}  total products affected={agg[1]:,}  mean products/exit={agg[2]:.1f}"
      f"  total pre-exit rx/qtr={agg[3]:,.0f}",flush=True)
print("\n=== exits per year ===",flush=True)
for row in con.execute("""WITH f AS (SELECT lab,MIN(tq) t FROM ex GROUP BY 1)
 SELECT 2014+(t-1)/4, COUNT(*) FROM f GROUP BY 1 ORDER BY 1""").fetchall():
    print(f"   {int(row[0])}: {row[1]} exits",flush=True)

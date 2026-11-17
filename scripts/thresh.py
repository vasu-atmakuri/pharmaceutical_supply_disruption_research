import duckdb, glob, os, numpy as np
W=os.path.expanduser("~/work/parts3"); parts=sorted(glob.glob(W+"/*.parquet"))
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute(f"CREATE VIEW n AS SELECT * FROM read_parquet({parts!r})")
con.execute("CREATE VIEW xw AS SELECT * FROM read_parquet('/tmp/xw.parquet')")
con.execute("""CREATE OR REPLACE TABLE j AS SELECT n.lab,n.pcode,(n.yr-2014)*4+n.qtr tq,n.rx,
  xw.generic mol, NULLIF(trim(xw.epc),'') epc FROM n
  LEFT JOIN xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
  WHERE n.yr BETWEEN 2014 AND 2025 AND n.rx IS NOT NULL""")
con.execute("CREATE OR REPLACE TABLE lqall AS SELECT lab,tq,SUM(rx) rx FROM j GROUP BY 1,2")
con.execute("CREATE OR REPLACE TABLE lm AS SELECT lab,mol,tq,SUM(rx) rx FROM j WHERE mol IS NOT NULL GROUP BY 1,2,3")
con.execute("CREATE OR REPLACE TABLE molq AS SELECT mol,tq,SUM(rx) rx FROM lm GROUP BY 1,2")
MQ={}
for m,t,v in con.execute("SELECT mol,tq,rx FROM molq").fetchall(): MQ.setdefault(m,{})[t]=v
for TH in (20000,10000,5000,2000):
    con.execute(f"""CREATE OR REPLACE TABLE ev AS WITH s AS (SELECT lab,tq,
      AVG(rx) OVER (PARTITION BY lab ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
      AVG(rx) OVER (PARTITION BY lab ORDER BY tq ROWS BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4 FROM lqall)
      SELECT lab,MIN(tq) t FROM s WHERE pre4>={TH} AND post4<0.10*pre4 AND tq BETWEEN 9 AND 44 GROUP BY 1""")
    nex=con.execute("SELECT COUNT(*) FROM ev").fetchone()[0]
    con.execute("""CREATE OR REPLACE TABLE trt AS
    WITH f AS (SELECT e.lab,e.t,l.mol,SUM(l.rx) firm_rx FROM ev e JOIN lm l ON l.lab=e.lab AND l.tq BETWEEN e.t-4 AND e.t-1 GROUP BY 1,2,3),
     tt AS (SELECT e.lab,e.t,m.mol,SUM(m.rx) mol_rx FROM ev e JOIN molq m ON m.tq BETWEEN e.t-4 AND e.t-1 GROUP BY 1,2,3),
     s AS (SELECT f.mol,f.t,f.firm_rx/tt.mol_rx shr FROM f JOIN tt USING(lab,t,mol) WHERE f.firm_rx>200 AND tt.mol_rx>0),
     g AS (SELECT mol,MIN(t) t FROM s GROUP BY 1)
    SELECT g.mol,g.t,MAX(s.shr) shr FROM g JOIN s ON s.mol=g.mol AND s.t=g.t GROUP BY 1,2""")
    T=con.execute("SELECT mol,t,shr FROM trt").fetchall()
    sole=[(m,t) for m,t,s in T if s>=0.95]
    def eff(sel,k):
        v=[np.log1p(MQ[m][t+k])-np.log1p(MQ[m][t-1]) for m,t in sel
           if m in MQ and MQ[m].get(t+k) and MQ[m].get(t-1)]
        return (np.mean(v) if v else np.nan, len(v))
    e4=eff(sole,4); e8=eff(sole,8)
    print(f"threshold {TH:>6} rx/qtr: exits={nex:>3}  treated_mol={len(T):>4}  sole-supplier={len(sole):>3}"
          f"   effect t+4={e4[0]:+.3f}(n={e4[1]})  t+8={e8[0]:+.3f}(n={e8[1]})",flush=True)

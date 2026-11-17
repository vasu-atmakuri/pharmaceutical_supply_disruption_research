import duckdb, glob, os, numpy as np, json
W=os.path.expanduser("~/work/parts3"); parts=sorted(glob.glob(W+"/*.parquet"))
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute(f"CREATE VIEW n AS SELECT * FROM read_parquet({parts!r})")
con.execute("CREATE VIEW xw AS SELECT * FROM read_parquet('/tmp/xw.parquet')")
con.execute("""CREATE OR REPLACE TABLE j AS SELECT n.lab,n.pcode,(n.yr-2014)*4+n.qtr tq,n.rx,
 xw.generic mol, NULLIF(trim(xw.epc),'') epc FROM n LEFT JOIN xw
 ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
 WHERE n.yr BETWEEN 2014 AND 2025 AND n.rx IS NOT NULL""")
con.execute("CREATE OR REPLACE TABLE lqall AS SELECT lab,tq,SUM(rx) rx FROM j GROUP BY 1,2")
con.execute("""CREATE OR REPLACE TABLE ev AS WITH s AS (SELECT lab,tq,
 AVG(rx) OVER (PARTITION BY lab ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
 AVG(rx) OVER (PARTITION BY lab ORDER BY tq ROWS BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4 FROM lqall)
 SELECT lab,MIN(tq) t FROM s WHERE pre4>=2000 AND post4<0.10*pre4 AND tq BETWEEN 9 AND 44 GROUP BY 1""")
con.execute("CREATE OR REPLACE TABLE lm AS SELECT lab,mol,tq,SUM(rx) rx FROM j WHERE mol IS NOT NULL GROUP BY 1,2,3")
con.execute("CREATE OR REPLACE TABLE molq AS SELECT mol,tq,SUM(rx) rx FROM lm GROUP BY 1,2")
con.execute("""CREATE OR REPLACE TABLE trt AS
WITH f AS (SELECT e.lab,e.t,l.mol,SUM(l.rx) fr FROM ev e JOIN lm l ON l.lab=e.lab AND l.tq BETWEEN e.t-4 AND e.t-1 GROUP BY 1,2,3),
 tt AS (SELECT e.lab,e.t,m.mol,SUM(m.rx) mr FROM ev e JOIN molq m ON m.tq BETWEEN e.t-4 AND e.t-1 GROUP BY 1,2,3),
 s AS (SELECT f.mol,f.t,f.fr/tt.mr shr FROM f JOIN tt USING(lab,t,mol) WHERE f.fr>200 AND tt.mr>0),
 g AS (SELECT mol,MIN(t) t FROM s GROUP BY 1)
SELECT g.mol,g.t,MAX(s.shr) shr FROM g JOIN s ON s.mol=g.mol AND s.t=g.t GROUP BY 1,2""")
MQ={}
for m,t,v in con.execute("SELECT mol,tq,rx FROM molq").fetchall(): MQ.setdefault(m,{})[t]=v
T=con.execute("SELECT mol,t,shr FROM trt").fetchall()
tre={m for m,_,_ in T}
ctl=[m for m in MQ if m not in tre and len([t for t in MQ[m] if MQ[m][t] and MQ[m][t]>0])>=40
     and np.mean([v for v in MQ[m].values() if v])>=400]
print(f"exits={con.execute('SELECT COUNT(*) FROM ev').fetchone()[0]} treated_mol={len(T)} controls={len(ctl)}",flush=True)
rng=np.random.default_rng(101); td=[t for _,t,_ in T]
def ch(sel,getT,lo=-6,hi=6):
    o=[]
    for m in sel:
        t=getT(m); s=MQ.get(m,{})
        pre=[s.get(t+k) for k in range(lo,0)]; post=[s.get(t+k) for k in range(1,hi+1)]
        if any(v is None or v<=0 for v in pre+post): continue
        o.append(np.mean(np.log(post))-np.mean(np.log(pre)))
    return np.array(o)
res={}
for lo,hi,nm in [(0,.35,"minor_0_35"),(.35,.95,"mid_35_95"),(.95,1.01,"sole_95_100"),(0,1.01,"all")]:
    sel=[m for m,_,s in T if lo<=s<hi]; tt={m:t for m,t,s in T if lo<=s<hi}
    tv=ch(sel,lambda m:tt[m]); cv=ch(ctl,lambda m:int(rng.choice(td)))
    d=tv.mean()-cv.mean()
    ph=[]
    for _ in range(600):
        c=ch(list(rng.choice(ctl,size=min(len(tv)*3,len(ctl)),replace=False)),lambda m:int(rng.choice(td)))
        if len(c)>5: ph.append(c.mean()-cv.mean())
    ph=np.array(ph); p=(np.sum(np.abs(ph)>=abs(d))+1)/(len(ph)+1)
    res[nm]=dict(n_treated=int(len(tv)),mean_treated=float(tv.mean()),mean_control=float(cv.mean()),
                 did=float(d),placebo_sd=float(ph.std(ddof=1)),perm_p=float(p),
                 pct_change=float(100*(np.exp(d)-1)))
    print(f"  {nm:>12}  n={len(tv):>3}  DiD={d:+.4f} ({100*(np.exp(d)-1):+.1f}%)  SD={ph.std(ddof=1):.4f}  p={p:.4f}",flush=True)
json.dump(res,open(os.path.expanduser("~/mnt/Research/firm_exit_main_results.json"),'w'),indent=2)
print("\nwrote Research/firm_exit_main_results.json",flush=True)

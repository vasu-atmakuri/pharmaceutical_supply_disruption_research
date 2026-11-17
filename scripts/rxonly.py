import duckdb, glob, os, numpy as np, json
W=os.path.expanduser("~/work/parts3"); parts=sorted(glob.glob(W+"/*.parquet"))
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute(f"""CREATE OR REPLACE TABLE j AS SELECT n.lab,n.pcode,(n.yr-2014)*4+n.qtr tq,n.rx,n.amt,
 xw.generic mol, NULLIF(trim(xw.epc),'') epc, pt.ptype FROM read_parquet({parts!r}) n
 LEFT JOIN read_parquet('/tmp/xw.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
 LEFT JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
 WHERE n.yr BETWEEN 2014 AND 2025 AND n.rx IS NOT NULL""")
con.execute("CREATE OR REPLACE TABLE lqall AS SELECT lab,tq,SUM(rx) rx FROM j GROUP BY 1,2")
con.execute("""CREATE OR REPLACE TABLE ev AS WITH s AS (SELECT lab,tq,
 AVG(rx) OVER (PARTITION BY lab ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
 AVG(rx) OVER (PARTITION BY lab ORDER BY tq ROWS BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4 FROM lqall)
 SELECT lab,MIN(tq) t FROM s WHERE pre4>=2000 AND post4<0.10*pre4 AND tq BETWEEN 9 AND 44 GROUP BY 1""")
# PRESCRIPTION-ONLY molecule panel
con.execute("""CREATE OR REPLACE TABLE lm AS SELECT lab,mol,tq,SUM(rx) rx,SUM(amt) amt FROM j
 WHERE mol IS NOT NULL AND ptype='HUMAN PRESCRIPTION DRUG' GROUP BY 1,2,3""")
con.execute("CREATE OR REPLACE TABLE molq AS SELECT mol,tq,SUM(rx) rx,SUM(amt) amt FROM lm GROUP BY 1,2")
con.execute("""CREATE OR REPLACE TABLE trt AS
WITH f AS (SELECT e.lab,e.t,l.mol,SUM(l.rx) fr FROM ev e JOIN lm l ON l.lab=e.lab AND l.tq BETWEEN e.t-4 AND e.t-1 GROUP BY 1,2,3),
 tt AS (SELECT e.lab,e.t,m.mol,SUM(m.rx) mr FROM ev e JOIN molq m ON m.tq BETWEEN e.t-4 AND e.t-1 GROUP BY 1,2,3),
 s AS (SELECT f.mol,f.t,f.fr/tt.mr shr FROM f JOIN tt USING(lab,t,mol) WHERE f.fr>200 AND tt.mr>0),
 g AS (SELECT mol,MIN(t) t FROM s GROUP BY 1)
SELECT g.mol,g.t,MAX(s.shr) shr FROM g JOIN s ON s.mol=g.mol AND s.t=g.t GROUP BY 1,2""")
MQ={};MA={}
for m,t,v,a in con.execute("SELECT mol,tq,rx,amt FROM molq").fetchall(): MQ.setdefault(m,{})[t]=v; MA.setdefault(m,{})[t]=a
T=con.execute("SELECT mol,t,shr FROM trt").fetchall(); TT={m:(t,s) for m,t,s in T}
tre=set(TT); ctl=[m for m in MQ if m not in tre and len([t for t in MQ[m] if MQ[m][t] and MQ[m][t]>0])>=40
  and np.mean([v for v in MQ[m].values() if v])>=400]
print(f"PRESCRIPTION-ONLY: exits={con.execute('SELECT COUNT(*) FROM ev').fetchone()[0]} treated={len(T)} sole={sum(1 for _,_,s in T if s>=.95)} controls={len(ctl)}",flush=True)
rng=np.random.default_rng(77); td=[t for _,t,_ in T]
def ch(sel,getT,P=MQ,lo=-6,hi=6):
    o=[]
    for m in sel:
        t=getT(m); s=P.get(m,{})
        pre=[s.get(t+k) for k in range(lo,0)]; post=[s.get(t+k) for k in range(1,hi+1)]
        if any(v is None or v<=0 for v in pre+post): continue
        o.append(np.mean(np.log(post))-np.mean(np.log(pre)))
    return np.array(o)
out={}
print("\n  band              n     DiD      change    perm p",flush=True)
for lo,hi,nm in [(0,.35,"minor 0-35%"),(.35,.95,"mid 35-95%"),(.95,1.01,"sole 95-100%"),(0,1.01,"all treated")]:
    sel=[m for m,_,s in T if lo<=s<hi]
    tv=ch(sel,lambda m:TT[m][0]); cv=ch(ctl,lambda m:int(rng.choice(td)))
    d=tv.mean()-cv.mean(); ph=[]
    for _ in range(600):
        c=ch(list(rng.choice(ctl,size=min(max(len(tv)*3,30),len(ctl)),replace=False)),lambda m:int(rng.choice(td)))
        if len(c)>5: ph.append(c.mean()-cv.mean())
    ph=np.array(ph); p=(np.sum(np.abs(ph)>=abs(d))+1)/(len(ph)+1)
    out[nm]=dict(n=int(len(tv)),did=float(d),pct=float(100*(np.exp(d)-1)),p=float(p),sd=float(ph.std(ddof=1)))
    print(f"  {nm:<16}{len(tv):>4}  {d:+.4f}  {100*(np.exp(d)-1):>+7.1f}%   {p:.4f}",flush=True)
print("\n=== event-time, prescription-only, sole band ===",flush=True)
sole=[m for m in TT if TT[m][1]>=0.95]
for k in range(-6,9):
    v=[np.log(MQ[m][TT[m][0]+k])-np.log(MQ[m][TT[m][0]-1]) for m in sole
       if MQ.get(m,{}).get(TT[m][0]+k,0)>0 and MQ.get(m,{}).get(TT[m][0]-1,0)>0]
    print(f"   t{k:+d}: {np.mean(v):+.3f} (n={len(v)})",flush=True)
json.dump(out,open(os.path.expanduser("~/mnt/Research/firm_exit_results_rx_only.json"),'w'),indent=2)
print("\nwrote Research/firm_exit_results_rx_only.json",flush=True)

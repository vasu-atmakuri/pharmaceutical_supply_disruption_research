import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
# approval-level market panel
con.execute("CREATE OR REPLACE TABLE aq AS SELECT mkt,appid,tq,SUM(rx) rx FROM read_parquet('/tmp/pq_app.parquet') GROUP BY 1,2,3")
con.execute("CREATE OR REPLACE TABLE mq AS SELECT mkt mol,tq,SUM(rx) rx FROM aq GROUP BY 1,2")
# detect approval-level supplier loss, same rule
con.execute("""CREATE OR REPLACE TABLE ev AS
WITH s AS (SELECT appid,mkt,tq,
   AVG(rx) OVER (PARTITION BY appid,mkt ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
   AVG(rx) OVER (PARTITION BY appid,mkt ORDER BY tq ROWS BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4 FROM aq),
 e AS (SELECT appid,mkt,tq FROM s WHERE pre4>=200 AND post4<0.05*pre4),
 f AS (SELECT appid,mkt,MIN(tq) t FROM e GROUP BY 1,2),
 fr AS (SELECT f.appid,f.mkt,f.t,SUM(l.rx) a_rx FROM f JOIN aq l ON l.appid=f.appid AND l.mkt=f.mkt
        AND l.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2,3),
 tt AS (SELECT f.mkt,f.t,SUM(m.rx) m_rx FROM f JOIN mq m ON m.mol=f.mkt AND m.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2)
SELECT fr.appid,fr.mkt mol,fr.t,fr.a_rx/NULLIF(tt.m_rx,0) shr
FROM fr JOIN tt ON tt.mkt=fr.mkt AND tt.t=fr.t WHERE tt.m_rx>0""")
print("approval-level supplier-loss events:",con.execute("SELECT COUNT(*) FROM ev").fetchone()[0],flush=True)
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM mq").fetchall(): MQ.setdefault(m,{})[t]=r
AQ={}
for m,a,t,r in con.execute("SELECT mkt,appid,tq,rx FROM aq").fetchall(): AQ.setdefault((m,a),{})[t]=r
SA={}
for m,a,t in con.execute("SELECT mkt,appid,tq FROM aq WHERE rx>0").fetchall(): SA.setdefault((m,t),set()).add(a)
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SL=con.execute("SELECT mol,appid,t,shr FROM ev").fetchall()
first={}
for m,a,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,a)
inwin={m:v for m,v in first.items() if LO<=v[0]<=HI}
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def post(m,t): return float(np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)]))
COH=[m for m,(t,s,a) in inwin.items() if basec(m,t) is not None]
OBS=[m for m in COH if any(MQ[m].get(inwin[m][0]+k) is not None for k in range(1,7))]
print(f"cohort {len(COH)}   with post obs {len(OBS)}   no post {len(COH)-len(OBS)}",flush=True)
def wil(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
def R(m,t,a):
    db=np.mean([AQ.get((m,a),{}).get(t+k) or 0.0 for k in range(B0,B1)])
    ob=np.mean([(MQ[m][t+k] or 0.0)-(AQ.get((m,a),{}).get(t+k) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQ[m].get(t+k) or 0.0)-(AQ.get((m,a),{}).get(t+k) or 0.0) for k in range(1,7)])
    return None if db<=0 else (op-ob)/db
print("\n=== APPROVAL-LEVEL REPLICATION OF THE MAIN RESULT ===",flush=True)
print(f"  {'departing approval share':<26}{'n':>4}{'below2%':>10}{'rate':>8}{'95% CI':>18}{'median R':>11}",flush=True)
rng=np.random.default_rng(77); OUT={}
for lo,hi,nm in [(0,.35,"under 35%"),(.35,.65,"35 to 65%"),(.65,.95,"65 to 95%"),(.95,1.01,"95% or above")]:
    sel=[m for m in OBS if lo<=inwin[m][1]<hi]
    if not sel: continue
    k=sum(1 for m in sel if post(m,inwin[m][0])<=0.02*basec(m,inwin[m][0]))
    v=[R(m,inwin[m][0],inwin[m][2]) for m in sel]; v=[x for x in v if x is not None]
    c=wil(k,len(sel))
    OUT[nm]=dict(n=len(sel),k=k,rate=k/len(sel),ci=list(c),medR=float(np.median(v)) if v else None)
    print(f"  {nm:<26}{len(sel):>4}{k:>10}{k/len(sel):>8.1%}   [{c[0]:>5.1%},{c[1]:>6.1%}]"
          f"{np.median(v) if v else float('nan'):>11.2f}",flush=True)
# bootstrap CI on sole median and on the contrast
a=[R(m,inwin[m][0],inwin[m][2]) for m in OBS if inwin[m][1]<.35]; a=[x for x in a if x is not None]
b=[R(m,inwin[m][0],inwin[m][2]) for m in OBS if inwin[m][1]>=.95]; b=[x for x in b if x is not None]
d=[np.median(rng.choice(a,len(a),True))-np.median(rng.choice(b,len(b),True)) for _ in range(20000)]
print(f"\n  difference in medians (minority minus sole): {np.median(a)-np.median(b):.2f}  "
      f"95% CI [{np.percentile(d,2.5):.2f}, {np.percentile(d,97.5):.2f}]",flush=True)
print(f"  sole-band event-level R: {sum(1 for x in b if abs(x)<1e-9)} of {len(b)} exactly zero",flush=True)
print("\n=== HOW OFTEN DOES THE APPROVAL DEFINITION DISAGREE WITH THE LABELER DEFINITION? ===",flush=True)
LB={}
for m,l,t,s in con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall():
    if m not in LB or t<LB[m][0]: LB[m]=(t,s,l)
lab_sole={m for m,(t,s,l) in LB.items() if s>=.95 and LO<=t<=HI}
app_sole={m for m,(t,s,a) in inwin.items() if s>=.95}
print(f"  sole by labeler: {len(lab_sole)}   sole by approval: {len(app_sole)}   in both: {len(lab_sole&app_sole)}",flush=True)
print(f"  sole by labeler only: {len(lab_sole-app_sole)}   sole by approval only: {len(app_sole-lab_sole)}",flush=True)
json.dump(OUT,open(os.path.expanduser("~/mnt/Research/RESULTS_approval_level.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_approval_level.json",flush=True)

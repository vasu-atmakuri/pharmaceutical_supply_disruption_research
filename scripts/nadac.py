import duckdb, glob, os, numpy as np, json
f=sorted(glob.glob(os.path.expanduser("~/mnt/Research/aux/nadac_*.csv")))
print("files:",[os.path.basename(x) for x in f],flush=True)
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute("SET preserve_insertion_order=false")
con.execute(f"""CREATE OR REPLACE TABLE nd AS
 SELECT lpad(CAST("NDC" AS VARCHAR),11,'0') ndc11,
   TRY_CAST("NADAC_Per_Unit" AS DOUBLE) price,
   TRY_CAST(strptime("Effective_Date",'%m/%d/%Y') AS DATE) eff,
   "Classification_for_Rate_Setting" cls, "OTC" otc
 FROM read_csv({f!r}, header=true, all_varchar=true, union_by_name=true, ignore_errors=true)
 WHERE "NADAC_Per_Unit" IS NOT NULL""")
print("rows:",con.execute("SELECT COUNT(*) FROM nd").fetchone()[0],flush=True)
con.execute("""CREATE OR REPLACE TABLE npq AS
 SELECT substr(ndc11,1,5) lab, substr(ndc11,6,4) pcode,
  (year(eff)-1991)*4+quarter(eff) tq, median(price) price
 FROM nd WHERE eff IS NOT NULL AND price>0 GROUP BY 1,2,3""")
r=con.execute("SELECT COUNT(*),MIN(tq),MAX(tq) FROM npq").fetchone()
print(f"labeler-product-quarters: {r[0]:,}  tq {r[1]}..{r[2]} = {1991+(r[1]-1)//4}Q{(r[1]-1)%4+1}..{1991+(r[2]-1)//4}Q{(r[2]-1)%4+1}",flush=True)
yrs=con.execute("SELECT DISTINCT 1991+(tq-1)/4 y FROM npq ORDER BY 1").fetchall()
print("years covered:",[int(x[0]) for x in yrs],flush=True)
# market-quarter median price, volume-free (median across products in the market)
con.execute("""CREATE OR REPLACE TABLE mp AS
 SELECT xw.generic||' | '||CASE
   WHEN xw.form IS NULL THEN 'UNK'
   WHEN xw.form LIKE '%INJECT%' OR xw.form LIKE '%INFUSION%' THEN 'INJECTABLE'
   WHEN xw.form LIKE '%TABLET%' THEN 'TABLET' WHEN xw.form LIKE '%CAPSULE%' THEN 'CAPSULE'
   WHEN xw.form LIKE '%SOLUTION%' OR xw.form LIKE '%SUSPENSION%' OR xw.form LIKE '%SYRUP%' OR xw.form LIKE '%ELIXIR%' OR xw.form LIKE '%LIQUID%' THEN 'ORAL LIQUID'
   WHEN xw.form LIKE '%CREAM%' OR xw.form LIKE '%OINTMENT%' OR xw.form LIKE '%GEL%' OR xw.form LIKE '%LOTION%' OR xw.form LIKE '%PATCH%' OR xw.form LIKE '%FILM%' THEN 'TOPICAL'
   WHEN xw.form LIKE '%AEROSOL%' OR xw.form LIKE '%INHAL%' OR xw.form LIKE '%POWDER, METERED%' OR xw.form LIKE '%SPRAY%' THEN 'INHALED/SPRAY'
   WHEN xw.form LIKE '%SUPPOSITORY%' OR xw.form LIKE '%ENEMA%' THEN 'RECTAL'
   WHEN xw.form LIKE '%OPHTH%' OR xw.form LIKE '%DROP%' THEN 'DROPS' ELSE 'OTHER' END mol,
  n.tq, median(n.price) price, COUNT(*) nprod
 FROM npq n JOIN read_parquet('/tmp/xw.parquet') xw ON xw.lab=n.lab AND xw.pcode=n.pcode
 WHERE xw.generic<>'' GROUP BY 1,2""")
print("market-quarters with a NADAC price:",con.execute("SELECT COUNT(*) FROM mp").fetchone()[0],flush=True)
P={}
for m,t,p,_ in con.execute("SELECT mol,tq,price,nprod FROM mp").fetchall(): P.setdefault(m,{})[t]=p
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
S={}
for m,l,t in con.execute("SELECT mkt,lab,tq FROM read_parquet('/tmp/lmq_nat.parquet') WHERE rx>0").fetchall(): S.setdefault((m,t),set()).add(l)
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
ever={m for m,_,_,_ in SL}
inwin={m:v for m,v in first.items() if LO<=v[0]<=HI}
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
COH=[m for m,(t,s,l) in inwin.items() if basec(m,t) is not None]
def pr(m,t,w):
    v=[P.get(m,{}).get(t+k) for k in w]; v=[x for x in v if x and x>0]
    return float(np.mean(v)) if v else None
print("\n=== ACQUISITION COST (NADAC) AROUND SUPPLIER LOSS ===",flush=True)
print("   median NADAC per unit, market level; log change baseline t-6..t-3 vs t+1..t+6\n",flush=True)
print(f"  {'band':<16}{'n':>4}{'treated':>12}{'matched ctl':>14}{'difference':>13}",flush=True)
pool=[m for m in MQ if m not in ever]
rng=np.random.default_rng(5); OUT={}
for lo,hi,nm in [(0,.35,"under 35%"),(.35,.95,"35 to 95%"),(.95,1.01,"95% or above")]:
    tv=[];cv=[]
    for m in [x for x in COH if lo<=inwin[x][1]<hi]:
        t=inwin[m][0]
        a=pr(m,t,range(B0,B1)); b=pr(m,t,range(1,7))
        if not a or not b: continue
        tv.append(np.log(b)-np.log(a))
        nb=len(S.get((m,t-1),set())); vb=basec(m,t)
        cs=[c for c in pool if basec(c,t) and len(S.get((c,t-1),set()))==nb
            and vb/2<=basec(c,t)<=vb*2 and pr(c,t,range(B0,B1)) and pr(c,t,range(1,7))]
        if len(cs)>10: cs=list(rng.choice(cs,10,False))
        for c in cs:
            cv.append(np.log(pr(c,t,range(1,7)))-np.log(pr(c,t,range(B0,B1))))
    if not tv: continue
    tv=np.array(tv); cv=np.array(cv) if cv else np.array([0.0])
    d=100*(np.exp(tv.mean()-cv.mean())-1)
    OUT[nm]=dict(n=len(tv),treated=float(100*(np.exp(tv.mean())-1)),ctl=float(100*(np.exp(cv.mean())-1)),diff=float(d))
    print(f"  {nm:<16}{len(tv):>4}{100*(np.exp(tv.mean())-1):>11.1f}%{100*(np.exp(cv.mean())-1):>13.1f}%{d:>12.1f}%",flush=True)
print("\n=== sole band, event level ===",flush=True)
for m in [x for x in COH if inwin[x][1]>=.95]:
    t=inwin[m][0]; a=pr(m,t,range(B0,B1)); b=pr(m,t,range(1,7))
    if a and b: print(f"  {m[:44]:<46}{a:>9.4f} -> {b:>9.4f}   {100*(b/a-1):>+8.1f}%",flush=True)
json.dump(OUT,open(os.path.expanduser("~/mnt/Research/RESULTS_nadac.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_nadac.json",flush=True)

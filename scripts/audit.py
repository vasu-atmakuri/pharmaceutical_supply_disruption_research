import duckdb, glob, os, numpy as np, json
px=sorted(glob.glob(os.path.expanduser("~/work/partsxx/*.parquet")))
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute("""CREATE OR REPLACE MACRO fbucket(f) AS
 CASE WHEN f IS NULL THEN 'UNK' WHEN f LIKE '%INJECT%' OR f LIKE '%INFUSION%' THEN 'INJECTABLE'
  WHEN f LIKE '%TABLET%' THEN 'TABLET' WHEN f LIKE '%CAPSULE%' THEN 'CAPSULE'
  WHEN f LIKE '%SOLUTION%' OR f LIKE '%SUSPENSION%' OR f LIKE '%SYRUP%' OR f LIKE '%ELIXIR%' OR f LIKE '%LIQUID%' THEN 'ORAL LIQUID'
  WHEN f LIKE '%CREAM%' OR f LIKE '%OINTMENT%' OR f LIKE '%GEL%' OR f LIKE '%LOTION%' OR f LIKE '%PATCH%' OR f LIKE '%FILM%' THEN 'TOPICAL'
  WHEN f LIKE '%AEROSOL%' OR f LIKE '%INHAL%' OR f LIKE '%POWDER, METERED%' OR f LIKE '%SPRAY%' THEN 'INHALED/SPRAY'
  WHEN f LIKE '%SUPPOSITORY%' OR f LIKE '%ENEMA%' THEN 'RECTAL'
  WHEN f LIKE '%OPHTH%' OR f LIKE '%DROP%' THEN 'DROPS' ELSE 'OTHER' END""")
# market-quarter suppression counts
con.execute(f"""CREATE OR REPLACE TABLE msup AS
 SELECT xw.generic||' | '||fbucket(xw.form) mol,(n.yr-1991)*4+n.qtr tq,
   SUM(n.nsupp) nsupp, SUM(n.ncells) ncells, SUM(COALESCE(n.rx,0)) rx
 FROM read_parquet({px!r}) n
 JOIN read_parquet('/tmp/xw.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
 JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
 WHERE xw.generic<>'' AND pt.ptype='HUMAN PRESCRIPTION DRUG' GROUP BY 1,2""")
SUPM={}
for m,t,ns in con.execute("SELECT mol,tq,nsupp FROM msup").fetchall(): SUPM.setdefault(m,{})[t]=ns or 0
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
S={}
for m,l,t in con.execute("SELECT mkt,lab,tq FROM read_parquet('/tmp/lmq_nat.parquet') WHERE rx>0").fetchall(): S.setdefault((m,t),set()).add(l)
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SLall=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
firstall={}
for m,l,t,s in sorted(SLall,key=lambda x:x[2]):
    if m not in firstall: firstall[m]=(t,s,l)
print("=== EVENT FLOW ===",flush=True)
BANDS=[(0,.35,"under 35%"),(.35,.65,"35-65%"),(.65,.95,"65-95%"),(.95,1.01,"sole >=95%")]
def band(s):
    for lo,hi,nm in BANDS:
        if lo<=s<hi: return nm
    return "?"
rows={nm:[0,0,0,0,0] for _,_,nm in BANDS}
for m,(t,s,l) in firstall.items():
    b=band(s); rows[b][0]+=1
    if not (LO<=t<=HI): continue
    rows[b][1]+=1
    pre=[MQ[m].get(t+k) for k in range(B0,B1)]
    if any(v is None or v<=0 for v in pre): continue
    rows[b][2]+=1
    pq=[MQ[m].get(t+k) for k in range(1,7)]
    if all(v is None for v in pq): rows[b][4]+=1; continue
    rows[b][3]+=1
print(f"  {'band':<12}{'detected':>10}{'in window':>11}{'+baseline':>11}{'+post obs':>11}{'dropped: no post':>18}",flush=True)
tot=[0]*5
for _,_,nm in BANDS:
    r=rows[nm]; tot=[a+b for a,b in zip(tot,r)]
    print(f"  {nm:<12}{r[0]:>10}{r[1]:>11}{r[2]:>11}{r[3]:>11}{r[4]:>18}",flush=True)
print(f"  {'TOTAL':<12}{tot[0]:>10}{tot[1]:>11}{tot[2]:>11}{tot[3]:>11}{tot[4]:>18}",flush=True)
first={m:v for m,v in firstall.items() if LO<=v[0]<=HI}
EV=[]
for m,(t,s,l) in first.items():
    pre=[MQ[m].get(t+k) for k in range(B0,B1)]
    if any(v is None or v<=0 for v in pre): continue
    if all(MQ[m].get(t+k) is None for k in range(1,7)): continue
    EV.append(m)
print(f"\n  ANALYSIS COHORT n = {len(EV)}",flush=True)
print("\n=== WHY TABLE 1 (replacement) HAD 86 NOT 87 IN THE MINOR BAND ===",flush=True)
LMQ={}
for m,l,t,r in con.execute("SELECT mkt,lab,tq,rx FROM read_parquet('/tmp/lmq_nat.parquet')").fetchall(): LMQ.setdefault((m,l),{})[t]=r
bad=[]
for m in EV:
    t,s,dl=first[m]
    dep_b=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
    if dep_b<=0: bad.append((m,band(s),dep_b))
print(f"  events with zero observed departing-labeler baseline volume: {len(bad)}",flush=True)
for m,b,v in bad: print(f"    {m[:50]:<52} band={b}",flush=True)
print("  (departing labeler's own baseline quarters are all suppressed; market total is observed)",flush=True)
print("\n=== MARKET-LEVEL SUPPRESSION BOUND, analysis cohort ===",flush=True)
for lo,hi,nm in [(0,.35,"under 35%"),(.95,1.01,"sole >=95%")]:
    sel=[m for m in EV if lo<=first[m][1]<hi]; b=[]
    for m in sel:
        t=first[m][0]
        ns=np.mean([SUPM.get(m,{}).get(t+k,0) for k in range(1,7)])
        base=np.mean([MQ[m][t+k] for k in range(B0,B1)])
        b.append((10*ns, 10*ns/base if base>0 else np.nan))
    A=np.array(b)
    print(f"  {nm:<12} n={len(b):>3}  mean upper bound on hidden post volume: {A[:,0].mean():>7.1f} rx/qtr "
          f"({100*np.nanmean(A[:,1]):.2f}% of baseline)   max {A[:,0].max():.0f} rx",flush=True)
print("\n=== ENTRY ON THE CONSISTENT COHORT (was computed on a looser filter) ===",flush=True)
print(f"  {'band':<14}{'n':>4}{'lab t-1':>9}{'lab t+6':>9}{'any entry':>11}",flush=True)
ENT={}
for lo,hi,nm in [(0,.35,"under 35%"),(.35,.95,"35 to 95%"),(.95,1.01,"95% or above")]:
    r=[]
    for m in [x for x in EV if lo<=first[x][1]<hi]:
        t=first[m][0]
        pre=S.get((m,t-1),set()); new=set()
        for k in range(0,7): new|=(S.get((m,t+k),set())-pre)
        r.append((len(pre),len(S.get((m,t+6),set())),len(new)))
    if not r: continue
    A=np.array(r); ENT[nm]=dict(n=len(r),pre=float(A[:,0].mean()),t6=float(A[:,1].mean()),pct=float((A[:,2]>0).mean()))
    print(f"  {nm:<14}{len(r):>4}{A[:,0].mean():>9.2f}{A[:,1].mean():>9.2f}{100*(A[:,2]>0).mean():>10.0f}%",flush=True)
json.dump(dict(flow={nm:rows[nm] for _,_,nm in BANDS},cohort=len(EV),entry=ENT),
  open(os.path.expanduser("~/mnt/Research/RESULTS_event_flow.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_event_flow.json",flush=True)

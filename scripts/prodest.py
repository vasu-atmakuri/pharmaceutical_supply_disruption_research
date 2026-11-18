import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
con.execute("""CREATE OR REPLACE TABLE pm AS SELECT DISTINCT lab,pcode,est FROM read_parquet('/tmp/prodestab.parquet')
  WHERE op LIKE '%MANUFACTURE%' AND op<>'API MANUFACTURE'""")
PE={}
for l,p,e in con.execute("SELECT lab,pcode,est FROM pm").fetchall(): PE.setdefault((l,p),set()).add(e)
print(f"products with a manufacture site: {len(PE):,}",flush=True)
# product-level dispensing panel (labeler, product, market, quarter)
import glob
px=sorted(glob.glob(os.path.expanduser("~/work/partsxx/*.parquet")))
con.execute("""CREATE OR REPLACE MACRO fb(f) AS CASE WHEN f IS NULL THEN 'UNK'
 WHEN f LIKE '%INJECT%' OR f LIKE '%INFUSION%' THEN 'INJECTABLE' WHEN f LIKE '%TABLET%' THEN 'TABLET'
 WHEN f LIKE '%CAPSULE%' THEN 'CAPSULE'
 WHEN f LIKE '%SOLUTION%' OR f LIKE '%SUSPENSION%' OR f LIKE '%SYRUP%' OR f LIKE '%ELIXIR%' OR f LIKE '%LIQUID%' THEN 'ORAL LIQUID'
 WHEN f LIKE '%CREAM%' OR f LIKE '%OINTMENT%' OR f LIKE '%GEL%' OR f LIKE '%LOTION%' OR f LIKE '%PATCH%' OR f LIKE '%FILM%' THEN 'TOPICAL'
 WHEN f LIKE '%AEROSOL%' OR f LIKE '%INHAL%' OR f LIKE '%POWDER, METERED%' OR f LIKE '%SPRAY%' THEN 'INHALED/SPRAY'
 WHEN f LIKE '%SUPPOSITORY%' OR f LIKE '%ENEMA%' THEN 'RECTAL'
 WHEN f LIKE '%OPHTH%' OR f LIKE '%DROP%' THEN 'DROPS' ELSE 'OTHER' END""")
con.execute(f"""CREATE OR REPLACE TABLE pp AS SELECT xw.generic||' | '||fb(xw.form) mkt,
 lpad(n.lab,5,'0') lab, lpad(n.pcode,4,'0') pcode, (n.yr-1991)*4+n.qtr tq, SUM(n.rx) rx
 FROM read_parquet({px!r}) n
 JOIN read_parquet('/tmp/xw.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
 JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
 WHERE n.rx IS NOT NULL AND xw.generic<>'' AND pt.ptype='HUMAN PRESCRIPTION DRUG' GROUP BY 1,2,3,4""")
PROD={}
for m,l,p,t,r in con.execute("SELECT mkt,lab,pcode,tq,rx FROM pp WHERE rx>0").fetchall():
    PROD.setdefault((m,t),[]).append((l,p,r))
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l.zfill(5))
inwin={m:v for m,v in first.items() if LO<=v[0]<=HI}
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
COH=[m for m,(t,s,l) in inwin.items() if basec(m,t) is not None]
OBS=[m for m in COH if any(MQ[m].get(inwin[m][0]+k) is not None for k in range(1,7))]
def sites_of(m,t,only_lab=None,exclude_lab=None):
    """sites for the products ACTUALLY DISPENSING in market m at quarter t"""
    s=set(); cov_n=0; cov_d=0
    for l,p,r in PROD.get((m,t),[]):
        if only_lab and l!=only_lab: continue
        if exclude_lab and l==exclude_lab: continue
        cov_d+=1
        if (l,p) in PE: s|=PE[(l,p)]; cov_n+=1
    return s,(cov_n,cov_d)
print("\n=== PRODUCT-LEVEL LINKAGE: departing vs remaining products ===",flush=True)
print("   sites are those listed for the specific NDCs dispensing in that market at t-1 / t+6\n",flush=True)
res={}; rows=[]
for b,lo,hi in [("under 35%",0,.35),("35 to 95%",.35,.95),("sole >=95%",.95,1.01)]:
    sel=[m for m in COH if lo<=inwin[m][1]<hi]
    tested=0; disj=0; shared=0; covs=[]
    for m in sel:
        t,sh,dl=inwin[m]
        dsite,cd=sites_of(m,t-1,only_lab=dl)
        rsite,cr=sites_of(m,t-1,exclude_lab=dl)
        if cd[1]: covs.append(cd[0]/cd[1])
        if not dsite or not rsite: continue
        tested+=1
        if dsite & rsite: shared+=1
        else: disj+=1
    res[b]=dict(n=len(sel),tested=tested,disjoint=disj,shared=shared,
                coverage=float(np.mean(covs)) if covs else None)
    print(f"  {b:<14} markets={len(sel):>3}  testable={tested:>3}  "
          f"disjoint sites={disj:>3} ({disj/tested:.1%})  shared={shared}" if tested else
          f"  {b:<14} markets={len(sel):>3}  testable=0",flush=True)
print("\n=== REPLACEMENT PRODUCTS: did the volume that replaced the loss come from other sites? ===",flush=True)
print("   compares the departing labeler's sites at t-1 with the sites of products",flush=True)
print("   dispensing at t+6 that were NOT dispensing at t-1 (true replacements)\n",flush=True)
newdisj=0; newshare=0; nomatch=0
detail=[]
for m in [x for x in OBS if inwin[x][1]<.35]:
    t,sh,dl=inwin[m]
    dsite,_=sites_of(m,t-1,only_lab=dl)
    if not dsite: continue
    before={(l,p) for l,p,_ in PROD.get((m,t-1),[])}
    newp=[(l,p) for l,p,_ in PROD.get((m,t+6),[]) if (l,p) not in before]
    nsite=set()
    for l,p in newp:
        if (l,p) in PE: nsite|=PE[(l,p)]
    if not nsite: nomatch+=1; continue
    if dsite & nsite: newshare+=1
    else: newdisj+=1; detail.append(m)
tot=newdisj+newshare
print(f"  minority markets with new products at t+6 and site data: {tot}",flush=True)
if tot:
    print(f"    new products made at sites DISJOINT from the departing labeler's: {newdisj} ({newdisj/tot:.1%})",flush=True)
    print(f"    new products sharing at least one site with the departing labeler: {newshare} ({newshare/tot:.1%})",flush=True)
print(f"  markets with no new-product site data: {nomatch}",flush=True)
print("\n=== SOLE-LABELER MARKETS: how many distinct sites made the departing products? ===",flush=True)
ns=[]
for m in [x for x in COH if inwin[x][1]>=.95]:
    t,sh,dl=inwin[m]
    s,c=sites_of(m,t-1,only_lab=dl)
    if s: ns.append(len(s))
print(f"  n={len(ns)}  mean {np.mean(ns):.2f} sites  median {np.median(ns):.0f}  max {max(ns) if ns else 0}",flush=True)
print(f"  single-site: {sum(1 for x in ns if x==1)} of {len(ns)}",flush=True)
json.dump(dict(bands=res,new_disjoint=newdisj,new_shared=newshare,
               sole_sites_mean=float(np.mean(ns)) if ns else None,
               sole_single_site=int(sum(1 for x in ns if x==1)),sole_n=len(ns)),
  open(os.path.expanduser("~/mnt/Research/RESULTS_prodestab.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_prodestab.json",flush=True)

import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
# labeler code -> set of MANUFACTURE establishments
con.execute("""CREATE OR REPLACE TABLE le AS
 SELECT DISTINCT labcode, est_duns FROM read_parquet('/tmp/estab.parquet')
 WHERE ops LIKE '%MANUFACTURE%' AND ops NOT LIKE '%API MANUFACTURE%'""")
LE={}
for l,e in con.execute("SELECT labcode,est_duns FROM le").fetchall(): LE.setdefault(l,set()).add(e)
print(f"labelers with manufacture-site data: {len(LE)}",flush=True)
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
S={}
for m,l,t in con.execute("SELECT mkt,lab,tq FROM read_parquet('/tmp/lmq_nat.parquet') WHERE rx>0").fetchall():
    S.setdefault((m,t),set()).add(l.zfill(5))
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l.zfill(5))
inwin={m:v for m,v in first.items() if LO<=v[0]<=HI}
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def post(m,t): return float(np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)]))
COH=[m for m,(t,s,l) in inwin.items() if basec(m,t) is not None]
OBS=[m for m in COH if any(MQ[m].get(inwin[m][0]+k) is not None for k in range(1,7))]
print(f"cohort {len(COH)}  with post obs {len(OBS)}",flush=True)
print("\n=== LABELERS vs MANUFACTURING SITES AT t-1, cohort markets ===",flush=True)
print(f"  {'departing share':<18}{'n':>4}{'mean labelers':>15}{'mean sites':>12}{'sites<labelers':>16}{'coverage':>10}",flush=True)
ROW={}
for lo,hi,nm in [(0,.35,"under 35%"),(.35,.95,"35 to 95%"),(.95,1.01,"95% or above")]:
    sel=[m for m in COH if lo<=inwin[m][1]<hi]
    nl=[];ns=[];fewer=0;cov=[]
    for m in sel:
        t=inwin[m][0]; labs=S.get((m,t-1),set())
        if not labs: continue
        known=[l for l in labs if l in LE]
        sites=set()
        for l in known: sites|=LE[l]
        nl.append(len(labs)); ns.append(len(sites) if known else np.nan)
        cov.append(len(known)/len(labs))
        if known and len(sites)<len(known): fewer+=1
    nl=np.array(nl); ns=np.array(ns,dtype=float)
    ROW[nm]=dict(n=len(nl),labelers=float(np.nanmean(nl)),sites=float(np.nanmean(ns)),
                 fewer=int(fewer),coverage=float(np.mean(cov)))
    print(f"  {nm:<18}{len(nl):>4}{np.nanmean(nl):>15.2f}{np.nanmean(ns):>12.2f}{fewer:>16}{np.mean(cov):>9.0%}",flush=True)
print("\n=== DO MULTI-LABELER MARKETS COLLAPSE TO ONE SITE? ===",flush=True)
multi=0; onesite=0; detail=[]
for m in COH:
    t=inwin[m][0]; labs=S.get((m,t-1),set()); known=[l for l in labs if l in LE]
    if len(known)<2: continue
    sites=set()
    for l in known: sites|=LE[l]
    multi+=1
    if len(sites)==1:
        onesite+=1; detail.append((m,len(known)))
print(f"  markets with 2+ labelers having site data: {multi}",flush=True)
print(f"  of those, all labelers map to a single site: {onesite} ({onesite/multi:.1%})" if multi else "  n/a",flush=True)
for m,k in detail[:8]: print(f"    {m[:52]:<54}{k} labelers, 1 site",flush=True)
print("\n=== SOLE-SUPPLIER MARKETS: was the departing labeler the only site? ===",flush=True)
sole=[m for m in OBS if inwin[m][1]>=.95]
have=[m for m in sole if inwin[m][2] in LE]
print(f"  sole-supplier events: {len(sole)}   departing labeler has site data: {len(have)}",flush=True)
ns=[len(LE[inwin[m][2]]) for m in have]
if ns: print(f"  mean manufacturing sites behind the departing labeler: {np.mean(ns):.2f}  (median {np.median(ns):.0f}, max {max(ns)})",flush=True)
k=sum(1 for m in have if post(m,inwin[m][0])<=0.02*basec(m,inwin[m][0]))
print(f"  below 2% among those: {k} of {len(have)} = {k/len(have):.1%}" if have else "",flush=True)
print("\n=== SHARED-SITE CHECK ON THE MINORITY STRATUM ===",flush=True)
print("   (if 'absorbed' markets were really one manufacturer under several labels, replacement",flush=True)
print("    would be an illusion; this tests that directly)",flush=True)
mn=[m for m in OBS if inwin[m][1]<.35]
same=0; diff=0
for m in mn:
    t=inwin[m][0]; dl=inwin[m][2]
    if dl not in LE: continue
    others=[l for l in S.get((m,t-1),set()) if l!=dl and l in LE]
    if not others: continue
    osites=set()
    for l in others: osites|=LE[l]
    if LE[dl]&osites: same+=1
    else: diff+=1
tot=same+diff
print(f"  minority markets testable: {tot}",flush=True)
if tot: print(f"  departing labeler shared a site with a remaining labeler: {same} ({same/tot:.1%})",flush=True)
if tot: print(f"  remaining labelers used entirely different sites:        {diff} ({diff/tot:.1%})",flush=True)
json.dump(dict(bands=ROW,multi=multi,onesite=onesite,shared=same,notshared=diff),
  open(os.path.expanduser("~/mnt/Research/RESULTS_establishments.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_establishments.json",flush=True)

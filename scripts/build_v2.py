import duckdb, re, collections, json, os, numpy as np
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
DROP={'TABLET','TABLETS','CAPSULE','CAPSULES','INJECTION','INJECTABLE','SOLUTION','SOLUTIONS',
      'USP','AND','THE','FOR','WITH','MG','MCG','ML','GM','CV','CII','CIII','CIV','PACKET','PACKETS',
      'KIT','VIAL','VIALS','SYRINGE','BOTTLE','UNIT','UNITS','PER','DOSE','EACH','NDC',
      'OPHTHALMIC','OTIC','TOPICAL','NASAL','RECTAL','VAGINAL','ORAL'}
SALT={'HYDROCHLORIDE','HYDROBROMIDE','SULFATE','TARTRATE','MALEATE','MESYLATE','CITRATE',
      'PHOSPHATE','SUCCINATE','FUMARATE','BESYLATE','DIHYDRATE','MONOHYDRATE','ANHYDROUS',
      'BITARTRATE','NITRATE','OXALATE','PAMOATE','TOSYLATE','HEMIHYDRATE','HYDRATE','HCL'}
SYN={'HCL':'HYDROCHLORIDE','HBR':'HYDROBROMIDE','NA':'SODIUM','K':'POTASSIUM',
     'BICARB':'BICARBONATE','MONOHYD':'MONOHYDRATE','ANHYD':'ANHYDROUS'}
def tok(m):
    ing=(m.split(" | ")+[""])[0]
    w=[SYN.get(x,x) for x in re.split(r'[^A-Z0-9]+',ing.upper()) if x]
    return frozenset(x for x in w if x not in DROP and not re.fullmatch(r'[0-9.]+',x) and len(x)>1)
raw=[r[0] for r in con.execute("SELECT DISTINCT mkt FROM read_parquet('/tmp/lmq_rt.parquet')").fetchall()]
T={m:(tok(m),(m.split(" | ")+[""])[1]) for m in raw}
byform=collections.defaultdict(set)
for m,(t,f) in T.items(): byform[f].add(t)
canon={}
for f,sets in byform.items():
    for s in sets:
        best=s
        for o in sets:
            if o==s or not o: continue
            if o<s and (s-o)<=SALT and len(o)<len(best): best=o
        canon[(f,s)]=best
NK={m:(",".join(sorted(canon[(T[m][1],T[m][0])]))+" | "+T[m][1]) for m in raw}
print(f"route-aware raw keys {len(raw)} -> normalized {len(set(NK.values()))}  ({len(raw)-len(set(NK.values()))} absorbed)")
con.execute("CREATE TABLE nk(mkt VARCHAR,nmkt VARCHAR)")
con.executemany("INSERT INTO nk VALUES (?,?)",[(m,NK[m]) for m in raw])
con.execute("""CREATE TABLE lmq AS SELECT l.lab, nk.nmkt AS mkt, l.tq, SUM(l.rx) rx, SUM(l.amt) amt
  FROM read_parquet('/tmp/lmq_rt.parquet') l JOIN nk ON nk.mkt=l.mkt GROUP BY 1,2,3""")
con.execute("CREATE TABLE molq AS SELECT mkt mol,tq,SUM(rx) rx,SUM(amt) amt FROM lmq GROUP BY 1,2")
print("markets:",con.execute("SELECT COUNT(DISTINCT mol) FROM molq").fetchone()[0],
      " labeler-market-quarters:",con.execute("SELECT COUNT(*) FROM lmq").fetchone()[0])
con.execute("""CREATE TABLE ev AS
WITH s AS (SELECT lab,mkt,tq,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq ROWS BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4 FROM lmq),
 e AS (SELECT lab,mkt,tq FROM s WHERE pre4>=200 AND post4<0.05*pre4),
 f AS (SELECT lab,mkt,MIN(tq) t FROM e GROUP BY 1,2),
 fr AS (SELECT f.lab,f.mkt,f.t,SUM(l.rx) firm_rx FROM f JOIN lmq l ON l.lab=f.lab AND l.mkt=f.mkt
        AND l.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2,3),
 tt AS (SELECT f.mkt,f.t,SUM(m.rx) mol_rx FROM f JOIN molq m ON m.mol=f.mkt AND m.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2)
SELECT fr.lab,fr.mkt mol,fr.t,fr.firm_rx/NULLIF(tt.mol_rx,0) shr
FROM fr JOIN tt ON tt.mkt=fr.mkt AND tt.t=fr.t WHERE tt.mol_rx>0""")
print("events:",con.execute("SELECT COUNT(*) FROM ev").fetchone()[0],
      " distinct markets:",con.execute("SELECT COUNT(DISTINCT mol) FROM ev").fetchone()[0])
for t,p in [("ev","/tmp/sl_v2.parquet"),("molq","/tmp/molq_v2.parquet"),("lmq","/tmp/lmq_v2.parquet")]:
    con.execute(f"COPY (SELECT * FROM {t}) TO '{p}' (FORMAT PARQUET)")
json.dump(NK,open(os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/market_key_normalization_map.json"),"w"),indent=0)
# cohort
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM molq").fetchall(): MQ.setdefault(m,{})[t]=r
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SL=con.execute("SELECT mol,lab,t,shr FROM ev").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"
inwin={m:v for m,v in first.items() if LO<=v[0]<HI}
COH=[m for m,v in inwin.items() if basec(m,v[0]) is not None]
OBS=[m for m in COH if any(MQ[m].get(inwin[m][0]+k) is not None for k in range(1,7))]
band=lambda s:"<35%" if s<.35 else ("35-65%" if s<.65 else ("65-95%" if s<.95 else "sole"))
print(f"in window={len(inwin)}  baseline-complete={len(COH)}  with post obs={len(OBS)}")
print("bands:",dict(collections.Counter(band(inwin[m][1]) for m in OBS)))
print("\nSOLE events (route-aware + normalized):")
for m in sorted([x for x in OBS if inwin[x][1]>=.95],key=lambda x:inwin[x][0]):
    t,s,lab=inwin[m]; bl=basec(m,t)
    post=np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)])
    print(f"  {cal(t)} lab={lab} base={bl:>9.0f} post/base={post/bl:>5.2f} :: {m[:66]}")

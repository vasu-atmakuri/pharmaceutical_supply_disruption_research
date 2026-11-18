"""Rebuild the market panel on a normalized market key.

Two defects in the raw SDUD ingredient string split a single economic market
across several keys, manufacturing spurious sole-labeler markets:
  (1) form nouns, strengths, USP and word order ("METFORMIN HYDROCHLORIDE" /
      "METFORMIN HYDROCHLORIDE TABLETS"; "PIPERACILLIN SODIUM, TAZOBACTAM
      SODIUM" / "TAZOBACTAM SODIUM AND PIPERACILLIN SODIUM")
  (2) salt naming ("TERBINAFINE" / "TERBINAFINE HYDROCHLORIDE")

Step 1 normalizes to a sorted token set after dropping form nouns, strengths,
schedule codes and connectors. Step 2 merges a key into another ONLY when one
token set equals the other plus salt tokens, so that terbinafine merges with
terbinafine hydrochloride while diclofenac potassium and diclofenac sodium,
which are genuinely distinct markets, do not.
"""
import duckdb, re, collections, json, os
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
DROP={'TABLET','TABLETS','CAPSULE','CAPSULES','INJECTION','INJECTABLE','SOLUTION','SOLUTIONS',
      'USP','AND','THE','FOR','WITH','MG','MCG','ML','GM','CV','CII','CIII','CIV','PACKET','PACKETS',
      'KIT','VIAL','VIALS','SYRINGE','BOTTLE','UNIT','UNITS','PER','DOSE','EACH','NDC'}
SALT={'HYDROCHLORIDE','SODIUM','POTASSIUM','SULFATE','TARTRATE','MALEATE','MESYLATE','ACETATE',
      'CITRATE','PHOSPHATE','SUCCINATE','FUMARATE','BESYLATE','BROMIDE','CHLORIDE','DIHYDRATE',
      'MONOHYDRATE','ANHYDROUS','BITARTRATE','HYDROBROMIDE','NITRATE','OXALATE','PAMOATE',
      'TOSYLATE','VALERATE','PROPIONATE','DIPROPIONATE','FUROATE','XINAFOATE','HCL'}
def tokens(m):
    ing=(m.split(" | ")+[""])[0]
    w=[x for x in re.split(r'[^A-Z0-9]+',ing.upper()) if x]
    return frozenset(x for x in w if x not in DROP and not re.fullmatch(r'[0-9.]+',x) and len(x)>1)
raw=[r[0] for r in con.execute("SELECT DISTINCT mkt FROM read_parquet('/tmp/lmq_nat.parquet')").fetchall()]
T={m:(tokens(m),(m.split(" | ")+[""])[1]) for m in raw}
# step 1: token-set key
k1={m:(",".join(sorted(t))+" | "+f) for m,(t,f) in T.items()}
# step 2: salt containment merge, within form bucket
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
merged=len(raw)-len(set(NK.values()))
print(f"raw market keys {len(raw)} -> normalized {len(set(NK.values()))}  ({merged} keys absorbed)")
print(f"  step 1 only (no salt merge): {len(set(k1.values()))}")
con.execute("CREATE TABLE nk(mkt VARCHAR, nmkt VARCHAR)")
con.executemany("INSERT INTO nk VALUES (?,?)",[(m,NK[m]) for m in raw])
con.execute("""CREATE TABLE lmq AS SELECT l.lab, nk.nmkt AS mkt, l.tq, SUM(l.rx) rx, SUM(l.amt) amt
  FROM read_parquet('/tmp/lmq_nat.parquet') l JOIN nk ON nk.mkt=l.mkt GROUP BY 1,2,3""")
con.execute("CREATE TABLE molq AS SELECT mkt mol,tq,SUM(rx) rx,SUM(amt) amt FROM lmq GROUP BY 1,2")
print("markets:",con.execute("SELECT COUNT(DISTINCT mol) FROM molq").fetchone()[0])
print("labeler-market-quarters:",con.execute("SELECT COUNT(*) FROM lmq").fetchone()[0])
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
print("supplier-loss events:",con.execute("SELECT COUNT(*) FROM ev").fetchone()[0],
      " distinct markets:",con.execute("SELECT COUNT(DISTINCT mol) FROM ev").fetchone()[0])
for lo,hi,nm in [(0,.35,"minor <35%"),(.35,.65,"35-65%"),(.65,.95,"65-95%"),(.95,1.01,"sole >=95%")]:
    c=con.execute(f"SELECT COUNT(*),COUNT(DISTINCT mol) FROM ev WHERE shr>={lo} AND shr<{hi}").fetchone()
    print(f"  {nm:<12} events={c[0]:>5}  markets={c[1]:>5}")
for t,p in [("ev","/tmp/sl_norm.parquet"),("molq","/tmp/molq_norm.parquet"),("lmq","/tmp/lmq_norm.parquet")]:
    con.execute(f"COPY (SELECT * FROM {t}) TO '{p}' (FORMAT PARQUET)")
json.dump({m:NK[m] for m in raw}, open(os.path.expanduser(
  "~/mnt/Research/pharmaceutical_supply_disruption_research/results/market_key_normalization_map.json"),"w"),indent=0)
print("wrote normalized panels + normalization map")

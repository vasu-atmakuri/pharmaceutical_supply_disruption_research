"""What changes if the two known misspellings are corrected by hand.

The normalisation collapses keys that differ in form nouns, strengths, word order or
salt naming. It cannot collapse a key that differs by a typing error in the
ingredient name, because nothing in the string says it is one: ESCITSLOPRAM and
ESCITALOPRAM are as far apart to the algorithm as two different drugs. Two such keys
survive in the corrected panel and both appear as single-source markets.

Leaving them in the main estimate and disclosing them is defensible; leaving them in
without saying how much they move the estimate is not. This applies the two
corrections directly to the panel keys, reruns the detector and the concentration
measure, and reports the difference. The main specification is unchanged: this is a
sensitivity, and the typos are not fixed by a rule that could be applied blind to a
new panel.
"""
import json, os, sys, tempfile, atexit, shutil
import duckdb, numpy as np
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from _detector_sql import detector_sql

# (misspelled key, correctly spelled key). Both are in this panel; the script fails
# if either is absent, so a renamed key cannot make this silently measure nothing.
FIX=[("ESCITSLOPRAM | ORAL TABLET","ESCITALOPRAM | ORAL TABLET"),
     ("GRISOFULVIN | ORAL LIQUID","GRISEOFULVIN | ORAL LIQUID")]

TD=tempfile.mkdtemp(prefix="typo_"); atexit.register(shutil.rmtree,TD,ignore_errors=True)
c=duckdb.connect(os.path.join(TD,"t.duckdb")); c.execute("SET memory_limit='2000MB'")
c.execute("CREATE TABLE lmq0 AS SELECT * FROM read_parquet('/tmp/lmq_v2.parquet')")
c.execute("CREATE TABLE molq0 AS SELECT * FROM read_parquet('/tmp/molq_v2.parquet')")
for bad,good in FIX:
    for t,col in (("lmq0","mkt"),("molq0","mol")):
        n=c.execute(f"SELECT COUNT(*) FROM {t} WHERE {col}=?",[bad]).fetchone()[0]
        m=c.execute(f"SELECT COUNT(*) FROM {t} WHERE {col}=?",[good]).fetchone()[0]
        if not n: sys.exit(f"{bad!r} is not in {t}; update FIX in typo_sensitivity.py")
        if not m: sys.exit(f"{good!r} is not in {t}; the correctly spelled market is "
                           f"needed for the merge to mean anything")

def measure(table_l, table_m, tag):
    """Near-sole dispensing share and the near-sole event cohort on one panel."""
    c.execute(f"CREATE OR REPLACE TABLE lmq AS SELECT * FROM {table_l}")
    c.execute(f"CREATE OR REPLACE TABLE molq AS SELECT * FROM {table_m}")
    # share of dispensing in market-quarters where one labeler holds >=95 percent
    q="""WITH mq AS (SELECT mkt,tq,SUM(rx) tot FROM lmq WHERE rx IS NOT NULL GROUP BY 1,2),
      top AS (SELECT mkt,tq,MAX(rx) mx FROM (SELECT mkt,tq,lab,SUM(rx) rx FROM lmq
              WHERE rx IS NOT NULL GROUP BY 1,2,3) GROUP BY 1,2)
     SELECT SUM(CASE WHEN top.mx>=0.95*mq.tot THEN mq.tot ELSE 0 END)/SUM(mq.tot),
            COUNT(*) FILTER (WHERE top.mx>=0.95*mq.tot), COUNT(*)
     FROM mq JOIN top USING (mkt,tq) WHERE mq.tot>0"""
    vol,nsm,mq=c.execute(q).fetchone()
    c.execute(detector_sql("lmq","molq","ev"))
    ev=c.execute("SELECT COUNT(*) FROM ev").fetchone()[0]
    sole=c.execute("""SELECT COUNT(DISTINCT e.mol) FROM ev e JOIN
      (SELECT mol,MIN(t) t FROM ev GROUP BY 1) f ON f.mol=e.mol AND f.t=e.t
      WHERE e.shr>=0.95""").fetchone()[0]
    nk=c.execute("SELECT COUNT(DISTINCT mkt) FROM lmq").fetchone()[0]
    # The observed cohort and its collapses, on this panel, under the same eligibility
    # and collapse rules as the main analysis. The previous version of this sensitivity
    # stopped at the national share and the detected count, which left the reader to
    # infer what happened to the nineteen observed exits. Two of them are the artefacts
    # this correction removes, so the inference is exactly what should not be left to a
    # reader.
    MQd={}
    for m,t,rx in c.execute("SELECT mol,tq,rx FROM molq").fetchall():
        MQd.setdefault(m,{})[t]=rx
    SLr=c.execute("SELECT mol,lab,t,shr FROM ev").fetchall()
    TMAX=max(t for d in MQd.values() for t in d)
    YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
    firstev={}
    for m,l,t,sh in sorted(SLr,key=lambda x:(x[2],x[0],x[1])):
        if m not in firstev: firstev[m]=(t,sh,l)
    def basec(m,t):
        pp=[MQd[m].get(t+k) for k in range(B0,B1)]
        return None if any(v is None or v<=0 for v in pp) else float(np.mean(pp))
    obs=[]
    for m,(t,sh,l) in firstev.items():
        if sh<0.95 or not (LO<=t<HI): continue
        if basec(m,t) is None: continue
        if not any(MQd[m].get(t+k) is not None for k in range(1,7)): continue
        obs.append(m)
    coll=0
    for m in obs:
        t=firstev[m][0]; bl=basec(m,t)
        post=[MQd[m].get(t+k) for k in range(1,7)]
        if np.mean([0.0 if v is None else v for v in post])<0.02*bl: coll+=1
    out=dict(markets=int(nk),near_sole_volume_share=float(vol),
             near_sole_market_quarters=int(nsm),market_quarters=int(mq),
             events=int(ev),near_sole_exits=int(sole),
             observed_cohort=len(obs),collapsed=int(coll),
             collapse_rate=(float(coll)/len(obs) if obs else None))
    print(f"{tag:<22} markets {nk:>5}  near-sole volume {100*vol:>6.2f}%  "
          f"events {ev:>4}  near-sole exits {sole:>3}  observed {len(obs):>3}  "
          f"collapsed {coll:>2} ({100*coll/len(obs):.1f}%)")
    return out

base=measure("lmq0","molq0","as published")
c.execute("CREATE OR REPLACE TABLE lmq1 AS SELECT * FROM lmq0")
c.execute("CREATE OR REPLACE TABLE molq1 AS SELECT * FROM molq0")
for bad,good in FIX:
    c.execute("UPDATE lmq1 SET mkt=? WHERE mkt=?",[good,bad])
    c.execute("UPDATE molq1 SET mol=? WHERE mol=?",[good,bad])
# the merge creates duplicate rows for a market-quarter-labeler, so re-aggregate
c.execute("""CREATE OR REPLACE TABLE lmq1 AS SELECT lab,mkt,tq,SUM(rx) rx,SUM(amt) amt
             FROM lmq1 GROUP BY 1,2,3""")
c.execute("""CREATE OR REPLACE TABLE molq1 AS SELECT mol,tq,SUM(rx) rx,SUM(amt) amt
             FROM molq1 GROUP BY 1,2""")
fixed=measure("lmq1","molq1","typos corrected")

OUT={"as_published":base,"typos_corrected":fixed,
     "fixes":[{"misspelled":b,"corrected":g} for b,g in FIX],
     "delta":{k:(fixed[k]-base[k]) for k in base},
     "note":("A sensitivity, not the main specification. The two corrections are made by "
             "hand because no rule available to the normalisation identifies a typing "
             "error in an ingredient name; a rule that merged near-identical strings "
             "would also merge genuinely different drugs with similar names.")}
json.dump(OUT,open(f"{R}/results/typo_sensitivity.json","w"),indent=1,sort_keys=True)
print(f"near-sole dispensing share moves "
      f"{100*base['near_sole_volume_share']:.2f}% -> {100*fixed['near_sole_volume_share']:.2f}%, "
      f"near-sole exits {base['near_sole_exits']} -> {fixed['near_sole_exits']}")
print("wrote results/typo_sensitivity.json")

"""How many events each detector specification finds, on one panel.

Four specifications, each differing from the previous one in a single respect:

  rows_sparse   ROWS frames over the observed quarters only. A frame of four rows
                spans more than four quarters whenever a series has a gap, and
                13.1% of series do.
  range_sparse  RANGE frames, so the window is four quarters whether or not every
                quarter is observed, but still over the observed rows. A labeler
                that stops dispensing has no post-window rows at all, so its
                post-period average is NULL and no event can fire.
  range_dense   RANGE frames over a calendar grid from each series' first appearance
                to the panel end, with an absent quarter read as zero dispensing.
                A labeler that stops dispensing now has a post-period average of
                zero, which is what the data mean.
  range_dense_persist  the specification used in the paper. Adds the requirement
                that dispensing not return to half the baseline between t+4 and
                t+12, which removes dips that are suppression or a short gap
                rather than an exit.

The counts are not a robustness check on a result. They record how many events each
choice of window admits, so a reader can see that the correction is not a filter
applied to reach a number.
"""
import json,os,sys,tempfile,atexit,shutil
import duckdb
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LMQ=os.environ.get("LMQ_PARQUET","/tmp/lmq_v2.parquet")
MOL=os.environ.get("MOLQ_PARQUET","/tmp/molq_v2.parquet")
for p in (LMQ,MOL):
    if not os.path.exists(p):
        sys.exit(f"missing {p}; run the national panel stage first")
TD=tempfile.mkdtemp(prefix="dv_"); atexit.register(shutil.rmtree,TD,ignore_errors=True)
c=duckdb.connect(os.path.join(TD,"dv.duckdb"))
c.execute(f"CREATE TABLE lmq AS SELECT * FROM read_parquet('{LMQ}')")
c.execute(f"CREATE TABLE molq AS SELECT * FROM read_parquet('{MOL}')")

DENSE="""dense AS (SELECT g.lab,g.mkt,g.tq,COALESCE(l.rx,0.0) rx FROM
 (SELECT b.lab,b.mkt,q.tq FROM (SELECT lab,mkt,MIN(tq) first_q FROM lmq WHERE rx IS NOT NULL
   GROUP BY 1,2) b, (SELECT MAX(tq) last_q FROM lmq) p, (SELECT UNNEST(range(1,600)) tq) q
  WHERE q.tq BETWEEN b.first_q AND p.last_q) g
 LEFT JOIN lmq l ON l.lab=g.lab AND l.mkt=g.mkt AND l.tq=g.tq)"""
SPARSE="dense AS (SELECT lab,mkt,tq,rx FROM lmq WHERE rx IS NOT NULL)"

def count(frame,source,persist):
    pre=("RANGE" if frame=="RANGE" else "ROWS")+" BETWEEN 4 PRECEDING AND 1 PRECEDING"
    post=("RANGE" if frame=="RANGE" else "ROWS")+" BETWEEN 0 FOLLOWING AND 3 FOLLOWING"
    keep="later_max IS NULL OR later_max < 0.5*pre" if persist else "TRUE"
    q=f"""WITH {source},
 s AS (SELECT lab,mkt,tq,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq {pre}) pre4,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq {post}) post4 FROM dense),
 e AS (SELECT lab,mkt,tq FROM s WHERE pre4>=200 AND post4<0.05*pre4),
 f0 AS (SELECT lab,mkt,MIN(tq) t FROM e GROUP BY 1,2),
 base AS (SELECT f0.lab,f0.mkt,f0.t,
   (SELECT AVG(x.rx) FROM lmq x WHERE x.lab=f0.lab AND x.mkt=f0.mkt
      AND x.tq BETWEEN f0.t-4 AND f0.t-1) pre,
   (SELECT MAX(x.rx) FROM lmq x WHERE x.lab=f0.lab AND x.mkt=f0.mkt
      AND x.tq BETWEEN f0.t+4 AND f0.t+12) later_max FROM f0),
 f AS (SELECT lab,mkt,t FROM base WHERE {keep}),
 fr AS (SELECT f.lab,f.mkt,f.t,SUM(l.rx) firm_rx FROM f JOIN lmq l
        ON l.lab=f.lab AND l.mkt=f.mkt AND l.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2,3),
 tt AS (SELECT f.mkt,f.t,SUM(m.rx) mol_rx FROM f JOIN molq m
        ON m.mol=f.mkt AND m.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2),
 ev AS (SELECT fr.lab,fr.mkt,fr.t,fr.firm_rx/NULLIF(tt.mol_rx,0) shr
        FROM fr JOIN tt ON tt.mkt=fr.mkt AND tt.t=fr.t WHERE tt.mol_rx>0),
 firstev AS (SELECT mkt,MIN(t) t FROM ev GROUP BY 1)
SELECT (SELECT COUNT(*) FROM ev) n,
       (SELECT COUNT(DISTINCT e.mkt) FROM ev e JOIN firstev x
          ON x.mkt=e.mkt AND x.t=e.t WHERE e.shr>=0.95) sole"""
    return c.execute(q).fetchone()

# Two figures the Methods cites alongside the table.
# gappy_pct: the share of labeler-market series with at least one quarter missing
# between their first and last observed quarter. This is why a record-counted window
# is not a calendar window.
gappy=c.execute("""SELECT 100.0*AVG(CASE WHEN n < span THEN 1 ELSE 0 END) FROM
 (SELECT lab,mkt,COUNT(*) n, MAX(tq)-MIN(tq)+1 span FROM lmq WHERE rx IS NOT NULL
  GROUP BY 1,2)""").fetchone()[0]
# vanished: series that stop before the panel ends, with a final four-quarter mean of
# 200 or more at least four quarters before the panel ends, and which the
# record-counted detector on observed quarters never
# reports. These are the exits a NULL post-event window hides.
c.execute("""CREATE OR REPLACE TABLE vanished AS
WITH e AS (SELECT lab,mkt,MIN(tq) f,MAX(tq) l FROM lmq WHERE rx IS NOT NULL GROUP BY 1,2),
 p AS (SELECT MAX(tq) last_q FROM lmq),
 m AS (SELECT e.lab,e.mkt,e.l,(SELECT AVG(x.rx) FROM lmq x WHERE x.lab=e.lab
        AND x.mkt=e.mkt AND x.tq BETWEEN e.l-3 AND e.l) tail FROM e, p WHERE e.l <= p.last_q-4)
SELECT lab,mkt,l,tail FROM m WHERE tail>=200""")
c.execute(f"""CREATE OR REPLACE TABLE rows_ev AS WITH {SPARSE},
 s AS (SELECT lab,mkt,tq,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq ROWS BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4
   FROM dense)
SELECT DISTINCT lab,mkt FROM s WHERE pre4>=200 AND post4<0.05*pre4""")
vanished=c.execute("""SELECT COUNT(*) FROM vanished v WHERE NOT EXISTS
 (SELECT 1 FROM rows_ev r WHERE r.lab=v.lab AND r.mkt=v.mkt)""").fetchone()[0]
print(f"gappy series {gappy:.1f}%   vanished and undetected {vanished}")

out={"gappy_pct":round(float(gappy),1),"vanished_undetected":int(vanished)}
for nm,frame,src,per in (("rows_sparse","ROWS",SPARSE,False),
                         ("range_sparse","RANGE",SPARSE,False),
                         ("range_dense","RANGE",DENSE,False),
                         ("range_dense_persist","RANGE",DENSE,True)):
    n,sole=count(frame,src,per)
    out[nm]={"events":int(n),"near_sole":int(sole)}
    print(f"{nm:22s} events {n:5d}   near-sole {sole:4d}")
# ---- how much of the persistence window each event actually has ----
# The rule asks that a labeler not return to half its baseline between t+4 and t+12.
# An event late in the panel has fewer than twelve quarters of follow-up, so the rule
# is evaluated on a shorter window there. This records how many events are in that
# position and what the detector finds when they are excluded, so the rule's
# dependence on event date is reported rather than assumed away.
_last=c.execute("SELECT MAX(tq) FROM lmq").fetchone()[0]
c.execute(f"""CREATE OR REPLACE TABLE ev_final AS WITH {DENSE},
 s AS (SELECT lab,mkt,tq,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq RANGE BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq RANGE BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4
   FROM dense),
 e AS (SELECT lab,mkt,tq FROM s WHERE pre4>=200 AND post4<0.05*pre4),
 f0 AS (SELECT lab,mkt,MIN(tq) t FROM e GROUP BY 1,2),
 base AS (SELECT f0.lab,f0.mkt,f0.t,
   (SELECT AVG(x.rx) FROM lmq x WHERE x.lab=f0.lab AND x.mkt=f0.mkt
      AND x.tq BETWEEN f0.t-4 AND f0.t-1) pre,
   (SELECT MAX(x.rx) FROM lmq x WHERE x.lab=f0.lab AND x.mkt=f0.mkt
      AND x.tq BETWEEN f0.t+4 AND f0.t+12) later_max FROM f0)
SELECT lab,mkt,t FROM base WHERE later_max IS NULL OR later_max < 0.5*pre""")
_tot=c.execute("SELECT COUNT(*) FROM ev_final").fetchone()[0]
_full=c.execute(f"SELECT COUNT(*) FROM ev_final WHERE t+12<={_last}").fetchone()[0]
# The count that bears on the results is the near-sole subset, since that is the
# cohort every later section uses.
c.execute("""CREATE OR REPLACE TABLE ns AS
 WITH fr AS (SELECT f.lab,f.mkt,f.t,SUM(l.rx) firm_rx FROM ev_final f JOIN lmq l
             ON l.lab=f.lab AND l.mkt=f.mkt AND l.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2,3),
  tt AS (SELECT f.mkt,f.t,SUM(m.rx) mol_rx FROM ev_final f JOIN molq m
         ON m.mol=f.mkt AND m.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2),
  ev AS (SELECT fr.mkt,fr.t,fr.firm_rx/NULLIF(tt.mol_rx,0) shr FROM fr
         JOIN tt ON tt.mkt=fr.mkt AND tt.t=fr.t WHERE tt.mol_rx>0),
  fe AS (SELECT mkt,MIN(t) t FROM ev GROUP BY 1)
 SELECT e.mkt,e.t FROM ev e JOIN fe ON fe.mkt=e.mkt AND fe.t=e.t WHERE e.shr>=0.95""")
_nst=c.execute("SELECT COUNT(*) FROM ns").fetchone()[0]
_nsf=c.execute(f"SELECT COUNT(*) FROM ns WHERE t+12<={_last}").fetchone()[0]
print(f"  near-sole subset: {_nsf} of {_nst} have the full twelve quarters")
out["persistence_window"]={"events":int(_tot),"full_twelve_quarters":int(_full),
 "truncated":int(_tot-_full),
 "near_sole_events":int(_nst),"near_sole_full_twelve":int(_nsf),
 "near_sole_truncated":int(_nst-_nsf),
 "note":("Events whose t+12 falls beyond the panel are evaluated on a shorter "
         "persistence window. The rule is the same; the follow-up available to it "
         "is not.")}
print(f"persistence window: {_full} of {_tot} events have the full twelve quarters, "
      f"{_tot-_full} are evaluated on a shorter window")

# The last row is what the paper reports, so it is checked against the panel's own
# recorded totals rather than trusted. If the detector changes and this file is not
# regenerated, this fails instead of publishing two different numbers.
_sp={x["tag"][0]:x for x in json.load(open(f"{R}/results/three_specifications.json"))}["C"]
_f=out["range_dense_persist"]
assert _f["events"]==_sp["events"], f'variants {_f["events"]} vs spec C {_sp["events"]}'
assert _f["near_sole"]==_sp["sole_flow"]["detected"], \
       f'variants {_f["near_sole"]} vs flow {_sp["sole_flow"]["detected"]}'
print("last row agrees with specification C as recorded in three_specifications.json")
out["note"]=("Each row changes one element of the specification. The last row is the "
             "specification reported in the paper.")
p=os.path.join(R,"results","detector_variants.json")
json.dump(out,open(p,"w"),indent=1,sort_keys=True); print("wrote",p)

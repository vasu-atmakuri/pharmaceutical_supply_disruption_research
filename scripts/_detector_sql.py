"""The labeler-exit detector, in one place, for all three specifications.

Two defects in the previous implementation are fixed here, and the reason each
matters is recorded because the correction changes the event cohort.

1. The window counted ROWS, not calendar quarters. The manuscript defines the
   baseline as the mean over t-4..t-1 and the outcome as the mean over t..t+3. With
   SQL ROWS frames, four preceding ROWS span more than four quarters whenever a
   series has a gap, and 13 percent of labeler-market series do.

2. More seriously, a labeler that stopped dispensing altogether had no rows after
   its exit, so the post-event average was NULL, the comparison was NULL, and the
   event never fired. The detector could only see labelers that kept dispensing a
   little. An audit found 58 labeler-markets that disappear entirely, with
   four-quarter baselines of 200 or more prescriptions, none of them detected.

A third condition is added because the first two exposed it. On a dense grid a
labeler whose dispensing is suppressed for four consecutive quarters and then
resumes satisfies a bare "sustained fall" test, and 67 of 500 such events were
labelers that later returned to half their own baseline or more. A dip is not an
exit, so the detector now also requires that the labeler not return to 50 percent
or more of its baseline at any point from t+4 to t+12. This tightens the definition
rather than loosening it, and it is stated in the Methods.

The first two are fixed by evaluating the detector on a dense calendar grid: one row per
quarter from a series' first appearance to the end of the panel, with an absent
quarter carried as zero dispensing. Absence in SDUD means no reported dispensing,
either none or a count below the suppression threshold of 11, so zero is the right
reading and is conservative against baselines of 200 or more. The grid is used ONLY
to detect events; the panels themselves stay sparse, so no downstream baseline or
outcome calculation changes meaning.
"""

def detector_sql(lmq="lmq", molq="molq", out="ev"):
    return f"""CREATE OR REPLACE TABLE {out} AS
WITH bounds AS (SELECT lab,mkt,MIN(tq) first_q FROM {lmq} WHERE rx IS NOT NULL GROUP BY 1,2),
 panel AS (SELECT MAX(tq) last_q FROM {lmq}),
 grid AS (SELECT b.lab,b.mkt,q.tq
          FROM bounds b, panel p, (SELECT UNNEST(range(1,600)) tq) q
          WHERE q.tq BETWEEN b.first_q AND p.last_q),
 dense AS (SELECT g.lab,g.mkt,g.tq,COALESCE(l.rx,0.0) rx
           FROM grid g LEFT JOIN {lmq} l
           ON l.lab=g.lab AND l.mkt=g.mkt AND l.tq=g.tq),
 s AS (SELECT lab,mkt,tq,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq
                 RANGE BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
   AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq
                 RANGE BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4
   FROM dense),
 e AS (SELECT lab,mkt,tq FROM s WHERE pre4>=200 AND post4<0.05*pre4),
 f0 AS (SELECT lab,mkt,MIN(tq) t FROM e GROUP BY 1,2),
 -- persistence: a labeler that returns to half its baseline later did not exit
 base AS (SELECT f0.lab,f0.mkt,f0.t,
          (SELECT AVG(x.rx) FROM {lmq} x WHERE x.lab=f0.lab AND x.mkt=f0.mkt
           AND x.tq BETWEEN f0.t-4 AND f0.t-1) pre,
          (SELECT MAX(x.rx) FROM {lmq} x WHERE x.lab=f0.lab AND x.mkt=f0.mkt
           AND x.tq BETWEEN f0.t+4 AND f0.t+12) later_max
          FROM f0),
 f AS (SELECT lab,mkt,t FROM base
       WHERE later_max IS NULL OR later_max < 0.5*pre),
 fr AS (SELECT f.lab,f.mkt,f.t,SUM(l.rx) firm_rx FROM f JOIN {lmq} l
        ON l.lab=f.lab AND l.mkt=f.mkt AND l.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2,3),
 tt AS (SELECT f.mkt,f.t,SUM(m.rx) mol_rx FROM f JOIN {molq} m
        ON m.mol=f.mkt AND m.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2)
SELECT fr.lab,fr.mkt mol,fr.t,fr.firm_rx/NULLIF(tt.mol_rx,0) shr
FROM fr JOIN tt ON tt.mkt=fr.mkt AND tt.t=fr.t WHERE tt.mol_rx>0"""

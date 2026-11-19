"""Does the detector's ROWS window change the event set versus calendar quarters?

The manuscript defines the detector on calendar quarters: the mean over t-4..t-1
against the mean over t..t+3. The implementation used SQL ROWS frames, which count
rows rather than quarters, and 13 percent of labeler-market series have at least one
missing quarter inside their span. The two are then not the same window.

This recomputes the detector with RANGE frames, which are calendar-quarter frames
because tq is an integer quarter index, and reports every difference in the event
set, the near-sole candidates and the observed cohort.
"""
import duckdb, json, os
_ROOT=os.environ.get("PSDR_ROOT") or os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
con.execute("CREATE OR REPLACE VIEW lmq AS SELECT * FROM read_parquet('/tmp/lmq_v2.parquet')")
con.execute("CREATE OR REPLACE VIEW molq AS SELECT * FROM read_parquet('/tmp/molq_v2.parquet')")

def events(frame):
    con.execute(f"""CREATE OR REPLACE TABLE ev_{frame} AS
    WITH s AS (SELECT lab,mkt,tq,
       AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq {frame} BETWEEN 4 PRECEDING AND 1 PRECEDING) pre4,
       AVG(rx) OVER (PARTITION BY lab,mkt ORDER BY tq {frame} BETWEEN 0 FOLLOWING AND 3 FOLLOWING) post4
       FROM lmq),
     e AS (SELECT lab,mkt,tq FROM s WHERE pre4>=200 AND post4<0.05*pre4),
     f AS (SELECT lab,mkt,MIN(tq) t FROM e GROUP BY 1,2),
     fr AS (SELECT f.lab,f.mkt,f.t,SUM(l.rx) firm_rx FROM f JOIN lmq l
            ON l.lab=f.lab AND l.mkt=f.mkt AND l.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2,3),
     tt AS (SELECT f.mkt,f.t,SUM(m.rx) mol_rx FROM f JOIN molq m
            ON m.mol=f.mkt AND m.tq BETWEEN f.t-4 AND f.t-1 GROUP BY 1,2)
    SELECT fr.lab,fr.mkt mol,fr.t,fr.firm_rx/NULLIF(tt.mol_rx,0) shr
    FROM fr JOIN tt ON tt.mkt=fr.mkt AND tt.t=fr.t WHERE tt.mol_rx>0""")
    return con.execute(f"SELECT COUNT(*), SUM(CASE WHEN shr>=0.95 THEN 1 ELSE 0 END) FROM ev_{frame}").fetchone()

rows_n, rows_sole = events("ROWS")
rng_n,  rng_sole  = events("RANGE")
same=con.execute("""SELECT COUNT(*) FROM ev_ROWS r JOIN ev_RANGE g
  ON g.lab=r.lab AND g.mol=r.mol AND g.t=r.t""").fetchone()[0]
only_rows=con.execute("""SELECT COUNT(*) FROM ev_ROWS r LEFT JOIN ev_RANGE g
  ON g.lab=r.lab AND g.mol=r.mol AND g.t=r.t WHERE g.lab IS NULL""").fetchone()[0]
only_rng=con.execute("""SELECT COUNT(*) FROM ev_RANGE g LEFT JOIN ev_ROWS r
  ON g.lab=r.lab AND g.mol=r.mol AND g.t=r.t WHERE r.lab IS NULL""").fetchone()[0]
shifted=con.execute("""SELECT COUNT(*) FROM ev_ROWS r JOIN ev_RANGE g
  ON g.lab=r.lab AND g.mol=r.mol WHERE g.t<>r.t""").fetchone()[0]
sole_rows=set(con.execute("SELECT lab,mol,t FROM ev_ROWS WHERE shr>=0.95").fetchall())
sole_rng =set(con.execute("SELECT lab,mol,t FROM ev_RANGE WHERE shr>=0.95").fetchall())
out=dict(rows_events=rows_n, range_events=rng_n,
         rows_near_sole=rows_sole, range_near_sole=rng_sole,
         identical_events=same, only_under_rows=only_rows, only_under_range=only_rng,
         same_series_different_quarter=shifted,
         near_sole_identical=len(sole_rows & sole_rng),
         near_sole_only_rows=len(sole_rows - sole_rng),
         near_sole_only_range=len(sole_rng - sole_rows),
         gappy_series_pct=con.execute("""
           WITH s AS (SELECT lab,mkt,COUNT(*) n,MAX(tq)-MIN(tq)+1 span FROM lmq
                      WHERE rx IS NOT NULL GROUP BY 1,2)
           SELECT ROUND(100.0*SUM(CASE WHEN n<span THEN 1 ELSE 0 END)/COUNT(*),1) FROM s""").fetchone()[0])
json.dump(out,open(f"{_ROOT}/results/detector_window_test.json","w"),indent=1)
print(f"series with a missing quarter inside their span: {out['gappy_series_pct']}%\n")
print(f"{'':24}{'ROWS':>8}{'RANGE':>8}")
print(f"{'detected events':24}{rows_n:>8}{rng_n:>8}")
print(f"{'near-sole (share>=0.95)':24}{rows_sole:>8}{rng_sole:>8}")
print(f"\nevent identity:")
print(f"  identical (labeler, market, quarter) : {same}")
print(f"  only under ROWS                      : {only_rows}")
print(f"  only under RANGE                     : {only_rng}")
print(f"  same series, different event quarter : {shifted}")
print(f"\nnear-sole set: identical {out['near_sole_identical']}, "
      f"only ROWS {out['near_sole_only_rows']}, only RANGE {out['near_sole_only_range']}")

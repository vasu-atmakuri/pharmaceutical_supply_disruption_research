"""Stage 1a: the form-only crosswalk, derived from the route-aware one.

This re-parsed FDA's product.txt and the openFDA NDC file, which stage 1b already
parses for exactly the same rows. Parsing twice cost more than a minute, produced two
tables that could disagree, and was the slowest stage in the pipeline. The form-only
crosswalk is the route-aware crosswalk without the route column, plus the
established-pharmacologic-class string that natpanel.py labels markets with, so it is
now projected from it.
"""
import duckdb, os
import os as _os
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser(
    "~/mnt/Research/pharmaceutical_supply_disruption_research")
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
if not os.path.exists("/tmp/xw_route.parquet"):
    raise SystemExit("/tmp/xw_route.parquet is missing: run rebuild_xw_route.py first. "
                     "run_all.sh orders these stages correctly.")
con=duckdb.connect(); con.execute("SET memory_limit='1200MB'")
con.execute("""CREATE OR REPLACE TABLE xw2 AS
  SELECT lab, pcode, generic, substance, pclass, form,
         CASE WHEN pclass IS NULL THEN NULL
              ELSE regexp_extract(pclass,'([^;,]*\\[EPC\\])',1) END AS epc
  FROM read_parquet('/tmp/xw_route.parquet')""")
n=con.execute("SELECT COUNT(*) FROM xw2").fetchone()[0]
e=con.execute("SELECT COUNT(*) FROM xw2 WHERE epc IS NOT NULL AND epc<>''").fetchone()[0]
con.execute("COPY (SELECT * FROM xw2) TO '/tmp/xw.parquet' (FORMAT PARQUET)")
print(f"form-only crosswalk: {n:,} labeler-product keys, {e:,} with an EPC class")

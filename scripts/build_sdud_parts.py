"""Stage 0: aggregate the raw SDUD year files into one parquet part per year.

Reads the national aggregate rows (State='XX') from each StateDrugUtilizationData
year file and writes a labeler-product-quarter part beside the data. Every later
stage reads these parts, but nothing in the pipeline built them: they were produced
by an ad-hoc command, so a clean machine failed at stage 2 with no parts to read.

Idempotent and resumable: a year whose part already exists is skipped, so re-running
costs nothing. The raw files are large, so a first run takes a while.

Paths: SDUD_PARTS for the output folder, RESEARCH_ROOT for the folder holding sdud/.
"""
import duckdb, glob, os, sys, time
D=os.environ.get("SDUD_DIR") or (
    (os.environ.get("RESEARCH_ROOT") or os.path.expanduser("~/mnt/Research"))+"/sdud")
W=os.environ.get("SDUD_PARTS_DIR") or (
    (os.environ.get("RESEARCH_ROOT") or os.path.expanduser("~/mnt/Research"))+"/sdud_parts")
if os.environ.get("SDUD_PARTS"):                 # a glob was given; use its folder
    W=os.path.dirname(os.environ["SDUD_PARTS"])
os.makedirs(W, exist_ok=True)
# The raw year files are 5 GB of public bulk data and were deleted from the working
# machine once the parts existed; see DATA.md. Their absence is only an error if there
# are no parts to read either, so that case is checked first. The parts are the data as
# far as every later stage is concerned.
have=sorted(glob.glob(W+"/*.x.parquet"))
if not have:
    have=sorted(glob.glob(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                          +"/data/sdud_parts/*.parquet"))
files=[]
if os.path.isdir(D):
    files=[f for f in sorted(glob.glob(D+"/StateDrugUtilizationData-*.csv")
                             +glob.glob(D+"/sdud2*.csv"))
           if any(str(y) in os.path.basename(f) for y in range(2016,2027))]
if not files:
    if have:
        print(f"parts folder: {W}\nno raw year files in {D}; "
              f"{len(have)} parts already present, nothing to build")
        raise SystemExit(0)
    sys.exit(f"no SDUD year files for 2016-2026 in {D} and no parts in {W}.\n"
             f"See DATA.md: the parts committed under data/sdud_parts are what the "
             f"panel stages read, or re-download the year files with "
             f"wget -i sdud/dl.txt -P sdud/")
todo=[f for f in files if not os.path.exists(W+"/"+os.path.basename(f)+".x.parquet")]
print(f"SDUD source: {D}\nparts folder: {W}\n{len(files)} year files, {len(todo)} to build")
for f in todo:
    b=os.path.basename(f); s=time.time()
    con=duckdb.connect(); con.execute("SET memory_limit='1200MB'"); con.execute("SET threads=2")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""CREATE VIEW s AS SELECT * FROM read_csv('{f}', all_varchar=true,
                    header=true, quote='"', escape='"')""")
    con.execute(f"""COPY (SELECT "Labeler Code" lab, "Product Code" pcode,
      TRY_CAST("Year" AS INT) yr, TRY_CAST("Quarter" AS INT) qtr,
      SUM(TRY_CAST("Number of Prescriptions" AS DOUBLE)) rx,
      SUM(TRY_CAST("Total Amount Reimbursed" AS DOUBLE)) amt,
      COUNT(*) ncells,
      SUM(CASE WHEN TRY_CAST("Number of Prescriptions" AS DOUBLE) IS NULL THEN 1 ELSE 0 END) nsupp
      FROM s WHERE "State"='XX' GROUP BY 1,2,3,4) TO '{W}/{b}.x.parquet' (FORMAT PARQUET)""")
    print(f"  {b}: {time.time()-s:.0f}s", flush=True); con.close()
built=[f for f in files if os.path.exists(W+"/"+os.path.basename(f)+".x.parquet")]
print(f"{len(built)} of {len(files)} parts present")
if len(built)!=len(files):
    sys.exit(f"{len(files)-len(built)} parts missing; re-run this stage")

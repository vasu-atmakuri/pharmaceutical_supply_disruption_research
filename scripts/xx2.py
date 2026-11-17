import duckdb, glob, os, sys, time
D=os.path.expanduser("~/mnt/Research/sdud"); W=os.path.expanduser("~/work/partsxx")
files=[f for f in sorted(glob.glob(D+"/StateDrugUtilizationData-*.csv")+glob.glob(D+"/sdud2*.csv"))
       if any(str(y) in os.path.basename(f) for y in range(2016,2027))]
todo=[f for f in files if not os.path.exists(W+"/"+os.path.basename(f)+".x.parquet")]
print(f"{len(todo)} remaining of {len(files)}",flush=True)
t0=time.time(); budget=float(sys.argv[1]) if len(sys.argv)>1 else 150.0
for f in todo:
    if time.time()-t0>budget: print("budget hit, rerun",flush=True); break
    b=os.path.basename(f); s=time.time()
    con=duckdb.connect(); con.execute("SET memory_limit='1200MB'"); con.execute("SET threads=2")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""CREATE VIEW s AS SELECT * FROM read_csv('{f}', all_varchar=true, header=true, quote='"', escape='"')""")
    con.execute(f"""COPY (SELECT "Labeler Code" lab, "Product Code" pcode,
      TRY_CAST("Year" AS INT) yr, TRY_CAST("Quarter" AS INT) qtr,
      SUM(TRY_CAST("Number of Prescriptions" AS DOUBLE)) rx,
      SUM(TRY_CAST("Total Amount Reimbursed" AS DOUBLE)) amt,
      COUNT(*) ncells,
      SUM(CASE WHEN TRY_CAST("Number of Prescriptions" AS DOUBLE) IS NULL THEN 1 ELSE 0 END) nsupp
      FROM s WHERE "State"='XX' GROUP BY 1,2,3,4) TO '{W}/{b}.x.parquet' (FORMAT PARQUET)""")
    print(f"  {b}: {time.time()-s:.0f}s",flush=True); con.close()
print("REMAINING:",len([f for f in files if not os.path.exists(W+"/"+os.path.basename(f)+".x.parquet")]),flush=True)

import duckdb, glob, os, sys, time
D=os.path.expanduser("~/mnt/Research/sdud"); W=os.path.expanduser("~/work/parts3")
files=sorted(glob.glob(D+"/StateDrugUtilizationData-*.csv")+glob.glob(D+"/sdud2*.csv"))
todo=[f for f in files if not os.path.exists(W+"/"+os.path.basename(f)+".n.parquet")]
print(f"{len(files)} total, {len(todo)} remaining",flush=True)
t0=time.time(); budget=float(sys.argv[1]) if len(sys.argv)>1 else 150.0
for f in todo:
    if time.time()-t0>budget: print("budget",flush=True); break
    b=os.path.basename(f); s=time.time()
    con=duckdb.connect(); con.execute("SET memory_limit='1200MB'"); con.execute("SET threads=2")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""CREATE VIEW s AS SELECT * FROM read_csv('{f}',
      all_varchar=true, header=true, quote='"', escape='"')""")
    con.execute(f"""COPY (SELECT "Labeler Code" lab, "Product Code" pcode,
      trim("Product Name") product, TRY_CAST("Year" AS INT) yr, TRY_CAST("Quarter" AS INT) qtr,
      COUNT(*) ncells, COUNT(DISTINCT "State") nstates,
      SUM(TRY_CAST("Number of Prescriptions" AS DOUBLE)) rx,
      SUM(TRY_CAST("Units Reimbursed" AS DOUBLE)) units,
      SUM(TRY_CAST("Total Amount Reimbursed" AS DOUBLE)) amt
      FROM s WHERE "State"<>'XX' GROUP BY 1,2,3,4,5) TO '{W}/{b}.n.parquet' (FORMAT PARQUET)""")
    print(f"  {b}: {time.time()-s:.0f}s",flush=True); con.close()
print("REMAINING:",len([f for f in files if not os.path.exists(W+"/"+os.path.basename(f)+".n.parquet")]),flush=True)

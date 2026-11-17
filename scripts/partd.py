import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
p=os.path.expanduser("~/mnt/Research/aux/partd_spending.csv")
con.execute(f"""CREATE OR REPLACE TABLE pd AS SELECT * FROM read_csv('{p}',header=true,all_varchar=true,ignore_errors=true)""")
n=con.execute("SELECT COUNT(*) FROM pd").fetchone()[0]
print(f"rows: {n:,}",flush=True)
YRS=[y for y in range(2019,2024)]
sel=", ".join([f'TRY_CAST("Tot_Clms_{y}" AS DOUBLE) c{y}' for y in YRS]+
              [f'TRY_CAST("Tot_Spndng_{y}" AS DOUBLE) s{y}' for y in YRS])
con.execute(f"""CREATE OR REPLACE TABLE d AS SELECT upper(trim("Gnrc_Name")) gnrc, upper(trim("Brnd_Name")) brnd,
  TRY_CAST("Tot_Mftr" AS INT) nmftr, "Mftr_Name" mftr, {sel} FROM pd""")
print("\n=== Tot_Mftr distribution (Overall rows) ===",flush=True)
for r in con.execute("""SELECT nmftr, COUNT(*) n FROM d WHERE mftr='Overall' AND nmftr IS NOT NULL
  GROUP BY 1 ORDER BY 1 LIMIT 10""").fetchall(): print(f"   {r[0]} manufacturer(s): {r[1]:,} drugs",flush=True)
# A Part D analogue of supplier loss: drug-level manufacturer count falls to 1 or 0 is not
# observable year to year in this file (Tot_Mftr is a single current value), so instead use the
# manufacturer-level rows: a manufacturer's claims for a drug collapsing between consecutive years.
print("\n=== MANUFACTURER-LEVEL EXITS IN PART D ===",flush=True)
con.execute("""CREATE OR REPLACE TABLE mrow AS SELECT gnrc,brnd,mftr,nmftr,
  c2019,c2020,c2021,c2022,c2023 FROM d WHERE mftr<>'Overall' AND mftr IS NOT NULL""")
print("manufacturer-drug rows:",con.execute("SELECT COUNT(*) FROM mrow").fetchone()[0],flush=True)
rows=con.execute("SELECT gnrc,brnd,mftr,nmftr,c2019,c2020,c2021,c2022,c2023 FROM mrow").fetchall()
drug={}
for g,b,mf,nm,*cs in rows: drug.setdefault((g,b),[]).append((mf,nm,cs))
print(f"distinct drugs: {len(drug):,}",flush=True)
YI={2019:0,2020:1,2021:2,2022:3,2023:4}
events=[]
for (g,b),lst in drug.items():
    tot=[sum(x[2][i] or 0 for x in lst) for i in range(5)]
    for mf,nm,cs in lst:
        for i in range(1,4):                       # exit between year i-1 and i, need i+1 for post
            pre=cs[i-1]; cur=cs[i]
            if not pre or pre<1000: continue
            if (cur or 0) > 0.05*pre: continue      # this manufacturer collapsed
            if tot[i-1] is None or tot[i-1]<=0: continue
            shr=pre/tot[i-1]
            post=tot[i+1] if i+1<5 else None
            if post is None: continue
            events.append((g,b,mf,i,shr,tot[i-1],post,len(lst)))
print(f"manufacturer-exit events with a following year: {len(events)}",flush=True)
def band(s):
    return "under 35%" if s<.35 else ("35 to 95%" if s<.95 else "95% or above")
print(f"\n  {'departing share':<16}{'n':>5}{'drug claims collapse':>22}{'median change':>16}",flush=True)
OUT={}
for nm in ["under 35%","35 to 95%","95% or above"]:
    sel=[e for e in events if band(e[4])==nm]
    if not sel: continue
    ch=[(e[6]-e[5])/e[5] for e in sel]
    col=sum(1 for e in sel if e[6]<=0.02*e[5])
    OUT[nm]=dict(n=len(sel),collapse=col/len(sel),median=float(np.median(ch)))
    print(f"  {nm:<16}{len(sel):>5}{col}/{len(sel)} = {col/len(sel):>8.1%}{100*np.median(ch):>14.1f}%",flush=True)
print("\n=== largest sole-manufacturer exits in Part D ===",flush=True)
sole=sorted([e for e in events if e[4]>=.95],key=lambda e:-e[5])[:12]
for g,b,mf,i,shr,pre,post,nl in sole:
    print(f"  {(b or g)[:30]:<32}{mf[:24]:<26}{2018+i}  {pre:>10,.0f} -> {post:>10,.0f}  {100*(post/pre-1):>+7.1f}%",flush=True)
json.dump(OUT,open(os.path.expanduser("~/mnt/Research/RESULTS_partd.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_partd.json",flush=True)

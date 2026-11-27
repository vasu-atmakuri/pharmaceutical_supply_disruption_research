"""What stands behind each suppressed market-quarter, counted in NDC product codes.

The reviewer's objection is correct and the previous version of this audit did not meet
it. It counted labeler series, and a labeler is not an NDC: one labeler can market
several product codes in the same normalized market, different strengths and package
sizes among them, and each is a separately reported cell that can be withheld on its
own. Near-sole also means a leading share of at least 95 percent, not one exclusive
supplier, so other labelers can contribute cells too.

So this counts product codes. For every suppressed market-quarter in the outcome window
of an observed near-sole event, it reports the distinct (labeler, product code) cells
that were dispensing into that market in the four quarters before the exit, the number
of labelers among them, the market's baseline, the two-percent collapse threshold the
baseline implies, and the ceiling that the primary suppression rule allows for the
quarter as a whole: ten prescriptions for each cell that could have been withheld.

It then reruns the collapse classification with every suppressed quarter set to that
ceiling, which is the most adverse NDC-aware scenario the suppression rule permits, and
reports how many of the nineteen events change classification. That is the number the
primary estimate has to survive, and reporting it is the only way the zero-imputed rate
can be read honestly.

Written to results/ndc_suppression_audit.json and, per quarter, to
results/ndc_suppression_audit.csv so the counts can be checked without rerunning this.
"""
import csv, glob, json, os, sys
import duckdb, numpy as np
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D=os.environ.get("RESEARCH_ROOT") or os.path.dirname(R)
PARTS=os.environ.get("SDUD_PARTS") or (D+"/sdud_parts/*.parquet")
px=sorted(glob.glob(PARTS)) or sorted(glob.glob(f"{R}/data/sdud_parts/*.parquet"))
if not px: sys.exit(f"no SDUD parts at {PARTS}")
MAP=json.load(open(f"{R}/results/market_key_normalization_map.json"))

con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
MQ={}; LMQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_v2.parquet')").fetchall():
    MQ.setdefault(m,{})[t]=r
for l,m,t,r in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_v2.parquet')").fetchall():
    LMQ.setdefault(m,{}).setdefault(t,{})[l]=r
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_v2.parquet')").fetchall()
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1
B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
inwin={m:v for m,v in first.items() if LO<=v[0]<HI}
OBS=[m for m,v in inwin.items() if basec(m,v[0]) is not None
     and any(MQ[m].get(v[0]+k) is not None for k in range(1,7))]
sole=[m for m in OBS if inwin[m][1]>=0.95]
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"

# product-code level activity, mapped to the normalized market the panel uses
con.execute("CREATE OR REPLACE TABLE nk(raw VARCHAR, norm VARCHAR)")
con.executemany("INSERT INTO nk VALUES (?,?)", list(MAP.items()))
_np=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "natpanel_route.py")).read()
_i=_np.index(" CASE\n  WHEN rt LIKE '%OPHTHALMIC%'")
BUCKET=_np[_i:_np.index("ELSE 'OTHER' END",_i)+len("ELSE 'OTHER' END")]
con.execute(f"""CREATE OR REPLACE TABLE cells AS
SELECT nk.norm mkt, (n.yr-1991)*4+n.qtr tq, n.lab, n.pcode, n.rx
FROM read_parquet({px!r}) n
JOIN (SELECT lab,pcode,generic,
             {BUCKET} AS bucket
      FROM (SELECT lab,pcode,generic,upper(COALESCE(route,'')) rt,
                   upper(COALESCE(form,'')) f
            FROM read_parquet('/tmp/xw_route.parquet') WHERE generic<>'')) x
  ON x.lab=lpad(n.lab,5,'0') AND x.pcode=lpad(n.pcode,4,'0')
JOIN nk ON nk.raw = x.generic||' | '||x.bucket""")
print(f"product-code cells mapped: "
      f"{con.execute('SELECT COUNT(*) FROM cells').fetchone()[0]:,}")

rows=[]
for m in sole:
    t,_s,lab=inwin[m]; bl=basec(m,t); thr=0.02*bl
    for k in range(1,7):
        if MQ[m].get(t+k) is not None: continue
        q=con.execute("""SELECT COUNT(DISTINCT lab||'-'||pcode), COUNT(DISTINCT lab)
                         FROM cells WHERE mkt=? AND tq BETWEEN ?-4 AND ?-1 AND rx IS NOT NULL
                      """,[m,t,t]).fetchone()
        ncells,nlabs=int(q[0]),int(q[1])
        present=con.execute("""SELECT COUNT(DISTINCT lab||'-'||pcode) FROM cells
                               WHERE mkt=? AND tq=? AND rx IS NOT NULL""",[m,t+k]).fetchone()[0]
        rows.append(dict(market=m, event_quarter=cal(t), missing_quarter=cal(t+k),
                         baseline_rx=round(bl,1), collapse_threshold_rx=round(thr,1),
                         ndc_cells_before=ncells, labelers_before=nlabs,
                         ndc_cells_reported_that_quarter=int(present),
                         ceiling_rx=10*ncells,
                         ceiling_above_threshold=int(10*ncells>thr)))
with open(f"{R}/results/ndc_suppression_audit.csv","w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# the adverse NDC-aware scenario: every suppressed quarter at its own ceiling
def collapse(m, fill):
    t=inwin[m][0]; bl=basec(m,t)
    p=[]
    for k in range(1,7):
        v=MQ[m].get(t+k)
        p.append(v if v is not None else fill(m,t+k))
    return 1 if float(np.mean(p))<0.02*bl else 0
ceil_by={(r["market"],r["missing_quarter"]):r["ceiling_rx"] for r in rows}
zero=sum(collapse(m, lambda mm,q: 0.0) for m in sole)
ten =sum(collapse(m, lambda mm,q: 10.0) for m in sole)
ceil=sum(collapse(m, lambda mm,q: float(ceil_by.get((mm,cal(q)),0))) for m in sole)
cells=[r["ndc_cells_before"] for r in rows]
OUT={"observed_events":len(sole),
     "suppressed_market_quarters":len(rows),
     "events_with_any":len({r["market"] for r in rows}),
     "ndc_cells_per_suppressed_quarter":{"min":int(min(cells)),
        "median":float(np.median(cells)),"max":int(max(cells))},
     "labelers_per_suppressed_quarter_max":int(max(r["labelers_before"] for r in rows)),
     "quarters_whose_ceiling_exceeds_the_threshold":
        sum(r["ceiling_above_threshold"] for r in rows),
     "collapses_zero_fill":int(zero),
     "collapses_ten_per_quarter":int(ten),
     "collapses_ndc_aware_ceiling":int(ceil),
     "note":("A cell is a (labeler, product code) series, which is the unit CMS "
             "suppresses. The ceiling for a suppressed market-quarter is ten "
             "prescriptions for each cell that was dispensing into the market in the "
             "four quarters before the exit, which is the most the primary rule allows "
             "that quarter to have held. Secondary suppression can withhold a cell to "
             "protect another, so even this is not a guaranteed bound. The last three "
             "figures are the collapse count under zero imputation, under ten "
             "prescriptions per market-quarter, and under the per-quarter ceiling.")}
json.dump(OUT,open(f"{R}/results/ndc_suppression_audit.json","w"),indent=1,sort_keys=True)
print(f"{len(rows)} suppressed market-quarters across {OUT['events_with_any']} of {len(sole)} events")
print(f"NDC cells behind them: min {min(cells)}, median {np.median(cells):.0f}, max {max(cells)}; "
      f"at most {OUT['labelers_per_suppressed_quarter_max']} labeler(s)")
print(f"ceiling above the collapse threshold in "
      f"{OUT['quarters_whose_ceiling_exceeds_the_threshold']} of {len(rows)} quarters")
print(f"collapses: {zero} zero-filled, {ten} at ten per quarter, {ceil} at the NDC-aware ceiling")
print("wrote results/ndc_suppression_audit.json and .csv")

"""How many reported cells stand behind a suppressed market-quarter.

A reviewer made two objections to the justification for reading an absent post-event
quarter as zero, and both are right.

The first is arithmetic. The collapse rule is a post-event mean below two percent of
baseline, which for a baseline of 200 prescriptions is four. Ten is above four, so ten
prescriptions does not satisfy the rule, and the paper's claim that either end of the
zero-to-ten range is a collapse was simply wrong. The sensitivity already showed it: the
collapse count falls from eight to seven when an absent quarter is read as ten.

The second is aggregation, and it is the more important one. Suppression applies to the
reported labeler-product cell, not to the market. A market-quarter can have several
suppressed cells behind it, so its unobserved total can exceed ten even if every
withheld cell is under eleven. This measures that: for every suppressed market-quarter
in an observed event's outcome window, how many labeler-product series were dispensing
into that market shortly before, which is the number of cells that could be withheld at
once, and therefore the scale of the quantity the zero reading sets to nothing.
"""
import duckdb, numpy as np, json, os, sys
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

rows=[]
for m in sole:
    t,_s,lab=inwin[m]; bl=basec(m,t)
    for k in range(1,7):
        if MQ[m].get(t+k) is not None: continue
        # labeler series dispensing into this market in the four quarters before the exit
        active=set()
        for j in range(-4,0):
            active|= {l for l,v in LMQ.get(m,{}).get(t+j,{}).items() if v}
        rows.append(dict(market=m, quarter=t+k, baseline_rx=round(bl,1),
                         collapse_threshold_rx=round(0.02*bl,1),
                         labeler_series_before=len(active),
                         max_if_each_cell_under_eleven=10*len(active)))
nsupp=len(rows)
cells=[r["labeler_series_before"] for r in rows]
exceeds=[r for r in rows if r["max_if_each_cell_under_eleven"]>r["collapse_threshold_rx"]]
OUT={"observed_events":len(sole),
     "suppressed_market_quarters":nsupp,
     "events_with_any":len({r["market"] for r in rows}),
     "labeler_series_per_suppressed_quarter":{
        "min":int(min(cells)) if cells else 0,"median":float(np.median(cells)) if cells else 0,
        "max":int(max(cells)) if cells else 0},
     "quarters_where_the_implied_ceiling_exceeds_the_collapse_threshold":len(exceeds),
     "note":("For each suppressed quarter in an observed event's outcome window, the number "
             "of labeler-product series dispensing into that market in the four quarters "
             "before the exit. Suppression applies to the cell, not the market, so the "
             "unobserved market total can be as large as ten times that count, which is "
             "above the two-percent collapse threshold in most cases. Ten prescriptions is "
             "therefore not a bound on a market-quarter, and the zero reading is a "
             "convention whose effect is measured in the outcome sensitivity rather than a "
             "consequence of the suppression rule.")}
json.dump(OUT,open(f"{R}/results/ndc_suppression_audit.json","w"),indent=1,sort_keys=True)
print(f"{nsupp} suppressed market-quarters across {OUT['events_with_any']} of {len(sole)} events")
if cells:
    print(f"labeler series behind them: min {min(cells)}, median {np.median(cells):.0f}, "
          f"max {max(cells)}")
    print(f"{len(exceeds)} of {nsupp} have an implied ceiling above the collapse threshold")
print("wrote results/ndc_suppression_audit.json")

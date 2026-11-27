"""The collapse outcome under three readings of a suppressed post-event quarter.

The Methods said the dense grid was used only to detect events and that no baseline or
outcome calculation treats a suppressed quarter as a zero. The second half was not true
of the outcome: the collapse rule averages the six post-event quarters with an absent
quarter read as zero, and eligibility only requires that one of the six be observed. A
reviewer read the released code and found it. The sentence is now corrected, and the
choice is measured here instead of asserted.

Three readings, all on the same cohort:

  zero       an absent post-event quarter counts as zero dispensing. This is what the
             paper reports, and it is the conservative reading for a collapse measure:
             absence means CMS withheld a count under eleven prescriptions, which
             against a baseline of 200 or more is close to zero.
  observed   the mean is taken over the observed quarters only, so a suppressed quarter
             neither lowers nor raises it. This is the complete-case reading.
  ten        every absent quarter counts as ten prescriptions, the most the suppression
             threshold allows a single withheld quarter to be.

Secondary suppression means a withheld cell can be suppressed to protect another cell
rather than because it is small, so ten is not a hard ceiling on what a quarter held.
It is the ceiling the primary rule implies, and the three readings are scenarios rather
than a bound.
"""
import duckdb, numpy as np, json, os, sys
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
MQ={}; LMQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_v2.parquet')").fetchall():
    MQ.setdefault(m,{})[t]=r
for l,m,t,r in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_v2.parquet')").fetchall():
    LMQ.setdefault((m,l),{})[t]=r
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

def post_mean(m,t,mode):
    p=[MQ[m].get(t+k) for k in range(1,7)]
    if mode=="zero":     v=[0.0 if x is None else x for x in p]
    elif mode=="ten":    v=[10.0 if x is None else x for x in p]
    else:                v=[x for x in p if x is not None]
    return float(np.mean(v)) if v else None

OUT={}
for mode in ("zero","observed","ten"):
    coll=[]; nsupp=0
    for m in sole:
        t=inwin[m][0]; bl=basec(m,t)
        if any(MQ[m].get(t+k) is None for k in range(1,7)): nsupp+=1
        pm=post_mean(m,t,mode)
        coll.append(1 if (pm is not None and pm<0.02*bl) else 0)
    OUT[mode]={"n":len(sole),"collapsed":int(sum(coll)),
               "rate":float(np.mean(coll)),
               "events_with_a_suppressed_post_quarter":nsupp}
    print(f"  {mode:9s} {sum(coll):2d} of {len(sole)} collapse  "
          f"({100*np.mean(coll):.1f}%)")
OUT["note"]=("Three readings of an absent post-event quarter, on the same observed "
  "cohort. The paper reports the zero reading. Secondary suppression means ten is the "
  "ceiling the primary rule implies and not a hard bound, so these are scenarios.")
OUT["events_affected"]=OUT["zero"]["events_with_a_suppressed_post_quarter"]
p=f"{R}/results/outcome_missing_sensitivity.json"
json.dump(OUT,open(p,"w"),indent=1,sort_keys=True)
print(f"\n{OUT['events_affected']} of {len(sole)} observed events have at least one "
      f"suppressed quarter in the outcome window")
print("wrote results/outcome_missing_sensitivity.json")

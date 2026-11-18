import duckdb, numpy as np, collections
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_v2.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_v2.parquet')").fetchall()
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"
def basec_strict(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def basec_relaxed(m,t,need=2):
    p=[v for v in (MQ[m].get(t+k) for k in range(-8,-1)) if v is not None and v>0]
    return float(np.mean(p)) if len(p)>=need else None
sole_all=[(m,v[0],v[1],v[2]) for m,v in first.items() if v[1]>=.95]
print(f"sole events in panel (first per market): {len(sole_all)}")
inw=[x for x in sole_all if LO<=x[1]<HI]
print(f"  within event window LO<=t<TMAX-6 ({cal(LO)}..{cal(HI-1)}): {len(inw)}   lost to window: {len(sole_all)-len(inw)}")
b1=[x for x in inw if basec_strict(x[0],x[1]) is not None]
print(f"  with 4 consecutive clean baseline quarters t-6..t-3: {len(b1)}   lost: {len(inw)-len(b1)}")
b2=[x for x in b1 if any(MQ[x[0]].get(x[1]+k) is not None for k in range(1,7))]
print(f"  with >=1 observed post quarter t+1..t+6: {len(b2)}   lost: {len(b1)-len(b2)}")
print(f"  ===> PRIMARY sole cohort: {len(b2)}")
r1=[x for x in inw if basec_relaxed(x[0],x[1]) is not None]
r2=[x for x in r1 if any(MQ[x[0]].get(x[1]+k) is not None for k in range(1,7))]
print(f"\nRELAXED baseline (>=2 observed quarters in t-8..t-2): cohort {len(r2)}  (+{len(r2)-len(b2)})")
print("\nevents recovered by the relaxed baseline:")
got={x[0] for x in b2}
for m,t,s,l in sorted([x for x in r2 if x[0] not in got],key=lambda x:x[1]):
    bl=basec_relaxed(m,t)
    print(f"  {cal(t)} lab={l} base~{bl:>8.0f} :: {m[:66]}")
print("\nsole events lost to the END-OF-PANEL window (t>=TMAX-6):")
for m,t,s,l in sorted([x for x in sole_all if t>=HI for t in [x[1]]],key=lambda x:x[1]):
    print(f"  {cal(t)} lab={l} :: {m[:66]}")

import duckdb, numpy as np, re
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
LMQ={}
for l,m,t,r in con.execute("SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_nat.parquet')").fetchall():
    LMQ.setdefault((m,t),{})[l]=r
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2
LO,HI=YMIN-B0+2,TMAX-6
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def cal(tq): return f"{1991+(tq-1)//4}Q{(tq-1)%4+1}"
def mean_win(m,t,a,b):
    v=[MQ[m].get(t+k) for k in range(a,b)]
    v=[0.0 if x is None else x for x in v]
    return float(np.mean(v)) if v else 0.0
inwin={m:v for m,v in first.items() if LO<=v[0]<HI}
sole=sorted([(m,v[0],v[1],v[2]) for m,v in inwin.items() if basec(m,v[0]) is not None
      and any(MQ[m].get(v[0]+k) is not None for k in range(1,7)) and v[1]>=.95], key=lambda x:x[1])
ALLM=set(MQ)
def toks(s):
    return set(w for w in re.split(r'[^A-Z0-9]+',s.split(" | ")[0].upper()) if len(w)>3)
print("For each sole event: did a near-identical market key gain volume when this one lost it?")
print("LOST = market's own drop (baseline minus post). SIB_GAIN = sum of sibling post-pre.\n")
for m,t,s,lab in sole:
    frm=(m.split(" | ")+[""])[1]; A=toks(m)
    bl=basec(m,t); post=mean_win(m,t,1,7); lost=bl-post
    sibs=[]
    for o in ALLM:
        if o==m or (o.split(" | ")+[""])[1]!=frm: continue
        B=toks(o)
        if not A or not B: continue
        j=len(A&B)/max(1,len(A|B))
        if j>=0.55:
            pre_o=mean_win(o,t,B0,B1); post_o=mean_win(o,t,1,7)
            sibs.append((j,o,pre_o,post_o,post_o-pre_o))
    gain=sum(x[4] for x in sibs)
    flag="  <== SIBLING ABSORBS" if lost>0 and gain>0.5*lost else ""
    print(f"{cal(t)} {m.split(' | ')[0][:46]:<46} LOST={lost:>9.0f}  SIB_GAIN={gain:>9.0f}{flag}")
    for j,o,pre_o,post_o,d in sorted(sibs,key=lambda x:-x[4])[:2]:
        print(f"          jac={j:.2f} pre={pre_o:>8.0f} post={post_o:>8.0f} d={d:>+9.0f} :: {o[:66]}")

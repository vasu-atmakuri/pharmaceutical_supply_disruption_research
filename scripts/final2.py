exec(open('final.py').read().split('rng=np.random.default_rng(101)')[0])
import numpy as np, json
S={}
for m,l,t in con.execute("SELECT mol,lab,tq FROM lm WHERE rx>0").fetchall(): S.setdefault((m,t),set()).add(l)
EPC={r[0]:r[1] for r in con.execute("SELECT mol,any_value(epc) FROM j WHERE mol IS NOT NULL AND epc IS NOT NULL GROUP BY 1").fetchall()}
CL={}
for m,t,v in con.execute("SELECT mol,tq,rx FROM molq").fetchall():
    e=EPC.get(m)
    if e: CL.setdefault((e,t),{})[m]=v
TT={m:(t,s) for m,t,s in T}
B=[(0,.35,"minor 0-35%"),(.35,.95,"mid 35-95%"),(.95,1.01,"sole 95-100%")]
def band(lo,hi): return [m for m in TT if lo<=TT[m][1]<hi]
print("=== EVENT-TIME, ingredient panel, threshold 2000 (log vs t-1) ===",flush=True)
print("  band            "+"".join(f"{k:>8}" for k in range(-6,9)),flush=True)
for lo,hi,nm in B+[(0,1.01,"all treated")]:
    out=[]
    for k in range(-6,9):
        v=[np.log(MQ[m][TT[m][0]+k])-np.log(MQ[m][TT[m][0]-1]) for m in band(lo,hi)
           if MQ.get(m,{}).get(TT[m][0]+k,0)>0 and MQ.get(m,{}).get(TT[m][0]-1,0)>0]
        out.append(np.mean(v) if v else np.nan)
    print(f"  {nm:<14}"+"".join(f"{x:>+8.3f}" for x in out),flush=True)
print("\n=== SUPPLIER COUNT AND ENTRY ===",flush=True)
print("  band             n   sup t-1   t+4   t+8   new firms by t+8   % with entry",flush=True)
for lo,hi,nm in B:
    r=[]
    for m in band(lo,hi):
        t=TT[m][0]
        if (m,t-1) not in S: continue
        pre=S[(m,t-1)]; new=set()
        for k in range(0,9): new|= (S.get((m,t+k),set())-pre)
        r.append((len(pre),len(S.get((m,t+4),set())),len(S.get((m,t+8),set())),len(new)))
    if not r: continue
    A=np.array(r)
    print(f"  {nm:<14}{len(r):>4}    {A[:,0].mean():.2f}  {A[:,1].mean():.2f}  {A[:,2].mean():.2f}"
          f"         {A[:,3].mean():.2f}            {100*(A[:,3]>0).mean():.0f}%",flush=True)
print("\n=== SUBSTITUTION: other ingredients in same EPC class (log vs t-1) ===",flush=True)
print("  band             n     t+0     t+2     t+4     t+6     t+8",flush=True)
for lo,hi,nm in B:
    sel=[m for m in band(lo,hi) if m in EPC]; out=[]
    for k in (0,2,4,6,8):
        v=[]
        for m in sel:
            t=TT[m][0]; e=EPC[m]
            a=sum(x for mm,x in CL.get((e,t+k),{}).items() if mm!=m)
            b=sum(x for mm,x in CL.get((e,t-1),{}).items() if mm!=m)
            if a>0 and b>0: v.append(np.log(a)-np.log(b))
        out.append((np.mean(v) if v else np.nan,len(v)))
    print(f"  {nm:<14}{out[0][1]:>4}  "+"  ".join(f"{a:+.3f}" for a,_ in out),flush=True)

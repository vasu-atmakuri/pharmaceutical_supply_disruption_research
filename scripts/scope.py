exec(open('final.py').read().split('rng=np.random.default_rng(101)')[0])
import numpy as np
FORM={r[0]:r[1] for r in con.execute("""SELECT xw.generic, any_value(xw.form) FROM read_parquet('/tmp/xw.parquet') xw
  WHERE xw.generic<>'' GROUP BY 1""").fetchall()}
EPC={r[0]:r[1] for r in con.execute("SELECT mol,any_value(epc) FROM j WHERE mol IS NOT NULL AND epc IS NOT NULL GROUP BY 1").fetchall()}
AMT={}
for m,t,v in con.execute("""SELECT xw.generic,(n.yr-2014)*4+n.qtr,SUM(n.amt) FROM read_parquet('/home/'||'x' ) x""" if False else
  "SELECT mol,tq,SUM(amt) FROM (SELECT xw.generic mol,(n.yr-2014)*4+n.qtr tq,n.amt FROM read_parquet('"+parts[0]+"') n JOIN read_parquet('/tmp/xw.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0') WHERE xw.generic<>'') GROUP BY 1,2").fetchall(): pass
# spending panel across all parts
con.execute(f"""CREATE OR REPLACE TABLE molamt AS SELECT xw.generic mol,(n.yr-2014)*4+n.qtr tq,SUM(n.amt) amt
  FROM read_parquet({parts!r}) n JOIN read_parquet('/tmp/xw.parquet') xw
  ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
  WHERE xw.generic<>'' AND n.yr BETWEEN 2014 AND 2025 AND n.amt IS NOT NULL GROUP BY 1,2""")
MA={}
for m,t,v in con.execute("SELECT mol,tq,amt FROM molamt").fetchall(): MA.setdefault(m,{})[t]=v
TT={m:(t,s) for m,t,s in T}
sole=[m for m in TT if TT[m][1]>=0.95]
print(f"=== A. SOLE-SUPPLIER INGREDIENTS AFFECTED (n={len(sole)}) ===",flush=True)
rowsout=[]
for m in sole:
    t=TT[m][0]
    pre=[MQ[m].get(t+k) for k in range(-4,0)]; post=[MQ[m].get(t+k) for k in range(1,5)]
    if any(v is None or v<=0 for v in pre): continue
    pv=np.mean(pre); qv=np.mean([v for v in post if v and v>0]) if any(v and v>0 for v in post) else 0.0
    rowsout.append((m,f"{2014+(t-1)//4}Q{(t-1)%4+1}",pv,qv,(qv/pv-1)*100,(FORM.get(m,'') or '')[:18],(EPC.get(m,'') or '')[:34]))
rowsout.sort(key=lambda r:-r[2])
print(f"  {'ingredient':<30}{'exit':<8}{'pre rx/q':>10}{'post rx/q':>11}{'change':>9}  {'form':<18} class",flush=True)
for r in rowsout[:22]:
    print(f"  {r[0][:29]:<30}{r[1]:<8}{r[2]:>10,.0f}{r[3]:>11,.0f}{r[4]:>8.0f}%  {r[5]:<18}{r[6]}",flush=True)
print(f"\n  total pre-exit volume at risk: {sum(r[2] for r in rowsout):,.0f} rx/quarter",flush=True)
print(f"  median change: {np.median([r[4] for r in rowsout]):.0f}%   share losing >50%: {100*np.mean([r[4]<-50 for r in rowsout]):.0f}%",flush=True)
def did(sel,P,lo=-6,hi=6):
    o=[]
    for m in sel:
        t=TT[m][0] if m in TT else None
        if t is None: continue
        pre=[P.get(m,{}).get(t+k) for k in range(lo,0)]; post=[P.get(m,{}).get(t+k) for k in range(1,hi+1)]
        if any(v is None or v<=0 for v in pre+post): continue
        o.append(np.mean(np.log(post))-np.mean(np.log(pre)))
    return np.array(o)
print("\n=== B. SPENDING vs VOLUME, sole-supplier band ===",flush=True)
for nm,P in [("prescriptions",MQ),("Medicaid spending",MA)]:
    v=did(sole,P); print(f"  {nm:<20} n={len(v):>3}  mean log change={v.mean():+.3f} ({100*(np.exp(v.mean())-1):+.1f}%)",flush=True)
print("\n=== C. FORM HETEROGENEITY, sole-supplier band ===",flush=True)
inj=[m for m in sole if 'INJECT' in (FORM.get(m,'') or '')]
oth=[m for m in sole if m not in inj]
for nm,sel in [("injectable",inj),("non-injectable",oth)]:
    v=did(sel,MQ)
    if len(v): print(f"  {nm:<16} n={len(v):>3}  {v.mean():+.3f} ({100*(np.exp(v.mean())-1):+.1f}%)",flush=True)
print("\n=== D. DOES REMAINING SUPPLIER COUNT MODERATE RECOVERY? (all treated) ===",flush=True)
S={}
for m,l,t in con.execute("SELECT mol,lab,tq FROM lm WHERE rx>0").fetchall(): S.setdefault((m,t),set()).add(l)
for lo,hi,nm in [(0,1,"0 remaining"),(1,2,"1 remaining"),(2,4,"2-3 remaining"),(4,999,"4+ remaining")]:
    sel=[m for m in TT if lo<=len(S.get((m,TT[m][0]+4),set()))<hi]
    v=did(sel,MQ)
    if len(v)>2: print(f"  {nm:<16} n={len(v):>3}  {v.mean():+.3f} ({100*(np.exp(v.mean())-1):+.1f}%)",flush=True)

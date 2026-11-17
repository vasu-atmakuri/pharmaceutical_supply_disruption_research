exec(open('rxonly.py').read().split('rng=np.random.default_rng(77)')[0])
import numpy as np, json
con.execute("CREATE OR REPLACE VIEW rc AS SELECT * FROM read_parquet('/tmp/recalls2.parquet')")
EV={r[0]:r[1] for r in con.execute("SELECT lab,t FROM ev").fetchall()}
A={r[0]:dict(n=r[1],c1=r[2]) for r in con.execute("""SELECT e.lab,COUNT(*),SUM(CASE WHEN rc.cls='Class I' THEN 1 ELSE 0 END)
  FROM ev e JOIN rc ON rc.lab=lpad(e.lab,5,'0') AND rc.tq BETWEEN e.t-4 AND e.t+4 GROUP BY 1""").fetchall()}
QQ={r[0] for r in con.execute("""SELECT e.lab FROM ev e JOIN rc ON rc.lab=lpad(e.lab,5,'0')
  AND rc.tq BETWEEN e.t-4 AND e.t+4
  WHERE lower(rc.reason) LIKE '%cgmp%' OR lower(rc.reason) LIKE '%good manufacturing%'
     OR lower(rc.reason) LIKE '%steril%' OR lower(rc.reason) LIKE '%contamina%'
     OR lower(rc.reason) LIKE '%impurit%' OR lower(rc.reason) LIKE '%nitrosamine%' GROUP BY 1""").fetchall()}
print("=== EXIT CAUSE SPLIT (firm-name matched) ===",flush=True)
print(f"  exits total: {len(EV)}",flush=True)
print(f"  recall-associated (any recall within +/-4 qtrs): {len(A)} ({100*len(A)/len(EV):.0f}%)",flush=True)
print(f"  quiet exits (no recall): {len(EV)-len(A)} ({100*(len(EV)-len(A))/len(EV):.0f}%)",flush=True)
print(f"  at least one Class I recall: {sum(1 for v in A.values() if v['c1']>0)}",flush=True)
print(f"  quality-driven (CGMP/sterility/contamination/impurity text): {len(QQ)}",flush=True)
MOLLAB=con.execute("""SELECT l.mol,l.lab FROM lm l JOIN ev e ON e.lab=l.lab AND l.tq BETWEEN e.t-4 AND e.t-1 GROUP BY 1,2""").fetchall()
M2L={}
for m,l in MOLLAB: M2L.setdefault(m,set()).add(l)
def feat(sel):
    z=[];l1=[]
    for m in sel:
        t=TT[m][0]; s=MQ.get(m,{})
        pre=[s.get(t+k) for k in range(-6,0)]
        if any(v is None or v<=0 for v in pre): continue
        post=[s.get(t+k) or 0.0 for k in range(1,7)]
        z.append(1.0 if np.mean(post)<=0.02*np.mean(pre) else 0.0)
        l1.append(np.mean(np.log1p(post))-np.mean(np.log1p(pre)))
    return np.array(z),np.array(l1)
rng=np.random.default_rng(66); td=[t for _,t,_ in T]
cz,cl=feat(ctl) if False else (None,None)
def featc(sel,getT):
    z=[];l1=[]
    for m in sel:
        t=getT(m); s=MQ.get(m,{})
        pre=[s.get(t+k) for k in range(-6,0)]
        if any(v is None or v<=0 for v in pre): continue
        post=[s.get(t+k) or 0.0 for k in range(1,7)]
        z.append(1.0 if np.mean(post)<=0.02*np.mean(pre) else 0.0)
        l1.append(np.mean(np.log1p(post))-np.mean(np.log1p(pre)))
    return np.array(z),np.array(l1)
cz,cl=featc(ctl,lambda m:int(rng.choice(td)))
out={}
for scope,sel0 in [("sole 95-100%",[m for m,_,s in T if s>=.95]),("all treated",[m for m,_,s in T])]:
    print(f"\n=== {scope.upper()}: EFFECT BY EXIT CAUSE ===",flush=True)
    print("  cause                  n    P(collapse)   vs ctrl   log1p change   perm p",flush=True)
    for nm,test in [("recall-associated",lambda L: L & set(A)),("quiet (no recall)",lambda L: not (L & set(A))),
                    ("quality-driven",lambda L: L & QQ)]:
        sel=[m for m in sel0 if test(M2L.get(m,set()))]
        z,l=feat(sel)
        if len(l)<2: print(f"  {nm:<22}{len(l):>3}   too few",flush=True); continue
        d=l.mean()-cl.mean(); ph=[]
        for _ in range(400):
            s2=list(rng.choice(ctl,size=min(max(len(l)*3,30),len(ctl)),replace=False))
            _,b=featc(s2,lambda m:int(rng.choice(td)))
            if len(b)>5: ph.append(b.mean()-cl.mean())
        ph=np.array(ph); p=(np.sum(np.abs(ph)>=abs(d))+1)/(len(ph)+1)
        out[f"{scope}|{nm}"]=dict(n=int(len(l)),collapse=float(z.mean()),log1p_did=float(d),pct=float(100*(np.exp(d)-1)),p=float(p))
        print(f"  {nm:<22}{len(l):>3}      {z.mean():.0%}        {cz.mean():.0%}      {100*(np.exp(d)-1):>+7.1f}%      {p:.4f}",flush=True)
json.dump(dict(exits=len(EV),recall_assoc=len(A),quiet=len(EV)-len(A),
  class1=sum(1 for v in A.values() if v['c1']>0),quality=len(QQ),by_cause=out),
  open(os.path.expanduser("~/mnt/Research/firm_exit_cause_split.json"),'w'),indent=2)
print("\nwrote Research/firm_exit_cause_split.json",flush=True)

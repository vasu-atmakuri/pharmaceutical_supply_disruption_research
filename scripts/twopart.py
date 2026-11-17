exec(open('rxonly.py').read().split('rng=np.random.default_rng(77)')[0])
import numpy as np, json
rng=np.random.default_rng(91); td=[t for _,t,_ in T]
def feat(sel,getT):
    zero=[];l1=[]
    for m in sel:
        t=getT(m); s=MQ.get(m,{})
        pre=[s.get(t+k) for k in range(-6,0)]
        if any(v is None or v<=0 for v in pre): continue
        post=[s.get(t+k) or 0.0 for k in range(1,7)]
        zero.append(1.0 if np.mean(post)<=0.02*np.mean(pre) else 0.0)
        l1.append(np.mean(np.log1p(post))-np.mean(np.log1p(pre)))
    return np.array(zero),np.array(l1)
print("  band              n   P(collapse to ~0)   log1p DiD    change    perm p",flush=True)
res={}
for lo,hi,nm in [(0,.35,"minor 0-35%"),(.35,.95,"mid 35-95%"),(.95,1.01,"sole 95-100%"),(0,1.01,"all treated")]:
    sel=[m for m,_,s in T if lo<=s<hi]
    tz,tl=feat(sel,lambda m:TT[m][0]); cz,cl=feat(ctl,lambda m:int(rng.choice(td)))
    dz=tz.mean()-cz.mean(); dl=tl.mean()-cl.mean()
    pz=[];pl=[]
    for _ in range(600):
        s2=list(rng.choice(ctl,size=min(max(len(tl)*3,30),len(ctl)),replace=False))
        a,b=feat(s2,lambda m:int(rng.choice(td)))
        if len(b)>5: pz.append(a.mean()-cz.mean()); pl.append(b.mean()-cl.mean())
    pz,pl=np.array(pz),np.array(pl)
    p_l=(np.sum(np.abs(pl)>=abs(dl))+1)/(len(pl)+1); p_z=(np.sum(np.abs(pz)>=abs(dz))+1)/(len(pz)+1)
    res[nm]=dict(n=int(len(tl)),p_collapse_treated=float(tz.mean()),p_collapse_control=float(cz.mean()),
      collapse_diff=float(dz),collapse_p=float(p_z),log1p_did=float(dl),pct=float(100*(np.exp(dl)-1)),log1p_p=float(p_l))
    print(f"  {nm:<16}{len(tl):>4}   {tz.mean():.0%} vs {cz.mean():.0%} ctrl (p={p_z:.3f})   {dl:+.4f}  {100*(np.exp(dl)-1):>+7.1f}%   {p_l:.4f}",flush=True)
print("\n=== event-time, log1p, zeros retained, sole band ===",flush=True)
sole=[m for m in TT if TT[m][1]>=0.95]
for k in range(-6,9):
    v=[np.log1p(MQ[m].get(TT[m][0]+k) or 0.0)-np.log1p(MQ[m][TT[m][0]-1]) for m in sole
       if MQ.get(m,{}).get(TT[m][0]-1,0)>0]
    print(f"   t{k:+d}: {np.mean(v):+.3f} (n={len(v)})",flush=True)
json.dump(res,open(os.path.expanduser("~/mnt/Research/firm_exit_results_twopart.json"),'w'),indent=2)
print("\nwrote Research/firm_exit_results_twopart.json",flush=True)

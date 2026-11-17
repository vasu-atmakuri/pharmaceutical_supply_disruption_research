exec(open('rxonly.py').read().split('rng=np.random.default_rng(77)')[0])
import numpy as np, json
rng=np.random.default_rng(55); td=[t for _,t,_ in T]
def slope(m,t):
    y=[MQ.get(m,{}).get(t+k) for k in range(-6,0)]
    if any(v is None or v<=0 for v in y): return None
    return np.polyfit(range(6),np.log(y),1)[0]
def feat(sel,getT,flat=False):
    z=[];l=[]
    for m in sel:
        t=getT(m); s=MQ.get(m,{})
        pre=[s.get(t+k) for k in range(-6,0)]
        if any(v is None or v<=0 for v in pre): continue
        if flat:
            sl=slope(m,t)
            if sl is None or abs(sl)>0.10: continue
        post=[s.get(t+k) or 0.0 for k in range(1,7)]
        z.append(1.0 if np.mean(post)<=0.02*np.mean(pre) else 0.0)
        l.append(np.mean(np.log1p(post))-np.mean(np.log1p(pre)))
    return np.array(z),np.array(l)
sole=[m for m,_,s in T if s>=.95]
print("=== PRE-TREND DIAGNOSTIC ===",flush=True)
sl=[slope(m,TT[m][0]) for m in sole]; sl=[x for x in sl if x is not None]
slc=[slope(m,int(rng.choice(td))) for m in ctl]; slc=[x for x in slc if x is not None]
print(f"  sole-supplier pre-trend slope: mean={np.mean(sl):+.4f} median={np.median(sl):+.4f} (log pts/qtr, n={len(sl)})",flush=True)
print(f"  control        pre-trend slope: mean={np.mean(slc):+.4f} median={np.median(slc):+.4f} (n={len(slc)})",flush=True)
print(f"  share of sole-supplier with |slope|<=0.10: {100*np.mean([abs(x)<=.10 for x in sl]):.0f}%",flush=True)
print("\n=== RESTRICTED TO FLAT PRE-TRENDS (|slope|<=0.10 log pts/qtr) ===",flush=True)
print("  band              n   P(collapse) treated vs ctrl   log1p DiD   change    perm p",flush=True)
res={}
for lo,hi,nm in [(0,.35,"minor 0-35%"),(.95,1.01,"sole 95-100%"),(0,1.01,"all treated")]:
    sel=[m for m,_,s in T if lo<=s<hi]
    tz,tl=feat(sel,lambda m:TT[m][0],flat=True); cz,cl=feat(ctl,lambda m:int(rng.choice(td)),flat=True)
    if len(tl)<3: continue
    dz=tz.mean()-cz.mean(); dl=tl.mean()-cl.mean(); pz=[];pl=[]
    for _ in range(500):
        s2=list(rng.choice(ctl,size=min(len(ctl),400),replace=False))
        a,b=feat(s2,lambda m:int(rng.choice(td)),flat=True)
        if len(b)>5: pz.append(a.mean()-cz.mean()); pl.append(b.mean()-cl.mean())
    pz,pl=np.array(pz),np.array(pl)
    p_l=(np.sum(np.abs(pl)>=abs(dl))+1)/(len(pl)+1); p_z=(np.sum(np.abs(pz)>=abs(dz))+1)/(len(pz)+1)
    res[nm]=dict(n=int(len(tl)),collapse_t=float(tz.mean()),collapse_c=float(cz.mean()),collapse_p=float(p_z),
                 log1p_did=float(dl),pct=float(100*(np.exp(dl)-1)),p=float(p_l))
    print(f"  {nm:<16}{len(tl):>4}      {tz.mean():.0%} vs {cz.mean():.0%} (p={p_z:.3f})       {dl:+.3f}  {100*(np.exp(dl)-1):>+7.1f}%   {p_l:.4f}",flush=True)
json.dump(res,open(os.path.expanduser("~/mnt/Research/firm_exit_results_flat_pretrend.json"),'w'),indent=2)
print("\nwrote Research/firm_exit_results_flat_pretrend.json",flush=True)

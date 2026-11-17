import duckdb, numpy as np, matplotlib, os
matplotlib.use('Agg'); import matplotlib.pyplot as plt
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
LMQ={}
for m,l,t,r in con.execute("SELECT mkt,lab,tq,rx FROM read_parquet('/tmp/lmq_nat.parquet')").fetchall(): LMQ.setdefault((m,l),{})[t]=r
S={}
for (m,l),d in LMQ.items():
    for t,v in d.items():
        if v and v>0: S.setdefault((m,t),set()).add(l)
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SLall=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
ever={m for m,_,_,_ in SLall}
first={}
for m,l,t,s in sorted([x for x in SLall if LO<=x[2]<=HI],key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
def ok(m,t):
    s=MQ.get(m,{})
    if any(s.get(t+k) is None or (s.get(t+k) or 0)<=0 for k in range(B0,B1)): return False
    return not all(s.get(t+k) is None for k in range(1,7))
EV=[m for m in first if ok(m,first[m][0])]
pool=[m for m in MQ if m not in ever]; rng=np.random.default_rng(2026); K=list(range(-6,7))
def mkt(m,t): return MQ.get(m,{}).get(t) or 0.0
def oth(m,t,dl): return max(mkt(m,t)-(LMQ.get((m,dl),{}).get(t) or 0.0),0.0)
def logpath(items):
    o={k:[] for k in K}
    for m,t,dl in items:
        b=np.mean([np.log1p(mkt(m,t+k)) for k in range(B0,B1)])
        for k in K: o[k].append(np.log1p(mkt(m,t+k))-b)
    return {k:(np.mean(v),np.std(v)/max(np.sqrt(len(v)),1),len(v)) for k,v in o.items()}
def rpath(items):
    o={k:[] for k in K}
    for m,t,dl in items:
        dep_b=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
        oth_b=np.mean([oth(m,t+k,dl) for k in range(B0,B1)])
        if dep_b<=0: continue
        for k in K: o[k].append((oth(m,t+k,dl)-oth_b)/dep_b)
    return {k:(np.mean(v),np.std(v)/max(np.sqrt(len(v)),1),np.median(v),len(v)) for k,v in o.items()}
sole=[(m,first[m][0],first[m][2]) for m in EV if first[m][1]>=.95]
minor=[(m,first[m][0],first[m][2]) for m in EV if first[m][1]<.35]
mid=[(m,first[m][0],first[m][2]) for m in EV if .35<=first[m][1]<.95]
ctl=[]
for m,t,dl in sole:
    bm=np.mean([MQ[m][t+k] for k in range(B0,B1)])
    cs=[c for c in pool if ok(c,t) and len(S.get((c,t-1),set()))==1
        and bm/3<=np.mean([MQ[c][t+k] for k in range(B0,B1)])<=bm*3]
    if len(cs)>25: cs=list(rng.choice(cs,size=25,replace=False))
    ctl+=[(c,t,None) for c in cs]
A=logpath(sole); Bm=logpath(minor); C=logpath(ctl)
Rs=rpath(sole); Rmid=rpath(mid); Rmin=rpath(minor)
fig,axes=plt.subplots(1,2,figsize=(10.6,4.2))
ax=axes[0]
for d,lab,col,mk in [(A,f"sole-supplier loss (n={A[0][2]})",'#b2182b','o'),
                     (Bm,f"minor-supplier loss (n={Bm[0][2]})",'#2166ac','s'),
                     (C,f"matched single-supplier, no loss (n={C[0][2]})",'#6e6e6e','^')]:
    ax.errorbar(K,[d[k][0] for k in K],yerr=[1.96*d[k][1] for k in K],label=lab,color=col,marker=mk,ms=3.6,lw=1.5,capsize=2)
ax.axvspan(B0-0.4,B1-0.6,color='#cccccc',alpha=.35,lw=0); ax.text((B0+B1-1)/2,0.75,"baseline",ha='center',fontsize=7,color='#555')
ax.axvline(-0.5,color='k',ls='--',lw=1,alpha=.7); ax.axhline(0,color='k',lw=.7,alpha=.4)
ax.set_xlabel("quarters relative to supplier loss"); ax.set_ylabel("change in log(1+prescriptions)")
ax.set_title("(a) Total market dispensing",fontsize=10); ax.legend(frameon=False,fontsize=7.2,loc='lower left'); ax.grid(alpha=.18); ax.set_xticks(K)
ax=axes[1]
for d,lab,col,mk in [(Rmin,f"minor-supplier loss (n={Rmin[0][3]})",'#2166ac','s'),
                     (Rmid,f"35 to 95% (n={Rmid[0][3]})",'#4d9221','v'),
                     (Rs,f"sole-supplier loss (n={Rs[0][3]})",'#b2182b','o')]:
    ax.plot(K,[d[k][2] for k in K],label=lab,color=col,marker=mk,ms=3.6,lw=1.5)
ax.axhline(1.0,color='k',ls=':',lw=1,alpha=.6); ax.text(-5.8,1.03,"full replacement",fontsize=7,color='#444')
ax.axhline(0,color='k',lw=.7,alpha=.4); ax.axvline(-0.5,color='k',ls='--',lw=1,alpha=.7)
ax.set_xlabel("quarters relative to supplier loss")
ax.set_ylabel("median replacement ratio")
ax.set_title("(b) Volume taken up by remaining suppliers,\nas a fraction of the departing supplier's volume",fontsize=9.5)
ax.legend(frameon=False,fontsize=7.2,loc='upper left'); ax.grid(alpha=.18); ax.set_xticks(K); ax.set_ylim(-0.3,1.8)
fig.tight_layout()
p=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/figures/fig1_supplier_loss_matched.pdf")
fig.savefig(p); fig.savefig(p.replace('.pdf','.png'),dpi=300)
print("wrote figure. controls n =",C[0][3] if len(C[0])>3 else C[0][2],flush=True)
print("\n median replacement ratio at t+6:",flush=True)
for nm,d in [("minor",Rmin),("35-95%",Rmid),("sole",Rs)]: print(f"   {nm:<8} {d[6][2]:+.2f}   (n={d[6][3]})",flush=True)

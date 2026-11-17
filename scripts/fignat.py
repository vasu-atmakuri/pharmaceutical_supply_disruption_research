import duckdb, numpy as np, matplotlib, os
matplotlib.use('Agg'); import matplotlib.pyplot as plt
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SL=[(m,t,s) for m,t,s in con.execute("SELECT mol,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall() if LO<=t<=HI]
first={}
for m,t,s in sorted(SL,key=lambda x:x[1]):
    if m not in first: first[m]=(t,s)
treated=set(first)
ctl=[m for m in MQ if m not in treated and len([t for t in MQ[m] if MQ[m][t] and MQ[m][t]>0 and t>=YMIN])>=34
     and np.mean([v for v in MQ[m].values() if v])>=400]
rng=np.random.default_rng(9); td=[t for t,_ in first.values()]; K=range(-6,7)
def path(sel,getT):
    o={k:[] for k in K}
    for m in sel:
        t=getT(m); s=MQ.get(m,{})
        if not (LO<=t<=HI): continue
        b=[s.get(t+k) for k in range(B0,B1)]
        if any(v is None or v<=0 for v in b): continue
        if all(s.get(t+k) is None for k in range(1,7)): continue
        bl=np.mean([np.log1p(v) for v in b])
        for k in K:
            v=s.get(t+k)
            if v is not None or k>=0: o[k].append(np.log1p(v or 0.0)-bl)
    return {k:(np.mean(v),np.std(v)/max(np.sqrt(len(v)),1),len(v)) for k,v in o.items() if v}
A=path([m for m in first if first[m][1]>=.95],lambda m:first[m][0])
B=path([m for m in first if first[m][1]<.35],lambda m:first[m][0])
C=path(ctl,lambda m:int(rng.choice(td)))
fig,ax=plt.subplots(figsize=(7.2,4.4))
for d,lab,col,mk in [(A,f"sole supplier, 95% or more (n={A[0][2]})",'#b2182b','o'),
                     (B,f"minor supplier, under 35% (n={B[0][2]})",'#2166ac','s'),
                     (C,f"never exposed, placebo dates (n={C[0][2]})",'#6e6e6e','^')]:
    x=sorted(d); y=[d[k][0] for k in x]; e=[1.96*d[k][1] for k in x]
    ax.errorbar(x,y,yerr=e,label=lab,color=col,marker=mk,ms=4,lw=1.6,capsize=2.5)
ax.axvspan(B0-0.4,B1-0.6,color='#cccccc',alpha=.35,lw=0)
ax.text((B0+B1-1)/2,0.6,"baseline",ha='center',fontsize=7.5,color='#555555')
ax.axvline(-0.5,color='k',ls='--',lw=1,alpha=.7)
ax.axhline(0,color='k',lw=.7,alpha=.4)
ax.set_xlabel("quarters relative to supplier loss"); ax.set_ylabel("change in log(1+prescriptions)")
ax.legend(frameon=False,fontsize=8,loc='lower left'); ax.grid(alpha=.18); ax.set_xticks(list(K))
fig.tight_layout()
p=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/figures/fig1_supplier_loss_event_study.png")
fig.savefig(p,dpi=300); fig.savefig(p.replace('.png','.pdf'))
print("wrote",os.path.basename(p),flush=True)
for k in sorted(A): print(f"  t{k:+d}  sole {A[k][0]:+.3f}  minor {B[k][0]:+.3f}  ctrl {C[k][0]:+.3f}",flush=True)

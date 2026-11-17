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
first={}
for m,l,t,s in sorted(SLall,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
inwin={m:v for m,v in first.items() if LO<=v[0]<=HI}
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
COH=[m for m,(t,s,l) in inwin.items() if basec(m,t) is not None]
OBS=[m for m in COH if any(MQ[m].get(inwin[m][0]+k) is not None for k in range(1,7))]
ever={m for m,_,_,_ in SLall}; pool=[m for m in MQ if m not in ever]
rng=np.random.default_rng(2026); K=list(range(-6,7))
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
        db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
        ob=np.mean([oth(m,t+k,dl) for k in range(B0,B1)])
        if db<=0: continue
        for k in K: o[k].append((oth(m,t+k,dl)-ob)/db)
    return {k:(np.median(v),len(v)) for k,v in o.items()}
sole=[(m,inwin[m][0],inwin[m][2]) for m in OBS if inwin[m][1]>=.95]
minor=[(m,inwin[m][0],inwin[m][2]) for m in OBS if inwin[m][1]<.35]
mid=[(m,inwin[m][0],inwin[m][2]) for m in OBS if .35<=inwin[m][1]<.95]
ctl=[]
for m,t,dl in sole:
    bm=basec(m,t)
    cs=[c for c in pool if basec(c,t) and len(S.get((c,t-1),set()))==1 and bm/3<=basec(c,t)<=bm*3]
    if len(cs)>25: cs=list(rng.choice(cs,25,False))
    ctl+=[(c,t,None) for c in cs]
A=logpath(sole); Bm=logpath(minor); C=logpath(ctl)
Rs=rpath(sole); Rmid=rpath(mid); Rmin=rpath(minor)
# control replacement path, pseudo-departing labeler
def shares(c,t):
    labs=S.get((c,t-1),set()); sh={}; tot=0
    for l in labs:
        v=np.mean([LMQ.get((c,l),{}).get(t+k) or 0.0 for k in range(B0,B1)]); sh[l]=v; tot+=v
    return {l:(v/tot,v) for l,v in sh.items()} if tot>0 else {}
Rc={k:[] for k in K}
for m,t,dl in minor:
    tgt=inwin[m][1]; bm=basec(m,t); nb=len(S.get((m,t-1),set()))
    cs=[c for c in pool if basec(c,t) and len(S.get((c,t-1),set()))==nb and bm/2<=basec(c,t)<=bm*2]
    if len(cs)>8: cs=list(rng.choice(cs,8,False))
    for c in cs:
        sh=shares(c,t)
        if not sh: continue
        l=min(sh,key=lambda x:abs(sh[x][0]-tgt)); db=sh[l][1]
        if db<=0: continue
        ob=np.mean([oth(c,t+k,l) for k in range(B0,B1)])
        for k in K: Rc[k].append((oth(c,t+k,l)-ob)/db)
Rc={k:(np.median(v),len(v)) for k,v in Rc.items() if v}
fig,axes=plt.subplots(1,2,figsize=(10.6,4.2))
ax=axes[0]
for d,lab,col,mk in [(A,f"sole-labeler loss (n={A[0][2]})",'#b2182b','o'),
                     (Bm,f"minority-labeler loss (n={Bm[0][2]})",'#2166ac','s'),
                     (C,f"matched single-labeler, no loss (n={C[0][2]})",'#6e6e6e','^')]:
    ax.errorbar(K,[d[k][0] for k in K],yerr=[1.96*d[k][1] for k in K],label=lab,color=col,marker=mk,ms=3.6,lw=1.5,capsize=2)
ax.axvspan(B0-0.4,B1-0.6,color='#cccccc',alpha=.35,lw=0); ax.text((B0+B1-1)/2,0.75,"baseline",ha='center',fontsize=7,color='#555')
ax.axvline(-0.5,color='k',ls='--',lw=1,alpha=.7); ax.axhline(0,color='k',lw=.7,alpha=.4)
ax.set_xlabel("quarters relative to supplier loss"); ax.set_ylabel("change in log(1+prescriptions)")
ax.set_title("(a) Total market dispensing",fontsize=10); ax.legend(frameon=False,fontsize=7.2,loc='lower left'); ax.grid(alpha=.18); ax.set_xticks(K)
ax=axes[1]
for d,lab,col,mk,ls in [(Rmin,f"minority-labeler loss (n={Rmin[0][1]})",'#2166ac','s','-'),
                        (Rmid,f"35 to 95% (n={Rmid[0][1]})",'#4d9221','v','-'),
                        (Rs,f"sole-labeler loss (n={Rs[0][1]})",'#b2182b','o','-'),
                        (Rc,f"matched controls, pseudo-departing labeler (n={Rc[0][1]})",'#999999','d','--')]:
    ax.plot(K,[d[k][0] for k in K],label=lab,color=col,marker=mk,ms=3.4,lw=1.5,ls=ls)
ax.axhline(1.0,color='k',ls=':',lw=1,alpha=.6); ax.text(-5.8,1.04,"full replacement",fontsize=7,color='#444')
ax.axhline(0,color='k',lw=.7,alpha=.4); ax.axvline(-0.5,color='k',ls='--',lw=1,alpha=.7)
ax.set_xlabel("quarters relative to supplier loss"); ax.set_ylabel("median replacement ratio")
ax.set_title("(b) Volume taken up by remaining labelers,\nas a fraction of the departing labeler's volume",fontsize=9.5)
ax.legend(frameon=False,fontsize=6.8,loc='upper left'); ax.grid(alpha=.18); ax.set_xticks(K); ax.set_ylim(-0.3,1.8)
fig.tight_layout()
p=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/figures/fig1_supplier_loss_matched.pdf")
fig.savefig(p); fig.savefig(p.replace('.pdf','.png'),dpi=300)
print("figure n labels: sole",A[0][2],"minority",Bm[0][2],"controls",C[0][2],flush=True)
print("panel b n: minority",Rmin[0][1],"mid",Rmid[0][1],"sole",Rs[0][1],"control",Rc[0][1],flush=True)
print("control median R at t+6:",f"{Rc[6][0]:+.2f}",flush=True)

import duckdb, os, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:(x[2],x[0],x[1])):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def band(s): return "minority" if s<.35 else ("mid" if s<.95 else "sole")
LOr=YMIN-B0+2
COH=[(m,v[0],v[1]) for m,v in first.items() if v[0]>=LOr and v[0]+11<=TMAX and basec(m,v[0]) is not None and any(MQ[m].get(v[0]+k) is not None for k in range(1,13))]
def wil(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
K=list(range(1,13))
fig,axes=plt.subplots(1,2,figsize=(10.4,4.2))
# (a) cumulative share regained, conditional on having fallen below 50%
ax=axes[0]
for b,col,mk,lab in [("minority",'#2166ac','s',"minority-labeler loss"),("sole",'#b2182b','o',"sole-labeler loss")]:
    sel=[(m,t) for m,t,s in COH if band(s)==b]
    ys=[];lo=[];hi=[];ns=[]
    for H in K:
        ar=0;rc=0
        for m,t in sel:
            bl=basec(m,t)
            d=next((k for k in range(1,H+1) if (MQ[m].get(t+k) or 0)<0.5*bl),None)
            if d is None: continue
            ar+=1
            if any((MQ[m].get(t+k) or 0)>=0.5*bl for k in range(d+1,H+1)): rc+=1
        ys.append(rc/ar if ar else np.nan); c=wil(rc,ar); lo.append(c[0]); hi.append(c[1]); ns.append(ar)
    ax.plot(K,ys,color=col,marker=mk,ms=4,lw=1.6,label=f"{lab} (n at risk {ns[0]} to {ns[-1]})")
    ax.fill_between(K,lo,hi,color=col,alpha=.13,lw=0)
ax.set_xlabel("quarters since supplier loss"); ax.set_ylabel("share regaining 50% of baseline")
ax.set_title("(a) Recovery among markets that fell below 50%",fontsize=9.5)
ax.legend(frameon=False,fontsize=7.4,loc='upper left'); ax.grid(alpha=.18); ax.set_xticks(K); ax.set_ylim(0,1)
# (b) median cumulative deficit path
ax=axes[1]
for b,col,mk,lab in [("minority",'#2166ac','s',"minority-labeler loss"),
                     ("mid",'#4d9221','v',"35 to 95%"),("sole",'#b2182b','o',"sole-labeler loss")]:
    sel=[(m,t) for m,t,s in COH if band(s)==b]
    if not sel: continue
    ys=[]
    for H in range(0,12):
        v=[sum(max(basec(m,t)-(MQ[m].get(t+k) or 0.0),0) for k in range(0,H+1))/basec(m,t) for m,t in sel]
        ys.append(np.median(v))
    ax.plot(range(0,12),ys,color=col,marker=mk,ms=4,lw=1.6,label=f"{lab} (n={len(sel)})")
ax.axvline(3.5,color='k',ls='--',lw=1,alpha=.6)
ax.text(3.6,0.4,"detection window ends",fontsize=7,color='#444',rotation=90,va='bottom')
ax.set_xlabel("quarters since supplier loss"); ax.set_ylabel("median cumulative deficit\n(quarters of baseline volume)")
ax.set_title("(b) Accumulated unreplaced dispensing",fontsize=9.5)
ax.legend(frameon=False,fontsize=7.4,loc='upper left'); ax.grid(alpha=.18); ax.set_xticks(range(0,12))
fig.tight_layout()
p=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/figures/fig2_recovery.pdf")
fig.savefig(p); fig.savefig(p.replace('.pdf','.png'),dpi=300)
print("wrote",os.path.basename(p),flush=True)

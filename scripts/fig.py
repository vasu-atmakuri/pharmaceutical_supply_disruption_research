exec(open('rxonly.py').read().split('rng=np.random.default_rng(77)')[0])
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
bands=[(0,.35,"Minor supplier (<35% share)"),(.35,.95,"Intermediate (35-95%)"),(.95,1.01,"Sole supplier (>=95%)")]
ks=list(range(-6,9)); fig,ax=plt.subplots(figsize=(8,5))
for lo,hi,nm in bands:
    sel=[m for m,_,s in T if lo<=s<hi]; y=[];n0=0
    for k in ks:
        v=[np.log1p(MQ[m].get(TT[m][0]+k) or 0.0)-np.log1p(MQ[m][TT[m][0]-1]) for m in sel
           if MQ.get(m,{}).get(TT[m][0]-1,0)>0]
        y.append(np.mean(v) if v else np.nan); n0=len(v)
    ax.plot(ks,y,marker='o',ms=4,label=f"{nm}  (n={n0})")
ax.axvline(-0.5,ls='--',c='k',lw=1); ax.axhline(0,c='gray',lw=.6)
ax.set_xlabel("Quarters relative to manufacturer exit"); ax.set_ylabel("Change in log(1+prescriptions) vs quarter -1")
ax.set_title("Medicaid dispensing around abrupt manufacturer exit, by exiting firm's market share")
ax.annotate("exit",xy=(-0.5,ax.get_ylim()[0]*0.9),fontsize=9)
ax.legend(frameon=False,fontsize=9); ax.grid(alpha=.25); fig.tight_layout()
p=os.path.expanduser("~/mnt/Research/fig1_event_time_firm_exit.png"); fig.savefig(p,dpi=200)
print("wrote",p,flush=True)

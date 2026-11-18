import duckdb, numpy as np, json, os, collections, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':8.5,'axes.labelsize':8.5,'axes.titlesize':9.5,
 'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':7.6,'axes.linewidth':0.6,
 'xtick.major.width':0.6,'ytick.major.width':0.6})
BLUE,RED,GREEN='#2166ac','#b2182b','#4d9221'
ROOT=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
FIG, SPR, RES = f"{ROOT}/figures", f"{ROOT}/springer", f"{ROOT}/results"
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
def load(tag):
    MQ={}; LM={}
    for m,t,r in con.execute(f"SELECT mol,tq,rx FROM read_parquet('/tmp/molq_{tag}.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
    for l,m,t,r in con.execute(f"SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_{tag}.parquet')").fetchall(): LM.setdefault((m,t),{})[l]=r
    SL=con.execute(f"SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_{tag}.parquet')").fetchall()
    return MQ,LM,SL
MQn,LMn,SLn=load('norm'); MQr,LMr,SLr=load('nat')
nmap=json.load(open(f"{RES}/market_key_normalization_map.json"))
VER={}

# ================= FIGURE 1: the measurement defect =================
cases=[("Pregabalin, capsule","PREGABALIN CAPSULES, CV | CAPSULE","69097",(2024-1991)*4+2),
       ("Mixed amphetamine salts, tablet",None,"42858",(2023-1991)*4+2),
       ("Terbinafine, tablet","TERBINAFINE TABLETS 250 MG | TABLET","69097",(2023-1991)*4+4)]
rows=[]
for nm,rawkey,lab,t in cases:
    if rawkey is None:
        cands=[k for k in MQr if k.startswith("DEXTROAMPHETAMINE SACCHARATE, AMPHETAMINE ASPARTATE MONOHYDRATE")]
        rawkey=max(cands,key=lambda k:(LMr.get((k,t-1),{}).get(lab) or 0))
    nkey=nmap[rawkey]
    dr=LMr.get((rawkey,t-1),{}); dn=LMn.get((nkey,t-1),{})
    sr=(dr.get(lab) or 0)/max(1e-9,sum(v or 0 for v in dr.values()))
    sn=(dn.get(lab) or 0)/max(1e-9,sum(v or 0 for v in dn.values()))
    rows.append((nm,sr,sn,len(dr),len(dn)))
    print(f"  {nm}: raw {sr:.1%} of {len(dr)} labeler(s) -> normalized {sn:.1%} of {len(dn)}")
grp=collections.Counter()
for v in nmap.values(): grp[v]+=1
dist=collections.Counter(grp.values())
fig,ax=plt.subplots(1,2,figsize=(10.2,3.4))
y=np.arange(len(rows)); h=0.34; a=ax[0]
a.barh(y+h/2,[r[1] for r in rows],h,color=RED,label="raw ingredient string",edgecolor='white',linewidth=0.9)
a.barh(y-h/2,[r[2] for r in rows],h,color=BLUE,label="normalized market key",edgecolor='white',linewidth=0.9)
for i,(nm,sr,sn,lr,ln) in enumerate(rows):
    a.text(sr+.015,i+h/2,f"{sr:.0%} of {lr} labeler",va='center',fontsize=7.3,color='#333')
    a.text(max(sn,0)+.015,i-h/2,f"{sn:.0%} of {ln} labelers",va='center',fontsize=7.3,color='#333')
a.set_yticks(y); a.set_yticklabels([r[0] for r in rows],fontsize=7.9); a.set_xlim(0,1.45)
a.set_xticks([0,.25,.5,.75,1.0]); a.set_xticklabels(["0","25%","50%","75%","100%"])
a.set_xlabel("departing labeler's share in the quarter before exit")
a.set_title("(a) Three apparent sole-supplier exits, re-measured",loc='left')
a.legend(frameon=False,loc='lower right'); a.grid(axis='x',alpha=.18); a.set_axisbelow(True)
for s in ('top','right','left'): a.spines[s].set_visible(False)
b=ax[1]; ks=sorted(dist); vs=[dist[k] for k in ks]
b.bar([str(k) for k in ks],vs,color=BLUE,edgecolor='white',linewidth=0.9)
for i,v in enumerate(vs): b.text(i,v*1.15,f"{v:,}",ha='center',fontsize=7.3,color='#333')
b.set_yscale('log'); b.set_ylim(0.7,max(vs)*4)
b.set_xlabel("raw ingredient strings mapping to one normalized market key")
b.set_ylabel("number of normalized keys (log)")
b.set_title("(b) Duplicate market keys across the panel",loc='left')
b.grid(axis='y',alpha=.18); b.set_axisbelow(True)
for s in ('top','right'): b.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(f"{FIG}/fig1_measurement_defect.pdf"); fig.savefig(f"{FIG}/fig1_measurement_defect.png",dpi=300)
VER['fig1']=[f"{rows[0][2]:.0%} of {rows[0][4]} labelers", f"{dist[1]:,}"]

# ================= FIGURE 2: dispensing in event time, by band =================
TMAX=max(t for d in MQn.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
first={}
for m,l,t,s in sorted(SLn,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
def basec(m,t):
    p=[MQn[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
inwin={m:v for m,v in first.items() if LO<=v[0]<HI}
OBS=[m for m,v in inwin.items() if basec(m,v[0]) is not None and any(MQn[m].get(v[0]+k) is not None for k in range(1,7))]
band=lambda s:"minority" if s<.35 else ("mid" if s<.95 else "sole")
fig,ax=plt.subplots(1,2,figsize=(10.2,3.8))
K=list(range(-6,7)); a=ax[0]
for b,col,mk,lab in [("minority",BLUE,'s',"departing share under 35%"),("mid",GREEN,'v',"35 to 95%"),("sole",RED,'o',"at least 95%")]:
    sel=[m for m in OBS if band(inwin[m][1])==b]
    ys=[]
    for k in K:
        v=[(MQn[m].get(inwin[m][0]+k) or 0.0)/basec(m,inwin[m][0]) for m in sel]
        ys.append(np.median(v))
    a.plot(K,ys,color=col,marker=mk,ms=4.5,lw=2.0,label=f"{lab} (n={len(sel)})")
a.axvline(0,color='#444',ls='--',lw=0.9); a.axhline(1.0,color='#999',lw=0.6)
a.set_xlabel("quarters relative to labeler exit"); a.set_ylabel("market dispensing, share of baseline")
a.set_title("(a) Dispensing in event time",loc='left')
a.legend(frameon=False,loc='lower left'); a.grid(alpha=.18); a.set_xticks(K); a.set_axisbelow(True)
for s in ('top','right'): a.spines[s].set_visible(False)
def R(m):
    t,s,dl=inwin[m]
    LMQ={}
    db=np.mean([ (LMn.get((m,t+k),{}) or {}).get(dl) or 0.0 for k in range(B0,B1)])
    if db<=0: return None
    ob=np.mean([(MQn[m].get(t+k) or 0.0)-((LMn.get((m,t+k),{}) or {}).get(dl) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQn[m].get(t+k) or 0.0)-((LMn.get((m,t+k),{}) or {}).get(dl) or 0.0) for k in range(1,7)])
    return (op-ob)/db
b2=ax[1]
data=[];labs=[];cols=[]
for bnd,col,lab in [("minority",BLUE,"under 35%"),("mid",GREEN,"35 to 95%"),("sole",RED,"at least 95%")]:
    v=[R(m) for m in OBS if band(inwin[m][1])==bnd]
    v=[x for x in v if x is not None]
    data.append(np.clip(v,-0.5,3.0)); labs.append(f"{lab}\n(n={len(v)})"); cols.append(col)
    print(f"  fig2 band {bnd}: n={len(v)} median={np.median(v):.2f}")
bp=b2.boxplot(data,labels=labs,patch_artist=True,widths=.5,showfliers=False,medianprops=dict(color='#222',lw=1.6))
for p,c in zip(bp['boxes'],cols): p.set_facecolor(c); p.set_alpha(.45); p.set_edgecolor(c)
for i,(v,c) in enumerate(zip(data,cols)):
    x=np.random.default_rng(7).normal(i+1,0.055,len(v))
    b2.plot(x,v,'.',color=c,ms=3.4,alpha=.75)
b2.axhline(0,color='#444',lw=0.8,ls='--')
b2.set_ylabel("replacement ratio R"); b2.set_xlabel("departing labeler's pre-exit share")
b2.set_title("(b) Replacement by other labelers",loc='left')
b2.grid(axis='y',alpha=.18); b2.set_axisbelow(True)
for s in ('top','right'): b2.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(f"{FIG}/fig2_dispensing_and_replacement.pdf"); fig.savefig(f"{FIG}/fig2_dispensing_and_replacement.png",dpi=300)
VER['fig2']=[f"n={sum(1 for m in OBS if band(inwin[m][1])=='sole')}"]

# ================= FIGURE 3: recovery from first crossing, censored =================
RC=json.load(open(f"{RES}/recovery_censored.json"))
fig,ax=plt.subplots(1,2,figsize=(10.2,3.8))
for p,(thr,ttl) in enumerate([("50%","(a) Returning to half of baseline"),("90%","(b) Returning to 90% of baseline")]):
    a=ax[p]
    for key,col,mk,lab in [("minority_rows",BLUE,'s',"departing share under 35%"),("sole_rows",RED,'o',"at least 95%")]:
        rows=[tuple(r) for r in RC[thr][key]]
        n=len(rows); at=n; S=1.0; xs=[0]; ys=[1.0]; cens=[]
        for t in sorted(set(t for t,_ in rows)):
            d=sum(1 for tt,e in rows if tt==t and e==1); c=sum(1 for tt,e in rows if tt==t and e==0)
            if at>0 and d>0: S*=1-d/at
            xs.append(t); ys.append(S)
            if c>0: cens.append((t,S))
            at-=(d+c)
        a.step(xs,[1-v for v in ys],where='post',color=col,lw=2.0,label=f"{lab} (n={n})")
        if cens: a.plot([c[0] for c in cens],[1-c[1] for c in cens],marker='|',ls='none',ms=7,mew=1.4,color=col)
    z=RC[thr]["logrank_z"]; pv=RC[thr]["logrank_p"]
    a.text(.97,.06,f"log-rank p = {pv:.3f}",transform=a.transAxes,ha='right',fontsize=7.6,color='#333')
    a.set_xlabel("quarters since the market first fell below the threshold")
    a.set_ylabel("cumulative share restored"); a.set_ylim(0,1); a.set_xlim(0,11)
    a.set_title(ttl,loc='left'); a.legend(frameon=False,loc='upper left'); a.grid(alpha=.18); a.set_axisbelow(True)
    for s in ('top','right'): a.spines[s].set_visible(False)
    print(f"  fig3 {thr}: log-rank p={pv:.3f}")
fig.tight_layout(); fig.savefig(f"{FIG}/fig3_recovery_censored.pdf"); fig.savefig(f"{FIG}/fig3_recovery_censored.png",dpi=300)
VER['fig3']=[f"p = {RC['90%']['logrank_p']:.3f}"]
import shutil
for src,dst in [("fig1_measurement_defect","fig1"),("fig2_dispensing_and_replacement","fig2"),("fig3_recovery_censored","fig3")]:
    shutil.copyfile(f"{FIG}/{src}.pdf",f"{SPR}/{dst}.pdf")
json.dump(VER,open(f"{RES}/figure_assertions.json","w"),indent=2)
print("\nfigures built and copied into springer/; assertions written")

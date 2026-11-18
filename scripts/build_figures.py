import duckdb, numpy as np, json, os, collections, matplotlib
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':8.5,'axes.labelsize':8.5,'axes.titlesize':9.5,
 'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':7.6,'axes.linewidth':0.6,
 'xtick.major.width':0.6,'ytick.major.width':0.6})
BLUE,RED,GREEN='#2166ac','#b2182b','#4d9221'
ROOT=_ROOT+""
FIG, SPR, RES = f"{ROOT}/figures", f"{ROOT}/springer", f"{ROOT}/results"
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
def load(tag):
    MQ={}; LM={}
    for m,t,r in con.execute(f"SELECT mol,tq,rx FROM read_parquet('/tmp/molq_{tag}.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
    for l,m,t,r in con.execute(f"SELECT lab,mkt,tq,rx FROM read_parquet('/tmp/lmq_{tag}.parquet')").fetchall(): LM.setdefault((m,t),{})[l]=r
    SL=con.execute(f"SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_{tag}.parquet')").fetchall()
    return MQ,LM,SL
MQn,LMn,SLn=load('v2'); MQr,LMr,SLr=load('nat')
nmap=json.load(open(f"{RES}/market_key_normalization_map.json"))
VER={}

# ================= FIGURE 1: the measurement defect =================
import csv
TR=list(csv.DictReader(open(f"{RES}/sole_event_transition.csv")))
from display_names import name as _dname
# Panel (a) shows three of the reclassified exits. Both the label and the shares come
# from the same transition file the table is built from, and the label comes from the
# shared display map, so the figure cannot disagree with Table 2 about a dosage form.
_PICK_CORRECTED=["PREGABALIN | ORAL CAPSULE",
                 "DORZOLAMIDE,HYDROCHLORIDE,MALEATE,TIMOLOL | OPHTHALMIC",
                 "AMPHETAMINE,ASPARTATE,DEXTROAMPHETAMINE,SACCHARATE,SULFATE | ORAL CAPSULE"]
rows=[]
for want in _PICK_CORRECTED:
    r=next((x for x in TR if x["corrected_market"]==want), None)
    if r is None:
        raise SystemExit(f"figure 1(a): no transition row with corrected market {want!r}")
    rows.append((_dname(want),
                 float(r["raw_share"]), float(r["corrected_share"]),
                 int(r["raw_labelers"]), int(r["corrected_labelers"])))
    print(f"  {rows[-1][0]}: {rows[-1][1]:.0%} of {rows[-1][3]} -> {rows[-1][2]:.1%} of {rows[-1][4]}")
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
a.set_xlabel("departing labeler's share of the market, four-quarter baseline")
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
fig,ax=plt.subplots(2,2,figsize=(10.2,4.9),gridspec_kw={'height_ratios':[3.1,1]})
for p,(thr,ttl) in enumerate([("50%","(a) Returning to half of baseline"),
                              ("90%","(b) Returning to 90% of baseline")]):
    a1=ax[0][p]; a2=ax[1][p]; risk={}
    for key,col,lab in [("minority_rows",BLUE,"departing share under 35%"),
                        ("sole_rows",RED,"at least 95%")]:
        rows=[tuple(r) for r in RC[thr][key]]
        n=len(rows); at=n; S=1.0; V=0.0
        xs=[0]; ys=[1.0]; lo=[1.0]; hi=[1.0]; cens=[]; rk={0:n}
        for t in sorted(set(t for t,_ in rows)):
            d=sum(1 for tt,e in rows if tt==t and e==1)
            c=sum(1 for tt,e in rows if tt==t and e==0)
            if at>0 and d>0:
                S*=1-d/at
                V+=d/(at*(at-d)) if at>d else 0.0     # Greenwood
            se=S*np.sqrt(V) if V>0 else 0.0
            xs.append(t); ys.append(S)
            lo.append(max(0.0,S-1.96*se)); hi.append(min(1.0,S+1.96*se))
            if c>0: cens.append((t,S))
            at-=(d+c)
            if t>0: rk[t]=at          # time 0 keeps the full entering cohort, as is conventional
        F=[1-v for v in ys]
        a1.step(xs,F,where='post',color=col,lw=2.0,label=f"{lab} (n={n})")
        a1.fill_between(xs,[1-h for h in hi],[1-l for l in lo],step='post',color=col,alpha=.13,lw=0)
        if cens: a1.plot([c[0] for c in cens],[1-c[1] for c in cens],marker='|',ls='none',
                         ms=7,mew=1.4,color=col)
        risk[lab]=rk
    pv=RC[thr]["logrank_p"]
    a1.text(.97,.06,f"log-rank p = {pv:.3f}",transform=a1.transAxes,ha='right',fontsize=7.6,color='#333')
    a1.set_ylabel("cumulative share restored"); a1.set_ylim(0,1); a1.set_xlim(0,11)
    a1.set_title(ttl,loc='left'); a1.legend(frameon=False,loc='upper left')
    a1.grid(alpha=.18); a1.set_axisbelow(True); a1.set_xticklabels([])
    for sp in ('top','right'): a1.spines[sp].set_visible(False)
    # numbers at risk
    ticks=list(range(0,12,2))
    a2.set_xlim(-3.2,11); a2.set_ylim(0,2.4); a2.axis('off')
    a2.text(-3.1,1.75,"numbers at risk",fontsize=7,color='#444',ha='left')
    for i,(lab,rk) in enumerate(risk.items()):
        col=BLUE if 'under' in lab else RED
        y=1.15-0.65*i
        for t in ticks:
            v=max(rk.get(k,0) for k in rk if k<=t) if any(k<=t for k in rk) else 0
            keys=[k for k in sorted(rk) if k<=t]
            v=rk[keys[-1]] if keys else 0
            a2.text(t,y,str(v),fontsize=7,ha='center',color=col)
        a2.text(-3.1,y,("minority" if 'under' in lab else "sole"),fontsize=7,color=col,ha='left')
    for t in ticks: a2.text(t,0.05,str(t),fontsize=7.5,ha='center',color='#333')
    a2.text(5.5,-0.5,"quarters since the market first fell below the threshold",
            fontsize=8.5,ha='center',color='#333')
fig.tight_layout()
fig.savefig(f"{FIG}/fig3_recovery_censored.pdf"); fig.savefig(f"{FIG}/fig3_recovery_censored.png",dpi=300)
VER['fig3']=[f"p = {RC['90%']['logrank_p']:.3f}"]
print(f"  fig3 50%: p={RC['50%']['logrank_p']:.3f}   fig3 90%: p={RC['90%']['logrank_p']:.3f}  (bands + risk table)")
import shutil
for src,dst in [("fig1_measurement_defect","fig1"),("fig2_dispensing_and_replacement","fig2"),("fig3_recovery_censored","fig3")]:
    shutil.copyfile(f"{FIG}/{src}.pdf",f"{SPR}/{dst}.pdf")
json.dump(VER,open(f"{RES}/figure_assertions.json","w"),indent=2)
print("\nfigures built and copied into springer/; assertions written")

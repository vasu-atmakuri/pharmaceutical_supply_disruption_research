import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
LMQ={}
for m,l,t,r in con.execute("SELECT mkt,lab,tq,rx FROM read_parquet('/tmp/lmq_nat.parquet')").fetchall(): LMQ.setdefault((m,l),{})[t]=r
S={}
for (m,l),d in LMQ.items():
    for t,v in d.items():
        if v and v>0: S.setdefault((m,t),set()).add(l)
FRM={r[0]:r[1] for r in con.execute("SELECT mol,frm FROM read_parquet('/tmp/meta_nat.parquet')").fetchall()}
GEN={r[0] for r in con.execute("SELECT DISTINCT lpad(lab,5,'0') FROM read_parquet('/tmp/xcat.parquet') WHERE mktcat IN ('ANDA','NDA AUTHORIZED GENERIC')").fetchall()}
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SLall=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SLall,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)          # RULE: first detected event per market, ever
inwin={m:v for m,v in first.items() if LO<=v[0]<=HI}
def basec(m,t): 
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def postobs(m,t): return any(MQ[m].get(t+k) is not None for k in range(1,7))
def post(m,t): return float(np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)]))
COH=[m for m,(t,s,l) in inwin.items() if basec(m,t) is not None]      # baseline complete
OBS=[m for m in COH if postobs(m,inwin[m][0])]                        # at least one post quarter
NOP=[m for m in COH if m not in OBS]
print(f"cohort with complete baseline: {len(COH)}   with post obs: {len(OBS)}   no post obs: {len(NOP)}",flush=True)
def wil(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
BANDS=[(0,.35,"under 35%"),(.35,.65,"35 to 65%"),(.65,.95,"65 to 95%"),(.95,1.01,"95% or above")]
print("\n=== THE 8 DROPPED SOLE EVENTS: what were they? ===",flush=True)
for m in sorted(NOP,key=lambda x:-basec(x,inwin[x][0])):
    t,s,l=inwin[m]; print(f"  {m[:48]:<50} band {s:.2f}  baseline {basec(m,t):>9,.0f} rx/qtr  {1991+(t-1)//4}Q{(t-1)%4+1}",flush=True)
print("\n=== MAIN OUTCOME AS BOUNDS ===",flush=True)
print("  Lower bound drops events with no observed post quarter (as before).",flush=True)
print("  Upper bound counts them as below threshold, since no observable dispensing remains.",flush=True)
print(f"\n  {'band':<14}{'n obs':>7}{'k':>4}{'lower':>8}{'95% CI':>18}  |{'n all':>7}{'k':>4}{'upper':>8}{'95% CI':>18}",flush=True)
T={}
for lo,hi,nm in BANDS:
    o=[m for m in OBS if lo<=inwin[m][1]<hi]; a=[m for m in COH if lo<=inwin[m][1]<hi]
    k=sum(1 for m in o if post(m,inwin[m][0])<=0.02*basec(m,inwin[m][0]))
    k2=k+len([m for m in a if m not in o])
    c1=wil(k,len(o)); c2=wil(k2,len(a))
    T[nm]=dict(n_obs=len(o),k=k,lower=k/len(o) if o else 0,ci_l=list(c1),
               n_all=len(a),k_all=k2,upper=k2/len(a) if a else 0,ci_u=list(c2))
    print(f"  {nm:<14}{len(o):>7}{k:>4}{k/len(o) if o else 0:>8.1%}   [{c1[0]:>5.1%},{c1[1]:>6.1%}]  |"
          f"{len(a):>7}{k2:>4}{k2/len(a) if a else 0:>8.1%}   [{c2[0]:>5.1%},{c2[1]:>6.1%}]",flush=True)
# ---- replacement ratio with bootstrap CIs and control adjustment
def R(m,t,dl):
    db=np.mean([LMQ.get((m,dl),{}).get(t+k) or 0.0 for k in range(B0,B1)])
    ob=np.mean([(MQ[m][t+k] or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQ[m].get(t+k) or 0.0)-(LMQ.get((m,dl),{}).get(t+k) or 0.0) for k in range(1,7)])
    return None if db<=0 else (op-ob)/db
def boot_med(x,B=20000,rng=None):
    rng=rng or np.random.default_rng(11); x=np.asarray(x)
    s=[np.median(rng.choice(x,size=len(x),replace=True)) for _ in range(B)]
    return float(np.median(x)),float(np.percentile(s,2.5)),float(np.percentile(s,97.5))
print("\n=== REPLACEMENT RATIO with bootstrap 95% CI on the median (20,000 resamples) ===",flush=True)
print(f"  {'band':<14}{'n':>4}{'median R':>10}{'95% CI':>22}{'mean':>9}{'IQR':>18}",flush=True)
RR={}; store={}
rng=np.random.default_rng(11)
for lo,hi,nm in BANDS:
    v=[R(m,inwin[m][0],inwin[m][2]) for m in OBS if lo<=inwin[m][1]<hi]
    v=[x for x in v if x is not None]
    if len(v)<3: continue
    store[nm]=v; med,l,u=boot_med(v,rng=rng)
    q1,q3=np.percentile(v,[25,75])
    RR[nm]=dict(n=len(v),median=med,ci=[l,u],mean=float(np.mean(v)),iqr=[float(q1),float(q3)])
    print(f"  {nm:<14}{len(v):>4}{med:>10.2f}   [{l:>6.2f}, {u:>6.2f}]{np.mean(v):>9.2f}   [{q1:>6.2f}, {q3:>6.2f}]",flush=True)
a=np.array(store["under 35%"]); b=np.array(store["95% or above"])
d=[]
for _ in range(20000):
    d.append(np.median(rng.choice(a,len(a),True))-np.median(rng.choice(b,len(b),True)))
d=np.array(d)
print(f"\n  difference in medians, minority minus sole: {np.median(a)-np.median(b):.2f}  "
      f"95% CI [{np.percentile(d,2.5):.2f}, {np.percentile(d,97.5):.2f}]",flush=True)
print(f"  bootstrap share of draws with difference <= 0: {(d<=0).mean():.5f}",flush=True)
print("\n=== EVENT-LEVEL DISTRIBUTION, sole band ===",flush=True)
sv=store["95% or above"]
print(f"  n={len(sv)}   exactly 0.00: {sum(1 for x in sv if abs(x)<1e-9)}   >0: {sum(1 for x in sv if x>1e-9)}   <0: {sum(1 for x in sv if x<-1e-9)}",flush=True)
print(f"  values: {', '.join(f'{x:.2f}' for x in sorted(sv))}",flush=True)
pos=[x for x in sv if x>1e-9]
if pos: print(f"  among markets receiving any replacement (n={len(pos)}): median {np.median(pos):.2f}, max {max(pos):.2f}",flush=True)
print("\n=== CONTROL-ADJUSTED: what do 'other labelers' do in matched never-exposed markets? ===",flush=True)
ever={m for m,_,_,_ in SLall}; pool=[m for m in MQ if m not in ever]
ctlR=[]
for m in [x for x in OBS if inwin[x][1]<.35]:
    t=inwin[m][0]; nb=len(S.get((m,t-1),set())); vb=basec(m,t)
    cs=[c for c in pool if basec(c,t) and len(S.get((c,t-1),set()))==nb and FRM.get(c)==FRM.get(m)
        and vb/2<=basec(c,t)<=vb*2]
    if len(cs)>10: cs=list(rng.choice(cs,10,False))
    for c in cs:
        db=np.mean([LMQ.get((m,inwin[m][2]),{}).get(t+k) or 0.0 for k in range(B0,B1)])
        if db<=0: continue
        ctlR.append((np.mean([MQ[c].get(t+k) or 0.0 for k in range(1,7)])-basec(c,t))/db)
if ctlR:
    m_,l_,u_=boot_med(ctlR,rng=rng)
    print(f"  counterfactual drift in matched controls, same denominator: median {m_:.2f}  95% CI [{l_:.2f}, {u_:.2f}]  (n={len(ctlR)})",flush=True)
print("\n=== SOLE BAND: safety-withdrawal and generic subsets ===",flush=True)
import json as js
rec=js.load(open(os.path.expanduser("~/mnt/Research/enforcement/drug-enforcement-0001-of-0001.json"),encoding='utf-8',errors='replace'))['results']
RC=[]
for r in rec:
    rd=str(r.get('recall_initiation_date') or r.get('report_date') or '')
    if len(rd)!=8: continue
    RC.append(((int(rd[:4])-1991)*4+((int(rd[4:6])-1)//3+1),((r.get('product_description') or '')+' '+(r.get('reason_for_recall') or '')).upper()))
def flagged(m,t):
    key=m.split('|')[0].strip().split()[0][:12]
    return len(key)>=5 and any(abs(tq-t)<=4 and key in tx for tq,tx in RC)
sole=[m for m in OBS if inwin[m][1]>=.95]
fl=[m for m in sole if flagged(m,inwin[m][0])]; nf=[m for m in sole if m not in fl]
gen=[m for m in sole if inwin[m][2].zfill(5) in GEN]; ngen=[m for m in sole if m not in gen]
for nm,g in [("all sole",sole),("recall-flagged",fl),("NOT recall-flagged",nf),("ANDA/auth-generic labeler",gen),("other labeler",ngen)]:
    if len(g)<2: print(f"  {nm:<28} n={len(g)}  too few",flush=True); continue
    k=sum(1 for m in g if post(m,inwin[m][0])<=0.02*basec(m,inwin[m][0]))
    v=[R(m,inwin[m][0],inwin[m][2]) for m in g]; v=[x for x in v if x is not None]
    print(f"  {nm:<28} n={len(g):>3}  below 2%: {k/len(g):>5.1%}   median R: {np.median(v):.2f}",flush=True)
print("\n=== LEAVE-ONE-OUT, sole band below-2% rate ===",flush=True)
rates=[]
for i in range(len(sole)):
    g=[m for j,m in enumerate(sole) if j!=i]
    rates.append(sum(1 for m in g if post(m,inwin[m][0])<=0.02*basec(m,inwin[m][0]))/len(g))
print(f"  range {min(rates):.1%} to {max(rates):.1%}  (full sample {sum(1 for m in sole if post(m,inwin[m][0])<=0.02*basec(m,inwin[m][0]))/len(sole):.1%})",flush=True)
json.dump(dict(bounds=T,replacement=RR,cohort=dict(baseline=len(COH),obs=len(OBS),nopost=len(NOP))),
  open(os.path.expanduser("~/mnt/Research/RESULTS_round2.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_round2.json",flush=True)

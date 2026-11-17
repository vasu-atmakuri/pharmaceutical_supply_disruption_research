import duckdb, os, numpy as np, json, glob
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'"); con.execute("SET threads=4")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
LMQ={}
for m,l,t,r in con.execute("SELECT mkt,lab,tq,rx FROM read_parquet('/tmp/lmq_nat.parquet')").fetchall(): LMQ.setdefault((m,l),{})[t]=r
S={}
for (m,l),d in LMQ.items():
    for t,v in d.items():
        if v and v>0: S.setdefault((m,t),set()).add(l)
FRM={r[0]:r[1] for r in con.execute("SELECT mol,frm FROM read_parquet('/tmp/meta_nat.parquet')").fetchall()}
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SLall=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
print("=== P0.1  285 vs 218 ===",flush=True)
print(f"  raw detector rows (labeler-market events): {len(SLall)}",flush=True)
print(f"  distinct markets with >=1 event:           {len({m for m,_,_,_ in SLall})}",flush=True)
first={}
for m,l,t,s in sorted(SLall,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
print(f"  first event per market:                    {len(first)}",flush=True)
def band(s): return "under 35%" if s<.35 else ("35 to 65%" if s<.65 else ("65 to 95%" if s<.95 else "95% or above"))
import collections
be=collections.Counter(band(s) for _,_,_,s in SLall)
bm=collections.Counter(band(v[1]) for v in first.values())
print(f"\n  {'band':<16}{'raw events':>12}{'markets (first)':>18}",flush=True)
for b in ["under 35%","35 to 65%","65 to 95%","95% or above"]:
    print(f"  {b:<16}{be[b]:>12}{bm[b]:>18}",flush=True)
print(f"  {'TOTAL':<16}{sum(be.values()):>12}{sum(bm.values()):>18}",flush=True)
print("  => 285 counts labeler-market events; 218 counts markets at their first event.",flush=True)
inwin={m:v for m,v in first.items() if LO<=v[0]<=HI}
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
def post(m,t): return float(np.mean([MQ[m].get(t+k) or 0.0 for k in range(1,7)]))
COH=[m for m,(t,s,l) in inwin.items() if basec(m,t) is not None]
OBS=[m for m in COH if any(MQ[m].get(inwin[m][0]+k) is not None for k in range(1,7))]
def wil(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
print("\n=== P0.2  CORRECTED BOUNDS (common denominator) ===",flush=True)
print(f"  {'band':<16}{'all':>5}{'obs':>5}{'k':>4}{'complete-case':>16}{'LOWER k/all':>14}{'UPPER':>12}",flush=True)
BND={}
for b in ["under 35%","35 to 65%","65 to 95%","95% or above"]:
    allm=[m for m in COH if band(inwin[m][1])==b]
    obs=[m for m in allm if m in OBS]; miss=len(allm)-len(obs)
    k=sum(1 for m in obs if post(m,inwin[m][0])<=0.02*basec(m,inwin[m][0]))
    cc=k/len(obs) if obs else 0; lo=k/len(allm); up=(k+miss)/len(allm)
    c0=wil(k,len(obs)); c1=wil(k,len(allm)); c2=wil(k+miss,len(allm))
    BND[b]=dict(n_all=len(allm),n_obs=len(obs),k=k,missing=miss,complete=cc,lower=lo,upper=up,
                ci_cc=list(c0),ci_lo=list(c1),ci_up=list(c2))
    print(f"  {b:<16}{len(allm):>5}{len(obs):>5}{k:>4}{cc:>15.1%}{lo:>14.1%}{up:>12.1%}",flush=True)
print("  (45.0% is the complete-case rate among evaluable events, NOT a bound on all 28)",flush=True)
print("\n=== P0.3  EVENT-LEVEL SUPPRESSION SENSITIVITY ===",flush=True)
px=sorted(glob.glob(os.path.expanduser("~/work/partsxx/*.parquet")))
con.execute("""CREATE OR REPLACE MACRO fb(f) AS CASE WHEN f IS NULL THEN 'UNK'
 WHEN f LIKE '%INJECT%' OR f LIKE '%INFUSION%' THEN 'INJECTABLE' WHEN f LIKE '%TABLET%' THEN 'TABLET'
 WHEN f LIKE '%CAPSULE%' THEN 'CAPSULE'
 WHEN f LIKE '%SOLUTION%' OR f LIKE '%SUSPENSION%' OR f LIKE '%SYRUP%' OR f LIKE '%ELIXIR%' OR f LIKE '%LIQUID%' THEN 'ORAL LIQUID'
 WHEN f LIKE '%CREAM%' OR f LIKE '%OINTMENT%' OR f LIKE '%GEL%' OR f LIKE '%LOTION%' OR f LIKE '%PATCH%' OR f LIKE '%FILM%' THEN 'TOPICAL'
 WHEN f LIKE '%AEROSOL%' OR f LIKE '%INHAL%' OR f LIKE '%POWDER, METERED%' OR f LIKE '%SPRAY%' THEN 'INHALED/SPRAY'
 WHEN f LIKE '%SUPPOSITORY%' OR f LIKE '%ENEMA%' THEN 'RECTAL'
 WHEN f LIKE '%OPHTH%' OR f LIKE '%DROP%' THEN 'DROPS' ELSE 'OTHER' END""")
con.execute(f"""CREATE OR REPLACE TABLE ms AS SELECT xw.generic||' | '||fb(xw.form) mol,
 (n.yr-1991)*4+n.qtr tq, SUM(n.nsupp) nsupp FROM read_parquet({px!r}) n
 JOIN read_parquet('/tmp/xw.parquet') xw ON xw.lab=lpad(n.lab,5,'0') AND xw.pcode=lpad(n.pcode,4,'0')
 JOIN read_parquet('/tmp/ptype.parquet') pt ON pt.lab=lpad(n.lab,5,'0') AND pt.pcode=lpad(n.pcode,4,'0')
 WHERE xw.generic<>'' AND pt.ptype='HUMAN PRESCRIPTION DRUG' GROUP BY 1,2""")
SUP={}
for m,t,ns in con.execute("SELECT mol,tq,nsupp FROM ms").fetchall(): SUP.setdefault(m,{})[t]=ns or 0
flip=0; rows=[]
for m in [x for x in OBS if inwin[x][1]>=.95]:
    t=inwin[m][0]; b=basec(m,t); p=post(m,t)
    hid=10*np.mean([SUP.get(m,{}).get(t+k,0) for k in range(1,7)])
    below=p<=0.02*b; below_worst=(p+hid)<=0.02*b
    if below!=below_worst: flip+=1
    rows.append((m,b,p,hid,below,below_worst))
print(f"  sole-supplier events tested: {len(rows)}",flush=True)
print(f"  classification changes when every suppressed record is set to its 10-rx maximum: {flip}",flush=True)
worst=sorted(rows,key=lambda r:-(r[3]/max(r[1],1)))[:5]
print(f"  {'market':<40}{'base':>9}{'post':>8}{'max hidden':>12}{'thresh':>9}",flush=True)
for m,b,p,h,x,y in worst:
    print(f"  {m[:38]:<40}{b:>9,.0f}{p:>8,.0f}{h:>12,.0f}{0.02*b:>9,.0f}",flush=True)
print("\n=== P0.4  CONTROL REPLACEMENT RATIO, correctly constructed ===",flush=True)
print("  pseudo-departing labeler = the control market's labeler whose t-1 share is closest",flush=True)
print("  to the treated market's departing share; ratio computed entirely within the control.\n",flush=True)
ever={m for m,_,_,_ in SLall}; pool=[m for m in MQ if m not in ever]
rng=np.random.default_rng(99)
def shares(c,t):
    labs=S.get((c,t-1),set()); tot=0; sh={}
    for l in labs:
        v=np.mean([LMQ.get((c,l),{}).get(t+k) or 0.0 for k in range(B0,B1)]); sh[l]=v; tot+=v
    return {l:(v/tot if tot>0 else 0,v) for l,v in sh.items()} if tot>0 else {}
def Rctl(c,t,target):
    sh=shares(c,t)
    if not sh: return None
    l=min(sh,key=lambda x:abs(sh[x][0]-target))
    db=sh[l][1]
    if db<=0: return None
    ob=np.mean([(MQ[c].get(t+k) or 0.0)-(LMQ.get((c,l),{}).get(t+k) or 0.0) for k in range(B0,B1)])
    op=np.mean([(MQ[c].get(t+k) or 0.0)-(LMQ.get((c,l),{}).get(t+k) or 0.0) for k in range(1,7)])
    return (op-ob)/db
def boot_med(x,B=20000,r=None):
    r=r or np.random.default_rng(4); x=np.asarray(x)
    s=[np.median(r.choice(x,len(x),True)) for _ in range(B)]
    return float(np.median(x)),float(np.percentile(s,2.5)),float(np.percentile(s,97.5))
OUTC={}
for b in ["under 35%","95% or above"]:
    vals=[]; uniq=set()
    for m in [x for x in OBS if band(inwin[x][1])==b]:
        t=inwin[m][0]; nb=len(S.get((m,t-1),set())); vb=basec(m,t); tgt=inwin[m][1]
        cs=[c for c in pool if basec(c,t) and len(S.get((c,t-1),set()))==nb and FRM.get(c)==FRM.get(m)
            and vb/2<=basec(c,t)<=vb*2]
        if len(cs)>10: cs=list(rng.choice(cs,10,False))
        for c in cs:
            r=Rctl(c,t,tgt)
            if r is not None: vals.append(r); uniq.add(c)
    if len(vals)<5: print(f"  {b:<16} too few",flush=True); continue
    md,l,u=boot_med(vals,r=rng)
    OUTC[b]=dict(n_obs=len(vals),n_unique=len(uniq),median=md,ci=[l,u])
    print(f"  {b:<16} control median R = {md:+.2f}  95% CI [{l:+.2f}, {u:+.2f}]   "
          f"({len(vals)} observations, {len(uniq)} unique markets)",flush=True)
print("\n=== P1  UNIQUE CONTROL MARKETS behind the 500 matched observations ===",flush=True)
sole=[m for m in OBS if inwin[m][1]>=.95]; uq=set(); nobs=0
for m in sole:
    t=inwin[m][0]; bm=basec(m,t)
    cs=[c for c in pool if basec(c,t) and len(S.get((c,t-1),set()))==1 and bm/3<=basec(c,t)<=bm*3]
    if len(cs)>25: cs=list(rng.choice(cs,25,False))
    uq|=set(cs); nobs+=len(cs)
print(f"  matched observations {nobs}   unique control markets {len(uq)}   mean reuse {nobs/max(len(uq),1):.2f}x",flush=True)
print("\n=== P1  EXACT ONE-LABELER SUBSET vs >=95% SHARE ===",flush=True)
one=[m for m in OBS if inwin[m][1]>=.95 and len(S.get((m,inwin[m][0]-1),set()))==1]
more=[m for m in OBS if inwin[m][1]>=.95 and len(S.get((m,inwin[m][0]-1),set()))>1]
for nm,g in [("exactly one labeler",one),("95%+ share, 2+ labelers",more)]:
    if not g: print(f"  {nm:<26} n=0",flush=True); continue
    k=sum(1 for m in g if post(m,inwin[m][0])<=0.02*basec(m,inwin[m][0]))
    print(f"  {nm:<26} n={len(g):>3}   below 2%: {k}/{len(g)} = {k/len(g):.1%}",flush=True)
json.dump(dict(bounds=BND,control_R=OUTC,supp_flips=flip,
               unique_controls=len(uq),matched_obs=nobs,
               exact_one=len(one),ge95_multi=len(more)),
  open(os.path.expanduser("~/mnt/Research/RESULTS_round3.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_round3.json",flush=True)

import duckdb, os, numpy as np, json
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ={}
for m,t,v in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_mf.parquet')").fetchall(): MQ.setdefault(m,{})[t]=v
META={r[0]:(r[1],r[2],r[3]) for r in con.execute("SELECT mol,gen,frm,epc FROM read_parquet('/tmp/mktmeta.parquet')").fetchall()}
S={}
for m,l,t in con.execute("SELECT mol,lab,tq FROM read_parquet('/tmp/lmq_mf.parquet') WHERE rx>0").fetchall(): S.setdefault((m,t),set()).add(l)
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; LO,HI=YMIN+8,TMAX-6
SL=[(m,t,s) for m,t,s in con.execute("SELECT mol,t,shr FROM read_parquet('/tmp/sl_mf.parquet')").fetchall() if LO<=t<=HI]
first={}
for m,t,s in sorted(SL,key=lambda x:x[1]):
    if m not in first: first[m]=(t,s)
# SAFETY-WITHDRAWAL SCREEN: ingredient appears in FDA recall text within +/-4 quarters of the event
import json as js
rec=js.load(open(os.path.expanduser("~/mnt/Research/enforcement/drug-enforcement-0001-of-0001.json"),encoding='utf-8',errors='replace'))['results']
RC=[]
for r in rec:
    rd=str(r.get('recall_initiation_date') or r.get('report_date') or '')
    if len(rd)!=8: continue
    yr,mo=int(rd[:4]),int(rd[4:6]); tq=(yr-1991)*4+((mo-1)//3+1)
    txt=((r.get('product_description') or '')+' '+(r.get('reason_for_recall') or '')).upper()
    RC.append((tq,txt,r.get('classification') or ''))
def recalled(gen,t):
    key=gen.split()[0][:12]
    if len(key)<5: return False
    for tq,txt,cls in RC:
        if abs(tq-t)<=4 and key in txt: return True
    return False
sole=[m for m in first if first[m][1]>=.95]
flagged=[m for m in sole if recalled(META[m][0],first[m][0])]
print(f"sole-supplier markets: {len(sole)}",flush=True)
print(f"flagged as safety/recall-contemporaneous: {len(flagged)}",flush=True)
print("  flagged:", ", ".join(META[m][0][:24] for m in flagged[:14]),flush=True)
clean=[m for m in sole if m not in flagged]
print(f"CLEAN sole-supplier markets (genuine supply failure): {len(clean)}",flush=True)
treated=set(first)
ctl=[m for m in MQ if m not in treated and len([t for t in MQ[m] if MQ[m][t] and MQ[m][t]>0 and t>=YMIN])>=34
     and np.mean([v for v in MQ[m].values() if v])>=400]
rng=np.random.default_rng(23); td=[first[m][0] for m in sole]
def feat(sel,getT):
    z=[];l=[]
    for m in sel:
        t=getT(m); s=MQ.get(m,{})
        if not (LO<=t<=HI): continue
        pre=[s.get(t+k) for k in range(-8,-4)]
        if any(v is None or v<=0 for v in pre): continue
        post=[s.get(t+k) for k in range(1,7)]
        if all(v is None for v in post): continue
        post=[0.0 if v is None else v for v in post]
        z.append(1.0 if np.mean(post)<=0.02*np.mean(pre) else 0.0); l.append(np.mean(np.log1p(post))-np.mean(np.log1p(pre)))
    return np.array(z),np.array(l)
cz,cl=feat(ctl,lambda m:int(rng.choice(td)))
print(f"\n  group                        n   collapse  ctrl    change      p",flush=True)
out={}
for nm,sel in [("all sole-supplier",sole),("CLEAN (recall excluded)",clean),("flagged safety/recall",flagged),
               ("minor <35% (placebo)",[m for m in first if first[m][1]<.35])]:
    z,l=feat(sel,lambda m:first[m][0])
    if len(l)<3: print(f"  {nm:<26}{len(l):>4}   too few",flush=True); continue
    d=l.mean()-cl.mean(); ph=[]
    for _ in range(600):
        s2=list(rng.choice(ctl,size=min(max(len(l),30),len(ctl)),replace=False))
        _,b=feat(s2,lambda m:int(rng.choice(td)))
        if len(b)>5: ph.append(b.mean()-cl.mean())
    ph=np.array(ph); p=(np.sum(np.abs(ph)>=abs(d))+1)/(len(ph)+1)
    out[nm]=dict(n=int(len(l)),collapse=float(z.mean()),pct=float(100*(np.exp(d)-1)),p=float(p))
    print(f"  {nm:<26}{len(l):>4}    {z.mean():>5.1%} {cz.mean():>5.1%}  {100*(np.exp(d)-1):>+7.1f}%   {p:.4f}",flush=True)
print("\n=== CLEAN sole-supplier markets, by volume ===",flush=True)
rows=[]
for m in clean:
    t=first[m][0]; pv=[MQ[m].get(t+k) for k in range(-8,-4)]
    if any(v is None for v in pv): continue
    rows.append((META[m][0][:36],META[m][1],f"{1991+(t-1)//4}Q{(t-1)%4+1}",np.mean(pv),
                 np.mean([MQ[m].get(t+k) or 0 for k in range(1,7)]),len(S.get((m,t+6),set()))))
rows.sort(key=lambda r:-r[3])
print(f"  {'ingredient':<38}{'form':<14}{'event':<8}{'before':>9}{'after':>9}{'sup after':>10}",flush=True)
for r in rows: print(f"  {r[0]:<38}{r[1]:<14}{r[2]:<8}{r[3]:>9,.0f}{r[4]:>9,.0f}{r[5]:>10}",flush=True)
print(f"\n  total: {sum(r[3] for r in rows):,.0f} rx/qtr across {len(rows)} markets",flush=True)
json.dump(dict(sole=len(sole),flagged=len(flagged),clean=len(clean),results=out),
  open(os.path.expanduser("~/mnt/Research/firm_exit_FINAL_clean.json"),'w'),indent=2)
print("\nwrote Research/firm_exit_FINAL_clean.json",flush=True)

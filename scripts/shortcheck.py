import json, os, duckdb, numpy as np, re, collections
S=json.load(open(os.path.expanduser("~/mnt/Research/aux/shortages_all.json"),encoding='utf-8',errors='replace'))['results']
print(f"shortage records: {len(S)}",flush=True)
def q(d):
    if not d or '/' not in str(d): return None
    m,dd,y=str(d).split('/')
    try: return (int(y)-1991)*4+((int(m)-1)//3+1)
    except: return None
SH=[]
for x in S:
    g=(x.get('generic_name') or '').upper().strip()
    t=q(x.get('initial_posting_date'))
    if g and t: SH.append((g,t,x.get('status'),(x.get('dosage_form') or '').upper()))
print(f"usable (generic + posting date): {len(SH)}",flush=True)
IDX=collections.defaultdict(list)
for g,t,st,df in SH:
    key=re.split(r'[ ,;(]',g)[0][:14]
    if len(key)>=5: IDX[key].append((t,st,g,df))
con=duckdb.connect(); con.execute("SET memory_limit='1200MB'")
MQ={}
for m,t,r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall(): MQ.setdefault(m,{})[t]=r
TMAX=max(t for d in MQ.values() for t in d); YMIN=(2016-1991)*4+1; B0,B1=-6,-2; LO,HI=YMIN-B0+2,TMAX-6
SL=con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first={}
for m,l,t,s in sorted(SL,key=lambda x:x[2]):
    if m not in first: first[m]=(t,s,l)
inwin={m:v for m,v in first.items() if LO<=v[0]<=HI}
def basec(m,t):
    p=[MQ[m].get(t+k) for k in range(B0,B1)]
    return None if any(v is None or v<=0 for v in p) else float(np.mean(p))
COH=[m for m,(t,s,l) in inwin.items() if basec(m,t) is not None]
def match(m,t,win=8):
    ing=m.split('|')[0].strip().upper()
    key=re.split(r'[ ,;(]',ing)[0][:14]
    if len(key)<5: return None
    best=None
    for st_,status,g,df in IDX.get(key,[]):
        if abs(st_-t)<=win:
            if best is None or abs(st_-t)<abs(best[0]-t): best=(st_,status,g)
    return best
print("\n=== DO DETECTED SUPPLIER LOSSES APPEAR IN THE FDA SHORTAGE REGISTER? ===",flush=True)
print("   match = same ingredient, shortage first posted within 8 quarters of the event",flush=True)
print("   NOTE one-sided: resolved shortages are purged after 6 months, so absence is uninformative\n",flush=True)
print(f"  {'band':<16}{'n':>5}{'matched':>9}{'rate':>8}",flush=True)
OUT={}
for lo,hi,nm in [(0,.35,"under 35%"),(.35,.95,"35 to 95%"),(.95,1.01,"95% or above")]:
    sel=[m for m in COH if lo<=inwin[m][1]<hi]
    k=sum(1 for m in sel if match(m,inwin[m][0]))
    OUT[nm]=dict(n=len(sel),matched=k,rate=k/len(sel) if sel else 0)
    print(f"  {nm:<16}{len(sel):>5}{k:>9}{k/len(sel) if sel else 0:>8.1%}",flush=True)
print("\n=== sole-supplier markets matched to a listed shortage ===",flush=True)
for m in [x for x in COH if inwin[x][1]>=.95]:
    t=inwin[m][0]; r=match(m,t)
    if r: print(f"  {m[:40]:<42}event {1991+(t-1)//4}Q{(t-1)%4+1}  shortage posted {1991+(r[0]-1)//4}Q{(r[0]-1)%4+1}  [{r[1]}]",flush=True)
# placebo: random markets never exposed
ever={m for m,_,_,_ in SL}; pool=[m for m in MQ if m not in ever]
rng=np.random.default_rng(3); td=[inwin[m][0] for m in COH]
hits=0;N=400
for _ in range(N):
    c=pool[rng.integers(len(pool))]; t=int(rng.choice(td))
    if match(c,t): hits+=1
print(f"\n  placebo rate (never-exposed markets, random dates): {hits}/{N} = {hits/N:.1%}",flush=True)
json.dump(OUT,open(os.path.expanduser("~/mnt/Research/RESULTS_shortages.json"),'w'),indent=2)
print("\nwrote Research/RESULTS_shortages.json",flush=True)

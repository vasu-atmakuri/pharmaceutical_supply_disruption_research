import duckdb, re, collections, numpy as np
con=duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MK=con.execute("SELECT DISTINCT mol FROM read_parquet('/tmp/molq_nat.parquet')").fetchall()
MK=[m[0] for m in MK]
print("markets in panel:",len(MK))
STOP={'TABLETS','TABLET','CAPSULES','CAPSULE','SOLUTION','OPHTHALMIC','OTIC','ORAL','INJECTION',
      'AND','THE','USP','MG','ML','CV','CIV','CIII','CII','EXTENDED','RELEASE','DELAYED','HCL'}
def key(m):
    ing,frm=(m.split(" | ")+[""])[0],(m.split(" | ")+[""])[1]
    w=[x for x in re.split(r'[^A-Z0-9]+',ing.upper()) if len(x)>2 and x not in STOP]
    return (frm, tuple(sorted(set(w))))
g=collections.defaultdict(list)
for m in MK: g[key(m)].append(m)
dups={k:v for k,v in g.items() if len(v)>1}
print(f"normalized keys: {len(g)}   keys holding >1 raw market: {len(dups)}")
print(f"raw markets involved in a collision: {sum(len(v) for v in dups.values())}")
print(f"\nmarkets would drop from {len(MK)} to {len(g)} under token-set normalization\n")
print("largest collisions:")
for k,v in sorted(dups.items(),key=lambda x:-len(x[1]))[:12]:
    print(f"  [{k[0]}] n={len(v)}")
    for m in v[:4]: print(f"      {m[:94]}")

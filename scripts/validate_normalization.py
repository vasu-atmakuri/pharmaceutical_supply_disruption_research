"""Independent validation of the market-key normalisation against FDA
SUBSTANCENAME, which is structured active-ingredient data populated separately
from the free-text NONPROPRIETARYNAME that the market key is built from.

A proposed merge is CONFIRMED when all raw keys in the group share an active
substance set; CONTRADICTED when they do not. A MISSED duplicate is a pair of
distinct normalised keys with the same substance set and route bucket.
"""
import duckdb, re, collections, json, os
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
NK=json.load(open(_ROOT+"/results/market_key_normalization_map.json"))
# Recompute the raw market key per PRODUCT (lab,pcode) straight from the crosswalk.
prod=con.execute("""SELECT lab,pcode,generic,substance,COALESCE(route,'') rt,COALESCE(form,'') fm
                    FROM read_parquet('/tmp/xw_route.parquet') WHERE generic<>''""").fetchall()
def bucket(rt,fm):
    r,f=rt.upper(),fm.upper()
    if 'OPHTHALMIC' in r: return 'OPHTHALMIC'
    if 'OTIC' in r or 'AURICULAR' in r: return 'OTIC'
    if 'NASAL' in r: return 'NASAL'
    if 'INHALATION' in r or 'RESPIRATORY' in r or 'ENDOTRACHEAL' in r: return 'INHALED'
    if 'VAGINAL' in r: return 'VAGINAL'
    if 'RECTAL' in r: return 'RECTAL'
    if 'TRANSDERMAL' in r: return 'TRANSDERMAL'
    if any(x in r for x in ('INTRAVENOUS','INTRAMUSCULAR','SUBCUTANEOUS','INTRA','INFILTRATION',
                            'EPIDURAL','INTRADERMAL','PARENTERAL','IMPLANT')): return 'INJECTABLE'
    if any(x in r for x in ('TOPICAL','CUTANEOUS','PERCUTANEOUS','DENTAL','PERIODONTAL','SUBGINGIVAL')): return 'TOPICAL'
    if any(x in r for x in ('ORAL','SUBLINGUAL','BUCCAL')):
        if 'TABLET' in f: return 'ORAL TABLET'
        if 'CAPSULE' in f: return 'ORAL CAPSULE'
        if any(x in f for x in ('SOLUTION','SUSPENSION','SYRUP','ELIXIR','LIQUID')): return 'ORAL LIQUID'
        return 'ORAL OTHER'
    if 'OPHTH' in f: return 'OPHTHALMIC'
    if 'OTIC' in f or 'AURICULAR' in f: return 'OTIC'
    if 'INJECT' in f or 'INFUSION' in f or 'IMPLANT' in f: return 'INJECTABLE'
    if 'SUPPOSITORY' in f or 'ENEMA' in f: return 'RECTAL'
    if any(x in f for x in ('SHAMPOO','CREAM','OINTMENT','LOTION','PATCH','GEL')): return 'TOPICAL'
    if any(x in f for x in ('AEROSOL','INHAL','SPRAY','POWDER, METERED')): return 'INHALED'
    if 'TABLET' in f: return 'ORAL TABLET'
    if 'CAPSULE' in f: return 'ORAL CAPSULE'
    if any(x in f for x in ('SOLUTION','SUSPENSION','SYRUP','ELIXIR','LIQUID')): return 'ORAL LIQUID'
    return 'OTHER'
SALTRE=re.compile(r'\b(HYDROCHLORIDE|HYDROBROMIDE|SODIUM|POTASSIUM|SULFATE|TARTRATE|MALEATE|MESYLATE|ACETATE|CITRATE|PHOSPHATE|SUCCINATE|FUMARATE|BESYLATE|BROMIDE|CHLORIDE|DIHYDRATE|MONOHYDRATE|ANHYDROUS|HCL|BITARTRATE)\b')
def sset(s):
    if not s: return frozenset()
    out=set()
    for p in re.split(r';',s.upper()):
        p=SALTRE.sub('',p)
        # FDA writes the same substance several ways; these suffixes carry no product content
        p=re.sub(r'\bUNSPECIFIED FORM\b','',p)
        p=re.sub(r'\b(HEMIHYDRATE|HYDRATE|HEPTAHYDRATE|DL|D L|ANHYDROUS|TRISODIUM)\b','',p)
        p=re.sub(r'[^A-Z0-9 ]',' ',p); p=" ".join(p.split())
        if len(p)>2: out.add(p)
    return frozenset(out)
raw_sub=collections.defaultdict(collections.Counter)
for lab,pc,gen,sub,rt,fm in prod:
    key=gen.strip().upper()+" | "+bucket(rt,fm)
    if key in NK: raw_sub[key][sset(sub)]+=1
# Counter.most_common breaks ties by insertion order, so an EMPTY substance set
# could win a tie in one run and lose it in the next, moving a merge group between
# "confirmed" and "not testable". Prefer a populated set and break ties on content.
SUB={}
for k,c in raw_sub.items():
    cand=[(n,s) for s,n in c.items() if s]
    if not cand: continue
    SUB[k]=max(cand,key=lambda x:(x[0],sorted(x[1])))[1]
print(f"raw keys with a substance set: {len([k for k,v in SUB.items() if v])} of {len(NK)}")
groups=collections.defaultdict(list)
for raw,norm in NK.items(): groups[norm].append(raw)
merged={k:v for k,v in groups.items() if len(v)>1}
ok=bad=unk=0; badlist=[]
for norm,members in sorted(merged.items()):
    ss=[SUB.get(m) for m in members]; ss=[s for s in ss if s]
    if len(ss)<2: unk+=1; continue
    if all(s==ss[0] for s in ss): ok+=1
    else:
        bad+=1
        if len(badlist)<10: badlist.append((norm,members))
print(f"\nPROPOSED MERGES: {len(merged)} groups covering {sum(len(v) for v in merged.values())} raw keys")
print(f"  confirmed by FDA substance data   : {ok}")
print(f"  contradicted (possible false merge): {bad}")
print(f"  not testable (substance missing)   : {unk}")
if ok+bad: print(f"  precision on testable merges       : {ok/(ok+bad):.1%}")
for norm,members in badlist:
    print(f"\n  CONTRADICTED {norm[:60]}")
    for m in members: print(f"      {m[:56]:<58} {sorted(SUB.get(m,frozenset()))}")
norm_sub=collections.defaultdict(set)
for raw,norm in NK.items():
    s=SUB.get(raw)
    if s: norm_sub[norm].add(s)
cand=collections.defaultdict(list)
for norm,ss in sorted(norm_sub.items()):
    if len(ss)==1: cand[(next(iter(ss)),(norm.split(" | ")+[""])[1])].append(norm)
missed={k:v for k,v in cand.items() if len(v)>1}
print(f"\nMISSED DUPLICATES: {len(missed)} substance-and-route groups still split across "
      f"{sum(len(v) for v in missed.values())} normalised keys")
for (s,rt),v in list(missed.items())[:6]:
    print(f"    [{rt}] {sorted(s)}")
    for n in v[:3]: print(f"        {n[:66]}")
json.dump({"merge_groups":len(merged),"raw_keys_merged":sum(len(v) for v in merged.values()),
           "confirmed":ok,"contradicted":bad,"untestable":unk,
           "precision":(ok/(ok+bad) if ok+bad else None),
           "missed_duplicate_groups":len(missed),"missed_keys":sum(len(v) for v in missed.values())},
  open(_ROOT+"/results/normalization_validation.json","w"),indent=2)

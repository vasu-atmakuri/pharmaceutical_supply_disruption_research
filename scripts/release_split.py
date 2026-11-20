"""How often the ingredient key separates modified-release from immediate-release.

The robustness section claims that extended- and delayed-release products are
already separate markets under the primary specification, because the normalisation
keeps release descriptors as distinguishing tokens. That claim was supported by two
typed numbers, one of which did not match the panel. This computes both.

A key "carries a release token" if its ingredient string contains one of the
descriptors below. A group "holds both forms" if, after removing those descriptors,
two keys with the same remaining ingredient set and the same route bucket differ in
whether they carry one. The second count is the one that matters, because it is where
the separation actually does work: a release token on a key with no plain
counterpart separates nothing.
"""
import duckdb, re, json, os, sys
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P=os.environ.get("LMQ_PARQUET","/tmp/lmq_v2.parquet")
if not os.path.exists(P): sys.exit(f"missing {P}; run the normalised panel stage first")
TOK=re.compile(r"\b(ER|XR|SR|CR|DR|EXTENDED|DELAYED|SUSTAINED|CONTROLLED|MODIFIED)\b")
c=duckdb.connect()
keys=[r[0] for r in c.execute(f"SELECT DISTINCT mkt FROM read_parquet('{P}')").fetchall()]
def strip(k):
    ing,rest=k.split(" | ",1)
    return ",".join(sorted(t for t in ing.split(",") if not TOK.fullmatch(t))), rest
carry=[k for k in keys if TOK.search(k.split(" | ")[0])]
groups={}
for k in keys:
    groups.setdefault(strip(k),set()).add(bool(TOK.search(k.split(" | ")[0])))
both=sorted(g for g,v in groups.items() if v=={True,False})
OUT={"release_token_markets":len(carry),"groups_with_both_forms":len(both),
     "groups":[" | ".join(g) for g in both],
     "descriptors":TOK.pattern,
     "note":("A release token with no plain counterpart separates nothing, so the "
             "second count is the one the robustness claim rests on.")}
json.dump(OUT,open(f"{R}/results/release_split.json","w"),indent=1,sort_keys=True)
print(f"{len(carry)} normalised markets carry a release descriptor; "
      f"{len(both)} ingredient-and-route groups hold both modified- and "
      f"immediate-release keys")
for g in both: print("   ", " | ".join(g))
print("wrote results/release_split.json")

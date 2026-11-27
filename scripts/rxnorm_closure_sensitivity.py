"""What the under-merging the RxNorm benchmark found would do to the reported figures.

rxnorm_market_equivalence.py scores the normalisation rule two ways. Precision is high:
of the merge groups the rule forms, RxNorm confirms nearly all. Recall is not: RxNorm
gives one ingredient signature to many key pairs that the rule leaves apart, because the
rule compares the tokens of a free-text name and the name sometimes carries a route or
form word that the bucket already encodes. BUDESONIDE and BUDESONIDE INHALATION are one
market, and the rule does not merge them.

This stage measures the consequence rather than arguing about it. It takes every raw-key
pair RxNorm calls equivalent inside one route-and-form bucket at equal stated strength,
drops the pairs whose names differ in a release or presentation modifier (RxNorm gives
an extended-release and an immediate-release product the same ingredient, and they are
not one market), closes the remainder transitively, and recomputes the concentration
figures the paper reports under that stricter normalisation.

It is a sensitivity, not a replacement. The published specification stays specification
C. This says how much further a normalisation adjudicated by RxNorm would move the
answer, which is what a reader should want to know once the recall figure is in print.
"""
import os, sys, csv, json, re, collections
import duckdb, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _stable_json import stable

R = os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LMQ = os.environ.get("PSDR_LMQ_V2", "/tmp/lmq_v2.parquet")
PAIRS = f"{R}/results/rxnorm_unmerged_equivalent_pairs.csv"
for p in (LMQ, PAIRS, f"{R}/results/market_key_normalization_map.json"):
    if not os.path.exists(p):
        sys.exit(f"missing {p}")

# A release or presentation modifier present on one name and not the other means the two
# are not one market, whatever RxNorm's ingredient set says.
MOD = re.compile(r"\b(ER|XR|SR|CR|LA|XL|DR|EXTENDED[- ]RELEASE|DELAYED[- ]RELEASE|"
                 r"SUSTAINED[- ]RELEASE|CONTROLLED[- ]RELEASE|IMMEDIATE[- ]RELEASE|"
                 r"24 ?HR|12 ?HR|CHEWABLE|DISINTEGRATING|ODT|SPRINKLE)\b")

nmap = json.load(open(f"{R}/results/market_key_normalization_map.json"))
pairs = list(csv.DictReader(open(PAIRS)))
kept, dropped = [], 0
for r in pairs:
    a, b = r["key_a"].split("|")[0].upper(), r["key_b"].split("|")[0].upper()
    if set(MOD.findall(a)) != set(MOD.findall(b)):
        dropped += 1
    else:
        kept.append((nmap[r["key_a"]], nmap[r["key_b"]]))

parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[max(ra, rb)] = min(ra, rb)   # deterministic: the lexically first key wins

for a, b in kept:
    union(a, b)
closure = {m: find(m) for m in parent}
groups = collections.Counter(closure.values())
print(f"{len(pairs)} RxNorm-equivalent pairs; {dropped} dropped as release or presentation "
      f"variants; {len(kept)} closed")
print(f"the closure merges {len(closure)} specification C markets into {len(groups)}, "
      f"a reduction of {len(closure)-len(groups)}")

con = duckdb.connect(); con.execute("SET memory_limit='2000MB'")
rows = con.execute(f"SELECT lab,mkt,tq,rx FROM read_parquet('{LMQ}')").fetchall()


def conc(remap):
    d = collections.defaultdict(dict)
    for lab, m, t, rx in rows:
        if not rx:
            continue
        mm = remap.get(m, m)
        d[(mm, t)][lab] = d[(mm, t)].get(lab, 0) + rx
    out = {}
    for k, v in d.items():
        tot = sum(v.values())
        if tot <= 0:
            continue
        sh = sorted((x / tot for x in v.values()), reverse=True)
        out[k] = dict(n=len(v), top=sh[0], hhi=sum(s * s for s in sh), rx=tot)
    return out


def stats(X):
    tot = sum(v["rx"] for v in X.values())
    one = [v for v in X.values() if v["n"] == 1]
    sole = [v for v in X.values() if v["top"] >= .95]
    return dict(mq=len(X),
                one_sh=len(one) / len(X), one_vol=sum(v["rx"] for v in one) / tot,
                sole_sh=len(sole) / len(X), sole_vol=sum(v["rx"] for v in sole) / tot,
                mean_hhi=float(np.mean([v["hhi"] for v in X.values()])),
                vw_hhi=sum(v["hhi"] * v["rx"] for v in X.values()) / tot)


# specification A's near-sole volume share, so the share of the defect this paper
# captures is a reported quantity rather than arithmetic a reader has to redo
A_sole = json.load(open(f"{R}/results/concentration_abc.json"))["A"]["sole_vol"]
C = stats(conc({}))
D = stats(conc(closure))
hdr = f"{'specification':<34}{'mkt-qtrs':>10}{'1 labeler':>11}{'vol':>9}{'top>=95%':>10}{'vol':>9}{'meanHHI':>9}"
print("\n" + hdr); print("-" * len(hdr))
for tag, r in [("C route-and-form, normalised", C), ("D  plus the RxNorm closure", D)]:
    print(f"{tag:<34}{r['mq']:>10,}{r['one_sh']:>10.1%}{r['one_vol']:>9.2%}"
          f"{r['sole_sh']:>10.1%}{r['sole_vol']:>9.2%}{r['mean_hhi']:>9.3f}")
print(f"\nnear-sole volume share  {C['sole_vol']:.2%} -> {D['sole_vol']:.2%}  "
      f"({(D['sole_vol']-C['sole_vol'])*100:+.2f} pp)")
print(f"single-labeler volume   {C['one_vol']:.2%} -> {D['one_vol']:.2%}  "
      f"({(D['one_vol']-C['one_vol'])*100:+.2f} pp)")

# how much of this reaches the analysed cohort
cohort_markets, touched = set(), set()
_cm = f"{R}/results/event_level_cohort_manifest.csv"
if os.path.exists(_cm):
    for r in csv.DictReader(open(_cm)):
        cohort_markets.add(r["market"])
    touched = cohort_markets & set(closure)
    print(f"\nevent cohort: {len(cohort_markets)} markets, {len(touched)} touched by an "
          f"adjudicated under-merge" + (": " + ", ".join(sorted(touched)) if touched else ""))

out = {"cohort_markets": len(cohort_markets),
       "cohort_markets_touched": len(touched),
       "cohort_markets_touched_names": sorted(touched),
       "pairs_total": len(pairs), "pairs_dropped_release_variant": dropped,
       "pairs_closed": len(kept),
       "markets_in_closure": len(closure), "closure_groups": len(groups),
       "markets_eliminated": len(closure) - len(groups),
       "C": C, "D": D,
       "delta_sole_vol_pp": (D["sole_vol"] - C["sole_vol"]) * 100,
       "total_defect_pp": (A_sole - D["sole_vol"]) * 100,
       "share_of_defect_captured_pct": 100 * (A_sole - C["sole_vol"]) / (A_sole - D["sole_vol"]),
       "delta_one_vol_pp": (D["one_vol"] - C["one_vol"]) * 100,
       "note": ("Specification D is specification C with every RxNorm-adjudicated equivalence "
                "closed transitively, excluding pairs whose names differ in a release or "
                "presentation modifier. It is reported as a sensitivity on the normalisation "
                "step. The published figures remain specification C, whose merges RxNorm "
                "confirms; D says how much further an externally adjudicated normalisation "
                "would move the concentration measures.")}
json.dump(stable(out), open(f"{R}/results/rxnorm_closure_sensitivity.json", "w"),
          indent=1, sort_keys=True)
print("\nwrote results/rxnorm_closure_sensitivity.json")

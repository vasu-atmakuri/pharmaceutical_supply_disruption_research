"""Independent market-equivalence benchmark against RxNorm.

The normalisation rule in this paper merges raw market keys whose substance sets agree
after counterion words are stripped. That rule is ours, and a reviewer is right that
nothing outside the paper has checked it. This stage checks it against an authority that
had no part in writing it: RxNorm, the National Library of Medicine's drug vocabulary.

What is resolved is the FDA structured substance name, not the free-text ingredient
string the market key is built from. Two reasons. The structured name is clean enough to
resolve, where a string like "TIMOLOL MALEATE OPHTHALMIC GEL FORMING SOLUTION, 0.25%" is
not. And it makes the test sharper: our rule asserts that TIMOLOL MALEATE and TIMOLOL are
the same ingredient because MALEATE is on a list of counterion words we wrote. RxNorm
decides the same question with its own ingredient hierarchy, in which a salt is a precise
ingredient (PIN) under a base ingredient (IN). Collapsing each substance to its IN is
therefore an outside adjudication of the exact step under review.

Each raw market key gets an RxNorm signature: the set of IN concepts its substances
resolve to. The stage then asks two questions of the rule:

  precision  of the merge groups the rule forms, what share have all member keys sharing
             one RxNorm signature
  recall     of the key pairs RxNorm gives one signature, inside a single route-and-form
             bucket, what share does the rule merge

Both with Wilson intervals. A substance RxNorm cannot resolve makes its key unresolved,
and unresolved keys are reported separately and never scored either way, because missing
evidence is not evidence against.

No account or API key: the RxNorm API serves non-proprietary NLM content, and the one
endpoint that needs a UMLS licence (getProprietaryInformation) is not used. Responses
cache to results/rxnorm_cache.json, so re-runs are free and the benchmark reproduces
offline once the cache is committed.

Run on a machine that can reach rxnav.nlm.nih.gov.
"""
import os, sys, json, time, re, csv, math, collections
import urllib.request, urllib.parse, urllib.error

R = os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{R}/scripts")
from _stable_json import stable

BASE = "https://rxnav.nlm.nih.gov/REST"
CACHE_PATH = f"{R}/results/rxnorm_cache.json"
MAP_PATH = f"{R}/results/market_key_normalization_map.json"
XW = os.environ.get("PSDR_XW", "/tmp/xw_route.parquet")
MIN_INTERVAL = 0.06      # 20 requests/second is NLM's published ceiling
MAX_RETRY = 4

CACHE = json.load(open(CACHE_PATH)) if os.path.exists(CACHE_PATH) else {}
_last = [0.0]
_net = [0]


def get(path, params=None):
    """One cached GET. Returns parsed JSON, {} for 'nothing there', None for failure.

    No parameter value may contain '+': urlencode would percent-encode it and RxNav
    reads the encoded form as a literal, which is how an earlier version of this stage
    sent tty=IN%2BMIN and got HTTP 400 back. Endpoints are chosen to need no such value.
    """
    url = f"{BASE}{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    if url in CACHE:
        return CACHE[url]
    for attempt in range(MAX_RETRY):
        wait = MIN_INTERVAL - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "market-equivalence-audit"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.loads(r.read().decode() or "{}")
            _net[0] += 1
            CACHE[url] = body
            if _net[0] % 300 == 0:
                save_cache()
            return body
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):      # no such concept, or no relation of that kind
                CACHE[url] = {}
                return {}
            if e.code in (403, 429, 500, 502, 503, 504) and attempt < MAX_RETRY - 1:
                time.sleep(2 ** attempt * 2)   # 403 here is the rate limit, per NLM's terms
                continue
            print(f"  HTTP {e.code} on {path}", flush=True)
            return None
        except Exception as e:
            if attempt < MAX_RETRY - 1:
                time.sleep(2 ** attempt * 2)
                continue
            print(f"  {type(e).__name__} on {path}: {e}", flush=True)
            return None
    return None


def save_cache():
    tmp = CACHE_PATH + ".tmp"
    json.dump(CACHE, open(tmp, "w"))
    os.replace(tmp, CACHE_PATH)


def rxcui_for(name):
    """RxNorm's own normalised string match. '' means no match, None means failure."""
    for search in ("2", "1"):
        b = get("/rxcui.json", {"name": name, "search": search})
        if b is None:
            return None
        ids = (b.get("idGroup") or {}).get("rxnormId") or []
        if ids:
            return ids[0]
    return ""


def base_ingredients(rxcui):
    """The IN concepts behind an rxcui, following PIN to its base ingredient."""
    b = get(f"/rxcui/{rxcui}/allrelated.json")
    if b is None:
        return None
    ins, self_tty = set(), None
    for g in ((b.get("allRelatedGroup") or {}).get("conceptGroup") or []):
        props = g.get("conceptProperties") or []
        if g.get("tty") == "IN":
            for c in props:
                ins.add(c["rxcui"])
        for c in props:
            if c.get("rxcui") == rxcui:
                self_tty = g.get("tty")
    if ins:
        return ins
    if self_tty in ("IN", "MIN"):
        return {rxcui}
    return set()


def ingredient_set(name):
    """RxNorm IN set for one substance name. None = failure, empty = unresolved."""
    rx = rxcui_for(name)
    if rx is None:
        return None
    if rx == "":
        return set()
    return base_ingredients(rx)


def selftest():
    """Known cases, including the salt case the whole benchmark rests on."""
    print("self-test against the RxNorm API")
    v = get("/version.json")
    print(f"  RxNorm version         {(v or {}).get('version', 'NO RESPONSE')}")
    if not v:
        return False
    sets, ok = {}, True
    for name, want in [("ibuprofen", 1), ("timolol", 1), ("timolol maleate", 1),
                       ("amoxicillin and clavulanate potassium", 2)]:
        s = ingredient_set(name)
        n = None if s is None else len(s)
        sets[name] = s
        flag = "ok" if n == want else "UNEXPECTED"
        print(f"  {name:38} {n} ingredient concept(s), expected {want}   {flag}")
        if n != want:
            ok = False
    if sets.get("timolol") and sets.get("timolol maleate"):
        same = sets["timolol"] == sets["timolol maleate"]
        print(f"  timolol == timolol maleate             {same}   "
              f"{'ok' if same else 'UNEXPECTED: the salt does not collapse to its base'}")
        ok = ok and same
    return ok


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)


def raw_key_substances(nmap):
    """raw market key -> (modal FDA substance string, heterogeneous?).

    The bucket rule is read out of natpanel_route.py at runtime, so this cannot drift
    from the panel the paper reports.
    """
    import duckdb
    if not os.path.exists(XW):
        sys.exit(f"{XW} is missing; run scripts/rebuild_xw_route.py first")
    np_src = open(f"{R}/scripts/natpanel_route.py").read()
    i = np_src.index(" CASE\n  WHEN rt LIKE '%OPHTHALMIC%'")
    j = np_src.index("ELSE 'OTHER' END", i) + len("ELSE 'OTHER' END")
    bucket_sql = np_src[i:j]
    if "ORAL TABLET" not in bucket_sql:
        sys.exit("could not read the route-bucket rule out of natpanel_route.py")
    con = duckdb.connect()
    rows = con.execute(
        "SELECT generic, " + bucket_sql + " AS bucket, substance, COUNT(*) n FROM ("
        "SELECT generic, COALESCE(route,'') rt, COALESCE(form,'') f, substance "
        f"FROM read_parquet('{XW}')) GROUP BY 1,2,3").fetchall()
    acc = collections.defaultdict(list)
    for g, b, sub, n in rows:
        k = f"{g} | {b}"
        if k in nmap:
            acc[k].append((n, sub or ""))
    out = {}
    for k, v in acc.items():
        out[k] = (max(v)[1], len({s for _, s in v if s}) > 1)
    return out


NUM = re.compile(r"\d+(?:\.\d+)?")


def strength(raw_key):
    """The numeric content of the ingredient string, as a sorted tuple.

    An RxNorm ingredient set says nothing about strength, so two keys can share a
    signature and still be different markets: TIMOLOL 0.25% and TIMOLOL 0.5% do. The
    recall arm therefore only treats a same-signature pair as a candidate merge when
    the numbers in the two ingredient strings agree, and reports how many pairs this
    excludes rather than scoring the rule against them.
    """
    return tuple(sorted(NUM.findall(raw_key.split("|")[0])))


def components(sub):
    out = []
    for c in re.split(r";", (sub or "").upper()):
        c = " ".join(c.split())
        if len(c) > 2:
            out.append(c)
    return out


def main():
    if not os.path.exists(MAP_PATH):
        sys.exit(f"missing {MAP_PATH}: run the pipeline first")
    if not selftest():
        save_cache()
        sys.exit("\nthe RxNorm API did not behave as this benchmark assumes, so nothing was "
                 "scored.\nsend the output above and the stage will be corrected before it "
                 "reports anything.")
    print()

    nmap = json.load(open(MAP_PATH))
    groups = collections.defaultdict(list)
    for raw, final in nmap.items():
        groups[final].append(raw)
    merged = {f: sorted(ks) for f, ks in groups.items() if len(ks) > 1}
    subs = raw_key_substances(nmap)
    het = sum(1 for _, h in subs.values() if h)
    print(f"{len(nmap)} raw keys, {len(groups)} normalised keys, {len(merged)} merge groups")
    print(f"{len(subs)} keys carry an FDA substance string; {het} have more than one across "
          f"their own products")

    comps = sorted({c for s, _ in subs.values() for c in components(s)})
    print(f"resolving {len(comps)} distinct substance names through RxNorm")
    ING, FAILED = {}, []
    for i, c in enumerate(comps, 1):
        s = ingredient_set(c)
        if s is None:
            FAILED.append(c)
        else:
            ING[c] = frozenset(s)
        if i % 200 == 0:
            print(f"  {i}/{len(comps)}", flush=True)
    save_cache()
    got = sum(1 for v in ING.values() if v)
    print(f"resolved {got} of {len(comps)} substance names; "
          f"{len(comps)-got-len(FAILED)} matched nothing; {len(FAILED)} service failures")

    SIG = {}
    for k, (s, _) in subs.items():
        cs = components(s)
        if not cs or any(c not in ING or not ING[c] for c in cs):
            continue
        SIG[k] = frozenset().union(*[ING[c] for c in cs])
    print(f"{len(SIG)} of {len(nmap)} raw keys carry a complete RxNorm signature")

    rows, conf, contra, unres = [], 0, 0, 0
    for final in sorted(merged):
        ks = merged[final]
        have = {k: SIG[k] for k in ks if k in SIG}
        if len(have) < 2:
            verdict, unres = "unresolved", unres + 1
        elif len(set(have.values())) == 1:
            verdict, conf = "confirmed", conf + 1
        else:
            verdict, contra = "contradicted", contra + 1
        rows.append({"normalised_key": final, "n_raw_keys": len(ks),
                     "n_with_signature": len(have), "verdict": verdict,
                     "raw_keys": " ;; ".join(ks),
                     "fda_substances": " ;; ".join(subs.get(k, ("", 0))[0] for k in ks),
                     "rxnorm_in_sets": " ;; ".join(
                         "+".join(sorted(SIG[k])) if k in SIG else "" for k in ks)})
    scored = conf + contra
    p, plo, phi = wilson(conf, scored)

    by_sig = collections.defaultdict(list)
    for k, v in SIG.items():
        by_sig[(k.split("|", 1)[1].strip() if "|" in k else "", v)].append(k)
    caught, missed, diff_strength, missed_rows = 0, 0, 0, []
    for (bk, sig), ks in by_sig.items():
        for a in range(len(ks)):
            for b in range(a + 1, len(ks)):
                ka, kb = ks[a], ks[b]
                if nmap[ka] == nmap[kb]:
                    caught += 1
                elif strength(ka) != strength(kb):
                    diff_strength += 1
                else:
                    missed += 1
                    missed_rows.append({"bucket": bk, "key_a": ka, "key_b": kb,
                                        "shared_rxnorm_in_set": "+".join(sorted(sig))})
    r, rlo, rhi = wilson(caught, caught + missed)

    out = {
        "raw_keys": len(nmap), "normalised_keys": len(groups), "merge_groups": len(merged),
        "substance_names_queried": len(comps), "substance_names_resolved": got,
        "substance_names_unmatched": len(comps) - got - len(FAILED),
        "substance_names_service_failure": len(FAILED),
        "keys_with_signature": len(SIG),
        "keys_heterogeneous_substance": het,
        "groups_confirmed": conf, "groups_contradicted": contra,
        "groups_unresolved": unres, "groups_scored": scored,
        "precision": p, "precision_lo": plo, "precision_hi": phi,
        "equivalent_pairs_merged": caught, "equivalent_pairs_not_merged": missed,
        "equivalent_pairs_excluded_differing_strength": diff_strength,
        "recall": r, "recall_lo": rlo, "recall_hi": rhi,
        "requests_made_this_run": _net[0],
        "note": ("RxNorm signature of a raw market key: the set of RxNorm base ingredient (IN) "
                 "concepts its FDA structured substance names resolve to, salts followed from "
                 "the precise ingredient to its base. Precision is the share of this paper's "
                 "merge groups whose member keys all share one signature, among groups where at "
                 "least two members have one. Recall is the share of same-signature key pairs "
                 "inside one route-and-form bucket, and of equal stated strength, that the rule "
                 "merges; an RxNorm ingredient set carries no strength, so same-signature pairs "
                 "whose ingredient strings differ numerically are excluded and counted, not "
                 "scored against the rule. Keys without a complete "
                 "signature are reported separately and scored neither way. RxNorm adjudicates "
                 "ingredient identity, not clinical substitutability, so agreement here is "
                 "evidence about the normalisation step alone."),
    }
    json.dump(stable(out), open(f"{R}/results/rxnorm_market_equivalence.json", "w"),
              indent=1, sort_keys=True)
    with open(f"{R}/results/rxnorm_market_equivalence.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    if missed_rows:
        with open(f"{R}/results/rxnorm_unmerged_equivalent_pairs.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(missed_rows[0].keys()))
            w.writeheader()
            w.writerows(sorted(missed_rows, key=lambda d: (d["bucket"], d["key_a"])))
    if FAILED:
        print(f"\n{len(FAILED)} substance names could not be queried at all, first few: "
              f"{FAILED[:5]}")

    print(f"\nprecision {conf}/{scored} = {p:.3f} [{plo:.3f}, {phi:.3f}]"
          f"   ({contra} contradicted, {unres} groups without two signatures)")
    print(f"recall    {caught}/{caught+missed} = {r:.3f} [{rlo:.3f}, {rhi:.3f}]"
          f"   ({missed} same-signature equal-strength pairs the rule leaves apart; "
          f"{diff_strength} more excluded for differing strength)")
    print("\nwrote results/rxnorm_market_equivalence.json and .csv"
          + (", results/rxnorm_unmerged_equivalent_pairs.csv" if missed_rows else ""))
    print(f"cache: results/rxnorm_cache.json ({len(CACHE)} responses)")


if __name__ == "__main__":
    main()

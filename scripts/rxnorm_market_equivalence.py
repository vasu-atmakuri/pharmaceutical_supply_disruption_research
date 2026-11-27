"""Independent market-equivalence benchmark against RxNorm.

The normalisation rule in this paper merges raw market keys whose ingredient token
sets agree after counterion stripping. That rule is ours. This stage tests it against
an outside authority that had no part in writing it: RxNorm, the National Library of
Medicine's drug vocabulary.

Each raw market key's ingredient string is resolved through the RxNorm API to a set of
RxNorm ingredient concepts (IN, or MIN for multi-ingredient concepts). Two raw keys are
RxNorm-equivalent when they resolve to identical ingredient-concept sets. The stage then
asks two questions of every merge group:

  precision  of the merges the rule performs, what share does RxNorm confirm
  recall     of the raw-key pairs RxNorm says are equivalent, within the same route and
             form bucket, what share does the rule merge

Both are reported with Wilson intervals. Keys RxNorm cannot resolve are counted
separately and never scored as agreement or disagreement, because an unresolved string
is missing evidence rather than evidence against.

No account or API key is needed: the RxNorm API serves non-proprietary NLM content, and
the one endpoint that requires a UMLS licence (getProprietaryInformation) is not used
here. Responses are cached in results/rxnorm_cache.json, so a second run costs nothing
and the benchmark is reproducible without network access.

Run this on a machine with network access to rxnav.nlm.nih.gov.
"""
import os, sys, json, time, re, urllib.request, urllib.parse, urllib.error, collections, math

R = os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{R}/scripts")
from _stable_json import stable

BASE = "https://rxnav.nlm.nih.gov/REST"
CACHE_PATH = f"{R}/results/rxnorm_cache.json"
MAP_PATH = f"{R}/results/market_key_normalization_map.json"
XW = os.environ.get("PSDR_XW", "/tmp/xw_route.parquet")
MIN_INTERVAL = 0.06          # <= 20 requests/second, NLM's published ceiling
MAX_RETRY = 4

CACHE = json.load(open(CACHE_PATH)) if os.path.exists(CACHE_PATH) else {}
_last = [0.0]
_net = [0]


def get(path, params):
    """One GET, cached by full URL. Returns parsed JSON or None on a hard failure."""
    url = f"{BASE}{path}?" + urllib.parse.urlencode(params)
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
            if _net[0] % 200 == 0:
                save_cache()
                print(f"  {_net[0]} requests made, cache saved", flush=True)
            return body
        except urllib.error.HTTPError as e:
            if e.code == 404:
                CACHE[url] = {}
                return {}
            if e.code in (403, 429, 500, 502, 503, 504) and attempt < MAX_RETRY - 1:
                time.sleep(2 ** attempt * 2)   # 403 here means the rate limit, per NLM's terms
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


def selftest():
    """Three known cases, so one run tells us whether the service behaves as assumed."""
    print("self-test against the RxNorm API")
    ok = True
    v = get("/version.json", {})
    print(f"  version                {(v or {}).get('version', 'NO RESPONSE')}")
    if not v:
        return False
    for name, expect in [("ibuprofen", 1), ("amoxicillin and clavulanate potassium", 2)]:
        ings = ingredients_for_string(name)
        got = len(ings) if ings is not None else None
        print(f"  {name[:34]:36} {got} ingredient concept(s), expected {expect}")
        if got != expect:
            ok = False
    return ok


def rxcui_for_string(s):
    """RxNorm's own normalised string match. search=2 allows its normalisation."""
    for search in ("2", "1"):
        b = get("/rxcui.json", {"name": s, "search": search})
        if b is None:
            return None
        ids = ((b.get("idGroup") or {}).get("rxnormId") or [])
        if ids:
            return ids[0]
    b = get("/approximateTerm.json", {"term": s, "maxEntries": "1", "option": "1"})
    if b is None:
        return None
    cands = ((b.get("approximateGroup") or {}).get("candidate") or [])
    for c in cands:
        if int(c.get("score", 0)) >= 90 and c.get("rxcui"):
            return c["rxcui"]
    return ""


def ingredients_for_rxcui(rxcui):
    b = get(f"/rxcui/{rxcui}/related.json", {"tty": "IN+MIN"})
    if b is None:
        return None
    out = set()
    for g in ((b.get("relatedGroup") or {}).get("conceptGroup") or []):
        if g.get("tty") == "IN":
            for c in (g.get("conceptProperties") or []):
                out.add(c["rxcui"])
    if out:
        return out
    for g in ((b.get("relatedGroup") or {}).get("conceptGroup") or []):
        if g.get("tty") == "MIN":
            for c in (g.get("conceptProperties") or []):
                out.add("MIN:" + c["rxcui"])
    return out


def ingredients_for_string(s):
    """None = service failure. Empty set = resolved to nothing (unresolved key)."""
    rx = rxcui_for_string(s)
    if rx is None:
        return None
    if rx == "":
        return set()
    ing = ingredients_for_rxcui(rx)
    if ing is None:
        return None
    if not ing:
        p = get(f"/rxcui/{rx}/property.json", {"propName": "TTY"})
        if p and ((p.get("propConceptGroup") or {}).get("propConcept") or [{}])[0].get("propValue") == "IN":
            return {rx}
    return ing


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)


def ingredient_string(raw_key):
    """The market key is 'INGREDIENT STRING | BUCKET'. Take the ingredient half."""
    return raw_key.split("|")[0].strip()


def bucket(raw_key):
    return raw_key.split("|", 1)[1].strip() if "|" in raw_key else ""


def main():
    if not os.path.exists(MAP_PATH):
        sys.exit(f"missing {MAP_PATH}: run the pipeline first")
    if not selftest():
        save_cache()
        sys.exit("\nthe RxNorm API did not behave as this stage assumes; nothing was scored.\n"
                 "re-run on a machine that can reach rxnav.nlm.nih.gov, and send the output above.")
    print()

    nmap = json.load(open(MAP_PATH))
    groups = collections.defaultdict(list)
    for raw, final in nmap.items():
        groups[final].append(raw)
    merged = {f: ks for f, ks in groups.items() if len(ks) > 1}
    print(f"{len(nmap)} raw keys, {len(groups)} normalised keys, {len(merged)} merge groups")

    keys = sorted(nmap)
    print(f"resolving {len(keys)} ingredient strings through RxNorm "
          f"({sum(1 for k in keys if f'{BASE}/rxcui.json?' + urllib.parse.urlencode({'name': ingredient_string(k), 'search': '2'}) not in CACHE)} not cached)")
    ING, FAILED = {}, []
    for i, k in enumerate(keys, 1):
        s = ingredient_string(k)
        ing = ingredients_for_string(s)
        if ing is None:
            FAILED.append(k)
        else:
            ING[k] = frozenset(ing)
        if i % 250 == 0:
            print(f"  {i}/{len(keys)}", flush=True)
    save_cache()
    resolved = {k: v for k, v in ING.items() if v}
    print(f"resolved {len(resolved)} of {len(keys)} keys; {len(keys)-len(resolved)-len(FAILED)} "
          f"resolved to nothing; {len(FAILED)} service failures")

    # precision: of the merges the rule performs, what share does RxNorm confirm
    rows, conf, contra, unres = [], 0, 0, 0
    for final, ks in sorted(merged.items()):
        sets = {k: resolved.get(k) for k in ks}
        have = {k: v for k, v in sets.items() if v}
        if len(have) < 2:
            verdict = "unresolved"
            unres += 1
        elif len(set(have.values())) == 1:
            verdict = "confirmed"
            conf += 1
        else:
            verdict = "contradicted"
            contra += 1
        rows.append({"normalised_key": final, "n_raw_keys": len(ks),
                     "n_resolved": len(have), "verdict": verdict,
                     "raw_keys": " ;; ".join(sorted(ks)),
                     "rxnorm_ingredient_sets": " ;; ".join(
                         sorted("+".join(sorted(v)) if v else "" for v in sets.values()))})
    scored = conf + contra
    p, plo, phi = wilson(conf, scored)

    # recall: pairs RxNorm calls equivalent, inside one route-and-form bucket, that the
    # rule leaves apart. Only keys that resolved are eligible on either side.
    by_sig = collections.defaultdict(list)
    for k, v in resolved.items():
        by_sig[(bucket(k), v)].append(k)
    missed, caught, missed_rows = 0, 0, []
    for (bk, sig), ks in by_sig.items():
        if len(ks) < 2:
            continue
        finals = {nmap[k] for k in ks}
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                if nmap[ks[i]] == nmap[ks[j]]:
                    caught += 1
                else:
                    missed += 1
                    missed_rows.append({"bucket": bk, "key_a": ks[i], "key_b": ks[j],
                                        "shared_ingredient_set": "+".join(sorted(sig))})
    r, rlo, rhi = wilson(caught, caught + missed)

    out = {
        "raw_keys": len(nmap), "normalised_keys": len(groups), "merge_groups": len(merged),
        "keys_resolved": len(resolved), "keys_unresolved": len(keys) - len(resolved) - len(FAILED),
        "keys_service_failure": len(FAILED),
        "groups_confirmed": conf, "groups_contradicted": contra, "groups_unresolved": unres,
        "groups_scored": scored,
        "precision": p, "precision_lo": plo, "precision_hi": phi,
        "equivalent_pairs_merged": caught, "equivalent_pairs_not_merged": missed,
        "recall": r, "recall_lo": rlo, "recall_hi": rhi,
        "requests_made_this_run": _net[0],
        "note": ("Precision is the share of this paper's merge groups whose member raw keys all "
                 "resolve to one RxNorm ingredient-concept set, among groups where at least two "
                 "members resolved. Recall is the share of RxNorm-equivalent raw-key pairs inside "
                 "a single route-and-form bucket that the rule does merge. Keys RxNorm cannot "
                 "resolve are reported separately and are not scored either way. RxNorm is an "
                 "independent authority on ingredient identity, not on market substitutability, "
                 "so agreement here is evidence about the normalisation step alone."),
    }
    json.dump(stable(out), open(f"{R}/results/rxnorm_market_equivalence.json", "w"),
              indent=1, sort_keys=True)

    import csv
    with open(f"{R}/results/rxnorm_market_equivalence.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    if missed_rows:
        with open(f"{R}/results/rxnorm_unmerged_equivalent_pairs.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(missed_rows[0].keys()))
            w.writeheader()
            w.writerows(sorted(missed_rows, key=lambda d: (d["bucket"], d["key_a"])))

    print(f"\nprecision {conf}/{scored} = {p:.3f} [{plo:.3f}, {phi:.3f}]"
          f"   ({contra} contradicted, {unres} groups unresolved)")
    print(f"recall    {caught}/{caught+missed} = {r:.3f} [{rlo:.3f}, {rhi:.3f}]"
          f"   ({missed} equivalent pairs the rule leaves apart)")
    print(f"\nwrote results/rxnorm_market_equivalence.json, .csv"
          + (", results/rxnorm_unmerged_equivalent_pairs.csv" if missed_rows else ""))
    print(f"cache: results/rxnorm_cache.json ({len(CACHE)} responses) "
          f"- commit it and the benchmark reruns offline")


if __name__ == "__main__":
    main()

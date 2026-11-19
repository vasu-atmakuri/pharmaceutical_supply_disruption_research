"""Readable names for the market keys and labeler codes the paper prints.

Both were hand-maintained lists, which is how the reclassification table and Figure
1(a) once disagreed about a dosage form, and how a growing event cohort stopped the
build. Both are now derived: labeler names come from FDA's own LABELERNAME field via
results/labeler_names.json, and market names from the ingredient tokens and route
bucket in the key itself. Overrides exist only where the derivation reads badly, and
an unresolvable name raises rather than guesses.
"""
import json, os, re

_ROOT=os.environ.get("PSDR_ROOT") or os.path.expanduser(
    "~/mnt/Research/pharmaceutical_supply_disruption_research")

# Salt, ester and hydrate words that belong after the base ingredient in prose.
_TRAILING={"ACETATE","HYDROCHLORIDE","SODIUM","POTASSIUM","CHLORIDE","BROMIDE",
           "SULFATE","TARTRATE","MALEATE","MESYLATE","PHOSPHATE","CITRATE",
           "SUCCINATE","FUMARATE","BESYLATE","TOSYLATE","OXALATE","NITRATE",
           "CARBONATE","GLUCONATE","EPOLAMINE","PALMITATE","SACCHARATE",
           "ASPARTATE","MONOHYDRATE","HYDRATE","CALCIUM","MALATE","VALERATE"}
_BUCKET={"ORAL TABLET":"oral tablet","ORAL CAPSULE":"oral capsule",
         "ORAL LIQUID":"oral liquid","ORAL OTHER":"oral, other",
         "INJECTABLE":"injectable","TOPICAL":"topical","OPHTHALMIC":"ophthalmic",
         "OTIC":"otic","NASAL":"nasal","INHALED":"inhaled","RECTAL":"rectal",
         "VAGINAL":"vaginal","TRANSDERMAL":"transdermal","OTHER":"other",
         "UNKNOWN ROUTE":"route not recorded"}
# Keys whose derived name reads poorly, or where the FDA free text is misspelled.
# A misspelling is kept in the key, because the key is the data; only the label is
# corrected, and the discrepancy is itself an instance of what the paper measures.
_OVERRIDE={
 "ACETATE,ACID,ALPHA,ASCORBIC,BETA,BIOTIN,CAROTENE,CHOLECALCIFEROL,CUPRIC,"
 "CYANOCOBALAMIN,FLUORIDE,FOLIC,GLUCONATE,GLUCOSAMINE,LEVOMEFOLATE,NIACINAMIDE,"
 "OXIDE,PYRIDOXINE,RIBOFLAVIN,SODIUM,THIAMINE,TOCOPHEROL,VITAMIN,ZINC | ORAL TABLET":
     "Multivitamin with minerals, oral tablet",
 "ACID,FOLIC,IRON,MINERAL,SUPPLEMENT,VITAMIN | OTHER":
     "Iron, folic acid and vitamin supplement, other",
 "ACETIC,ACID,HYDROCORTISONE | OTIC": "Hydrocortisone and acetic acid, otic",
 "AMPHETAMINE,ASPARTATE,DEXTROAMPHETAMINE,SACCHARATE,SULFATE | ORAL CAPSULE":
     "Mixed amphetamine salts, oral capsule",
 "BRIMONIDINE,BRINZOLAMIDE,TARTRATE | OPHTHALMIC":
     "Brinzolamide and brimonidine, ophthalmic",
 "DORZOLAMIDE,HYDROCHLORIDE,MALEATE,TIMOLOL | OPHTHALMIC":
     "Dorzolamide and timolol, ophthalmic",
 "ESCITSLOPRAM | ORAL TABLET": "Escitalopram, oral tablet\\textsuperscript{b}",
 "GRISOFULVIN | ORAL LIQUID": "Griseofulvin, oral liquid\\textsuperscript{b}",
 "3,MINERAL,OMEGA,SUPPLEMENT,VITAMIN | ORAL CAPSULE":
     "Omega-3 and multivitamin supplement, oral capsule",
 "1,CREAM,DENTAL,FLUORIDE,PRESCRIPTION,SODIUM | TOPICAL":
     "Prescription fluoride dental cream, topical",
 # the key sorts its tokens alphabetically, which puts the formulation index first
 "4,ELEMENTS,TRACE | INJECTABLE": "Trace Elements 4, injectable",
 "5,ELEMENTS,TRACE | INJECTABLE": "Trace Elements 5, injectable",
}

def _bucket_name(b):
    base=b.split(" #")[0]
    if base not in _BUCKET:
        raise SystemExit(f"display_names.py has no label for route bucket {base!r}")
    return _BUCKET[base]

def name(key):
    """A readable label for a corrected market key."""
    if key in _OVERRIDE: return _OVERRIDE[key]
    # the composition tie-break appends a hash to the bucket; the label is the same
    base=re.sub(r" #[0-9a-f]+$","",key)
    if base in _OVERRIDE: return _OVERRIDE[base]
    if " | " not in key:
        raise SystemExit(f"display_names.py cannot parse market key {key!r}")
    ing,bucket=key.split(" | ",1)
    toks=[t for t in ing.split(",") if t]
    if len(toks)>4:
        raise SystemExit(f"display_names.py has no event-table name for {key!r}: "
                         f"{len(toks)} ingredient tokens is too many to render "
                         f"automatically, so add an explicit override")
    head=[t for t in toks if t not in _TRAILING]
    tail=[t for t in toks if t in _TRAILING]
    if not head:
        raise SystemExit(f"display_names.py: every token in {key!r} is a salt word")
    words=[w.capitalize() for w in head]+[w.lower() for w in tail]
    return " ".join(words)+", "+_bucket_name(bucket)

_LAB=None
def _labs():
    global _LAB
    if _LAB is None:
        p=f"{_ROOT}/results/labeler_names.json"
        if not os.path.exists(p):
            raise SystemExit("results/labeler_names.json is missing; "
                             "rebuild_xw_route.py writes it from FDA product.txt")
        _LAB=json.load(open(p))
    return _LAB

_SUFFIX=re.compile(r"\b(inc|llc|lp|l\.p\.|corp|corporation|limited|ltd|co|company|"
                   r"laboratories|labs|pharmaceuticals?|pharma|therapeutics|sciences|"
                   r"usa|u\.s\.|us|division|div|specialty|of new york|americas?)\b\.?",
                   re.I)
def labeler(code):
    """A short display name for a labeler code, from FDA's own labeler name."""
    c=str(code).zfill(5)
    full=_labs().get(c)
    if not full:
        raise SystemExit(f"no FDA labeler name for code {c!r}; it is not in "
                         f"results/labeler_names.json")
    s=full.split(",")[0]
    if s.isupper(): s=s.title().replace("Womens","Women's")
    s=_SUFFIX.sub("",s)
    s=re.sub(r"\(\s*\)","",s)              # Advanz Pharma (US) Corp -> Advanz
    s=re.sub(r"\s{2,}"," ",s).strip(" .,-")
    s=re.sub(r"\bU\.?S\.?$","",s).strip(" .,-")   # Sanofi-Aventis U.S -> Sanofi-Aventis
    return s if s else full.split(",")[0].strip()

def labeler_full(code):
    return _labs().get(str(code).zfill(5),"")

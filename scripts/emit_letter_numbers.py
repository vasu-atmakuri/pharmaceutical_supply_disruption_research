"""Rewrite the response letter's volatile numbers from the analysis outputs.

The manuscript cannot carry a stale number because every quantity in it is a macro.
The letter is markdown and had no such protection, so each panel rebuild left it
contradicting the paper and audit_letter.py caught it after the fact. This applies
the same principle: each volatile figure is substituted from results before the
audit runs, and every pattern must match exactly once or this fails loudly.
"""
import json, os, re, sys
_ROOT=os.environ.get("PSDR_ROOT") or os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
R=f"{_ROOT}/results"
L=lambda f: json.load(open(f"{R}/{f}"))
NUM=L("manuscript_numbers.json"); RUL=L("reclassification_rules.json")
VAL=L("normalization_validation.json"); INF=L("inference_normalized.json")
SEN=L("sensitivities.json"); RML=L("recall_match_level.json")
SPEC={x["tag"][0]:x for x in L("three_specifications.json")}
FL=SPEC["C"]["sole_flow"]
def g(d,*k):
    for x in k: d=d[x]
    return d
# (pattern, replacement) - the pattern must capture nothing and match exactly once
SUBS=[
 (r"Of the [\d,]+ raw near-sole market-quarters",
  f"Of the {RUL['largest_n']:,} raw near-sole market-quarters"),
 (r"Adding strength gives [\d,]+ market-quarters, with [\d.]+% near-sole",
  f"Adding strength gives {SEN['strength_market_quarters']:,} market-quarters, "
  f"with {SEN['strength_nearsole_share']:.1f}% near-sole"),
 (r"\| Largest corrected component no longer near-sole \| [\d,]+ \| [\d.]+% \|",
  f"| Largest corrected component no longer near-sole | {RUL['largest_reclass']:,} | "
  f"{RUL['largest_rate']*100:.1f}% |"),
 (r"\| No component still near-sole \| [\d,]+ \| [\d.]+% \|",
  f"| No component still near-sole | {RUL['any_reclass']:,} | "
  f"{RUL['any_reclass']/RUL['largest_n']*100:.1f}% |"),
 (r"\| At least one component no longer near-sole \| [\d,]+ \| [\d.]+% \|",
  f"| At least one component no longer near-sole | {RUL['all_reclass']:,} | "
  f"{RUL['all_reclass']/RUL['largest_n']*100:.1f}% |"),
 (r"All \d+ macros now carry", f"All {NUM['generated_macro_count']} macros now carry"),
 (r"with the substance data to \*\*all \d+ testable groups",
  f"with the substance data to **all {VAL['confirmed']} testable groups"),
 (r"agreement is \d+ of \d+ testable groups",
  f"agreement is {VAL['confirmed']} of {VAL['confirmed']} testable groups"),
 (r"\d+ groups remain untestable", f"{VAL['untestable']} groups remain untestable"),
 (r"The bound is [\d.]+ to [\d.]+ percent",
  f"The bound is {NUM['bound_low']} to {NUM['bound_high']} percent"),
 (r"missing-follow-up bounds of [\d.]+% to [\d.]+%",
  f"missing-follow-up bounds of {NUM['bound_low']}% to {NUM['bound_high']}%"),
]
p=f"{_ROOT}/springer/response_to_reviewer.md"; s=open(p).read()
fails=[]; n=0
for pat,rep in SUBS:
    hits=len(re.findall(pat,s))
    if hits!=1: fails.append(f"pattern matched {hits} times, expected 1: {pat[:62]}")
    else: s=re.sub(pat,rep.replace("\\","\\\\"),s); n+=1
if fails:
    print(f"{len(fails)} LETTER PATTERNS DID NOT MATCH EXACTLY ONCE:")
    for f in fails: print("   "+f)
    print("\nEdit emit_letter_numbers.py to match the letter's current wording, or fix the letter.")
    sys.exit(1)
open(p,"w").write(s)
print(f"{n} volatile figures in the response letter refreshed from results")

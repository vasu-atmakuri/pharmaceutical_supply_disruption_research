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
import glob as _g, subprocess as _sp
# How many generated tables and relationship assertions there actually are. Both were
# typed in the letter and both changed this round.
_NTAB=len(_g.glob(f"{_ROOT}/springer/generated/tab_*.tex"))
_NREL=int(_sp.run([sys.executable,f"{_ROOT}/scripts/check_relationships.py"],
                  capture_output=True,text=True,
                  env={**os.environ,"PSDR_ROOT":_ROOT}).stdout.split(" relationship checks")[0].split()[-1])
# (pattern, replacement) - the pattern must capture nothing and match exactly once
SUBS=[
 (r"(?:\d+|nine|ten|eleven|twelve) of the tables and the abstract are emitted whole",
  "%d of the tables and the abstract are emitted whole" % _NTAB),
 (r"runs \d+ assertions on relationships",
  "runs %d assertions on relationships" % _NREL),
 (r"trimming \([\d.]+ → [\d.]+ → [\d.]+ → [\d.]+ removing",
  f"trimming ({INF['R_<35%']['median']:.2f} \u2192 "
  f"{SEN['minority_excl1_median']:.2f} \u2192 {SEN['minority_excl3_median']:.2f} \u2192 "
  f"{SEN['minority_excl5_median']:.2f} removing"),
 (r"mean falls from [-\d.]+ to [-\d.]+, [-\d.]+ and [-\d.]+, and the\nvolume-weighted ratio from [-\d.]+ to [-\d.]+, [-\d.]+ and [-\d.]+, changing sign\.",
  f"mean falls from {INF['R_<35%']['mean']:.2f} to {SEN['minority_excl1_mean']:.2f}, "
  f"{SEN['minority_excl3_mean']:.2f} and {SEN['minority_excl5_mean']:.2f}, and the\n"
  f"volume-weighted ratio from {INF['R_<35%']['volwtd']:.2f} to {SEN['minority_excl1_volwtd']:.2f}, "
  f"{SEN['minority_excl3_volwtd']:.2f} and {SEN['minority_excl5_volwtd']:.2f}, changing sign."),
 (r"The five largest ratios are [\d, ]+and [\d.]+\.",
  "The five largest ratios are "
  + ", ".join(f"{x:.0f}" for x in SEN["minority_top_ratios"][:-1])
  + f" and {SEN['minority_top_ratios'][-1]:.0f}."),
 (r"matched-set interval is [\d.]+ to [\d.]+ points",
  f"matched-set interval is {100*INF['matched']['ci_sets'][0]:.1f} to "
  f"{100*INF['matched']['ci_sets'][1]:.1f} points"),
 (r"\d+ of the \d+ observed events had exactly",
  f"{NUM['cohort_exactly_one_labeler']} of the {FL['observed']} observed events had exactly"),
 (r"\d+ had a second labeler whose dispensing was small enough",
  f"{NUM['cohort_two_plus_labelers']} had a second labeler whose dispensing was small enough"),
 (r"takes \d+ of \d+ to \d+ of \d+, or [\d.]+% to [\d.]+%\.",
  f"takes {SEN['suppression_primary_n']} of {SEN['suppression_n']} to "
  f"{SEN['suppression_scenario_n']} of {SEN['suppression_n']}, or "
  f"{SEN['suppression_primary_rate']}% to {SEN['suppression_scenario_rate']}%."),
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

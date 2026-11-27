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
# These two counts were derived here for phrases the letter no longer contains, and one
# of them shelled out to check_relationships.py to read its assertion count. That check
# needs poppler to read the figure PDFs, so on a machine without poppler it printed
# nothing and this stage died with an IndexError before the substitutions ran. A stage
# that refreshes a document should not depend on a check being runnable, so both are
# gone rather than guarded.
# (pattern, replacement) - the pattern must capture nothing and match exactly once
_WORD={8:"eight",9:"nine",10:"ten",11:"eleven",12:"twelve"}
# the number of final checks run_all.sh runs, excluding the preflight
_NCHK=len(set(re.findall(r"((?:audit|check|verify)_\w+)\.py",
            open(f"{_ROOT}/scripts/run_all.sh").read()))-{"check_environment"})

# number words, so a count the letter spells out agrees with the count in the results
_ONES=["zero","one","two","three","four","five","six","seven","eight","nine","ten",
 "eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen",
 "nineteen"]
_TENS={2:"twenty",3:"thirty",4:"forty",5:"fifty",6:"sixty",7:"seventy",8:"eighty",9:"ninety"}
def _w(n):
    n=int(n)
    if n<20: return _ONES[n]
    if n<100:
        t,o=divmod(n,10)
        return _TENS[t]+("" if o==0 else "-"+_ONES[o])
    return f"{n:,}"

import sys as _sys
_sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from exit_causes import SOURCES as _SRC

# Two tables in the letter are regenerated whole, between markers, because a table of
# six populations is not worth maintaining as a dozen regular expressions.
CS=L("cause_strata.json"); RC=L("recovery_censored.json")
TY=L("typo_sensitivity.json"); DV=L("detector_variants.json")
_SS=DV["suppression_sensitivity"]; _PW=DV["persistence_window"]
_LAD=[("all","Every observed near-sole exit"),
      ("ex_withdrawal","Excluding the market-wide withdrawal"),
      ("ex_withdrawal_transition","Excluding the withdrawal and the three transitions"),
      ("ex_strong_evidence","Excluding only market-wide or product-and-firm explanations"),
      ("ex_all_explained","Excluding every alternative-explanation class"),
      ("supply_only","Documented supply disruptions only")]
def _ladder_table():
    out=["| Population | Events | Median R | Collapsed |","|---|---|---|---|"]
    for k,lab in _LAD:
        v=CS["ladder"][k]
        out.append(f"| {lab} | {v['n']} | {v['median']:.2f} | {v['collapsed']} |")
    return "\n".join(out)
def _crosswalk_table():
    ch=RC["cohort"]
    rows=[("In both cohorts",f"{ch['in_main']} of {ch['n']}"),
          ("In the recovery cohort only",str(ch["recovery_only"])),
          ("Near-sole in both",str(ch["shared_sole"])),
          ("Near-sole in the analysis cohort only, panel too short here",
           str(ch["main_only_sole"])),
          ("Near-sole in the recovery cohort only, no observed quarter in the first six",
           str(ch["recovery_only_sole"]))]
    return "\n".join(["| | Markets |","|---|---|"]+[f"| {a} | {b} |" for a,b in rows])
OMS=L("outcome_missing_sensitivity.json")
def _recovery_table():
    return "\n".join(["| | Before | After |","|---|---|---|",
      f"| Minority markets crossing 50% | 15 | {len(RC['50%']['minority_rows'])} |",
      f"| Minority markets crossing 90% | 40 | {len(RC['90%']['minority_rows'])} |",
      f"| Log-rank p, 50% | 0.188 | {RC['50%']['logrank_p']:.3f} |",
      f"| Log-rank p, 90% | 0.002 | {RC['90%']['logrank_p']:.3f} |",
      f"| Shared-cohort p, 90% | 0.002 | "
      f"{RC['90%']['shared_cohort']['logrank_p']:.3f} |"])
def _outcome_table():
    return "\n".join(["| Reading of an absent post-event quarter | Collapses of "
      f"{OMS['zero']['n']} | Rate |","|---|---|---|",
      f"| Zero, which the paper reports | {OMS['zero']['collapsed']} | "
      f"{100*OMS['zero']['rate']:.1f}% |",
      f"| Ten prescriptions, the primary-suppression ceiling | {OMS['ten']['collapsed']} | "
      f"{100*OMS['ten']['rate']:.1f}% |",
      f"| Averaged over observed quarters only | {OMS['observed']['collapsed']} | "
      f"{100*OMS['observed']['rate']:.1f}% |"])
NA=L("ndc_composition_audit.json")
def _ndccat_table():
    return "\n".join(["| Category | Groups |","|---|---|",
      f"| Two or more different populated substance sets | "
      f"{NA['combinations_with_conflicting_populated_sets']} |",
      f"| One populated set plus records with none | "
      f"{NA['combinations_mixed_populated_and_missing']} |",
      f"| No usable substance set for any member | "
      f"{NA['combinations_with_no_usable_substance_set']} |",
      f"| Fully populated and consistent | "
      f"{NA['combinations_fully_populated_and_consistent']} |"])
def _ndcsplit_table():
    a=NA["panel_linked"]; u=NA["not_panel_linked"]
    return "\n".join(["| Population | Product codes | Groups | Conflicting groups |",
      "|---|---|---|---|",
      f"| Assigned a panel market | {a['product_codes']:,} | {a['groups']} | "
      f"{a['conflicting_groups']} |",
      f"| Not assigned a panel market | {u['product_codes']:,} | {u['groups']} | "
      f"{u['conflicting_groups']} |"])
BLOCKS={"ladder":_ladder_table,"crosswalk":_crosswalk_table,
        "recovery":_recovery_table,"outcome":_outcome_table,
        "ndccat":_ndccat_table,"ndcsplit":_ndcsplit_table}

# How many near-sole and minority markets ever cross each threshold, from the rows the
# recovery stage releases, so the letter's crossing counts come from the same place as
# the curves.
_cross90_sole=len(RC["90%"]["sole_rows"]); _cross90_min=len(RC["90%"]["minority_rows"])

# Inline figures the letter states in prose. Each pattern must match exactly once.
SUBS=[
 (r"[\d,]+ of [\d,]+ have a usable normalised substance set, and \d+\nof the \d+ represented market keys",
  f"{NA['panel_linked']['products_with_a_usable_substance_set']:,} of "
  f"{NA['panel_linked']['product_codes']:,} have a usable normalised substance set, and "
  f"{NA['panel_linked']['market_keys_with_no_usable_substance_set']}\nof the "
  f"{NA['panel_linked']['market_keys']} represented market keys"),
 (r"among those \d+, and the cause is our own cleaning rule",
  f"among those {NA['panel_linked']['market_keys_with_no_usable_substance_set']}, and the "
  f"cause is our own cleaning rule"),
 (r"[\w-]+ of the nineteen observed events have at least one suppressed",
  _w(OMS["events_affected"]).capitalize()+" of the nineteen observed events have at "
  "least one suppressed"),
 (r"censored on the quarter they crossed are \w+ at 50 percent and \w+ at 90",
  f"censored on the quarter they crossed are "
  f"{_w(RC['censored_at_crossing']['50%']['minority'])} at 50 percent and "
  f"{_w(RC['censored_at_crossing']['90%']['minority'])} at 90"),
 (r"the old manifest held \w+ and \w+\.",
  "the old manifest held eight and six."),
 (r"\| Raw ingredient-and-route keys \| [\d,]+ \| [\d,]+ \|",
  f"| Raw ingredient-and-route keys | 3,295 | {NUM['raw_route_keys']:,} |"),
 (r"\| Markets after normalisation \| [\d,]+ \| [\d,]+ \|",
  f"| Markets after normalisation | 2,916 | {SPEC['C']['markets']:,} |"),
 (r"\| Dispensing volume with an explicit route, by year \| [\d.]+ to [\d.]+% \| [\d.]+ to [\d.]+% \|",
  f"| Dispensing volume with an explicit route, by year | 94.4 to 95.8% | "
  f"{SEN['route_coverage_volume_min']} to {SEN['route_coverage_volume_max']}% |"),
 (r"\| Market-quarters at strength granularity \| [\d,]+ \| [\d,]+ \|",
  f"| Market-quarters at strength granularity | 200,534 | {SEN['strength_market_quarters']:,} |"),
 (r"\| Near-sole volume at strength granularity \| [\d.]+% \| [\d.]+% \|",
  f"| Near-sole volume at strength granularity | 19.96% | "
  # sensitivities.json already stores this as a percentage; multiplying by 100 again
  # printed 1657.00% in the letter while the manuscript printed 16.57
  f"{SEN['strength_nearsole_vol']:.2f}% |"),
 (r"absorbed duplicate keys is still [\d,]+",
  f"absorbed duplicate keys is still {NUM['keys_absorbed']:,}"),
 (r"removes \w+ of the \w+-\w+", 
  f"removes {_w(FL['failed_baseline'])} of the {_w(FL['in_window'])}"),
 (r"p = [\d.]+ on [\w-]+ near-sole and [\w-]+ minority-loss markets that cross, against p = [\d.]+ on\nthe full cohort",
  f"p = {RC['90%']['shared_cohort']['logrank_p']:.3f} on "
  f"{_w(RC['90%']['shared_cohort']['sole_n'])} near-sole and "
  f"{_w(RC['90%']['shared_cohort']['minority_n'])} minority-loss markets that cross, against "
  f"p = {RC['90%']['logrank_p']:.3f} on\nthe full cohort"),
 (r"repeat the test on the [\d,]+ markets the two cohorts share",
  f"repeat the test on the {RC['cohort']['in_main']:,} markets the two cohorts share"),
 (r"At 50 percent it gives p = [\d.]+ against p = [\d.]+\.",
  f"At 50 percent it gives p = {RC['50%']['shared_cohort']['logrank_p']:.3f} against "
  f"p = {RC['50%']['logrank_p']:.3f}."),
 (r"five prescriptions leaves [\d,]+ events and \d+\nnear-sole exits",
  f"five prescriptions leaves {_SS['events'][1]:,} events and {_SS['near_sole'][1]}\n"
  f"near-sole exits"),
 (r"leaves [\d,]+ and \d+\. The published",
  f"leaves {_SS['events'][2]:,} and {_SS['near_sole'][2]}. The published"),
 (r"observed near-sole cohort is \d+ events with \d+ collapses whether",
  f"observed near-sole cohort is {_SS['observed'][2]} events with {_SS['collapsed'][2]} "
  f"collapses whether"),
 (r"of the [\d,]+ events, [\d,]+ have the full twelve quarters and [\d,]+ are",
  f"of the {_PW['events']:,} events, {_PW['full_twelve_quarters']:,} have the full twelve "
  f"quarters and {_PW['truncated']:,} are"),
 (r"\d+ of \d+ have the full window",
  f"{_PW['near_sole_full_twelve']} of {_PW['near_sole_events']} have the full window"),
 (r"fully evaluate leaves [\d,]+ events",
  f"fully evaluate leaves {_PW['events_full_window_only']:,} events"),
 (r"becomes \w+ events and the collapse\ncount \w+, a rate of [\d.]+ percent against [\d.]+\.",
  f"becomes {_w(TY['typos_corrected']['observed_cohort'])} events and the collapse\n"
  f"count {_w(TY['typos_corrected']['collapsed'])}, a rate of "
  f"{100*TY['typos_corrected']['collapse_rate']:.1f} percent against "
  f"{100*TY['as_published']['collapse_rate']:.1f}."),
 (r"\w+ merge groups have no structured substance set",
  f"{_w(VAL['untestable'])} merge groups have no structured substance set"),
 (r"[\w-]+ of [\w-]+ near-sole markets cross below 90 percent against\n[\w-]+ of [\w-]+ minority-loss markets",
  f"{_w(_cross90_sole)} of {_w(RC['cohort']['sole'])} near-sole markets cross below 90 "
  f"percent against\n{_w(_cross90_min)} of {_w(RC['cohort']['minority'])} minority-loss markets"),
 (r"Three citations carry verified URLs",
  f"{_w(sum(1 for v in _SRC.values() if v.get('url'))).capitalize()} citations carry verified URLs"),
]


BLOCK_RE=r"<!-- GENERATED:%s -->\n.*?\n<!-- END:%s -->"
p=f"{_ROOT}/springer/response_to_reviewer.md"; L=open(p).read()
fails=[]; n=0
for name,fn in BLOCKS.items():
    pat=BLOCK_RE % (name,name)
    if len(re.findall(pat,L,re.S))!=1:
        fails.append(f"table block {name!r} not found exactly once in the letter")
    else:
        L=re.sub(pat, lambda _m,_f=fn,_n=name:
                 f"<!-- GENERATED:{_n} -->\n{_f()}\n<!-- END:{_n} -->", L, flags=re.S)
        n+=1
for pat,rep in SUBS:
    hits=len(re.findall(pat,L))
    if hits!=1: fails.append(f"pattern matched {hits} times, expected 1: {pat[:62]}")
    else:
        L=re.sub(pat, rep.replace("\\","\\\\"), L); n+=1
if fails:
    print(f"{len(fails)} LETTER SUBSTITUTIONS DID NOT APPLY:")
    for f in fails: print("   "+f)
    print("\nEdit emit_letter_numbers.py to match the letter's wording, or fix the letter.")
    sys.exit(1)
open(p,"w").write(L)
print(f"{n} figures and table blocks in the response letter refreshed from results")

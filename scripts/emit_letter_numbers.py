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
BLOCKS={"ladder":_ladder_table,"crosswalk":_crosswalk_table}

# How many near-sole and minority markets ever cross each threshold, from the rows the
# recovery stage releases, so the letter's crossing counts come from the same place as
# the curves.
_cross90_sole=len(RC["90%"]["sole_rows"]); _cross90_min=len(RC["90%"]["minority_rows"])

# Inline figures the letter states in prose. Each pattern must match exactly once.
SUBS=[
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
  f"{100*SEN['strength_nearsole_vol']:.2f}% |"),
 (r"absorbed duplicate keys is still [\d,]+",
  f"absorbed duplicate keys is still {NUM['keys_absorbed']:,}"),
 (r"removes \w+ of the \w+-\w+", 
  f"removes {_w(FL['failed_baseline'])} of the {_w(FL['in_window'])}"),
 (r"p = [\d.]+ on \w+ near-sole and \w+ minority-loss markets that cross, against p = [\d.]+ on\nthe full cohort",
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
 (r"\w+ of \w+ near-sole markets cross below 90 percent against\n\w+ of \w+-\w+ minority-loss markets",
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

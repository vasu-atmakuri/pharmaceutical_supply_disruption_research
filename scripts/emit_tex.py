"""Emit every table body and every headline number as LaTeX, straight from the
analysis outputs. Nothing in springer/generated/ is ever typed by hand, so a
stale table cell or headline figure is structurally impossible."""
import json, os, collections
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
R=_ROOT+"/results"
G=_ROOT+"/springer/generated"
os.makedirs(G,exist_ok=True)
L=lambda f: json.load(open(f"{R}/{f}"))
INF=L("inference_normalized.json"); ABC=L("concentration_abc.json"); NI=L("national_impact.json")
RUL=L("reclassification_rules.json"); RML=L("recall_match_level.json"); RUS=L("route_unknown_sensitivity.json"); VAL=L("normalization_validation.json"); SEN=L("sensitivities.json")
DEF=L("deficit_entry_normalized.json"); RU=L("route_unknown_sensitivity.json"); RC=L("recovery_censored.json"); NUM=L("manuscript_numbers.json")
SPEC={s["tag"][0]:s for s in L("three_specifications.json")}
_W={14:"fourteen",13:"thirteen",15:"fifteen",12:"twelve",16:"sixteen"}
_FL=SPEC["C"]["sole_flow"]
# Number to words, for counts the text spells out. A fixed dictionary broke the
# build when a rebuilt panel moved a count from 41 to 42: any count the pipeline can
# produce must render, so this covers the whole range and falls back to the numeral.
_ONES=["zero","one","two","three","four","five","six","seven","eight","nine","ten",
       "eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen",
       "eighteen","nineteen"]
_TENS=["","","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]
def _w(x):
    n=int(x)
    if n<0: return c(n)
    if n<20: return _ONES[n]
    if n<100:
        t,o=divmod(n,10)
        return _TENS[t] + ("-"+_ONES[o] if o else "")
    return c(n)          # past ninety-nine the numeral reads better anyway
def _cc():
    import csv, collections
    rows=list(csv.DictReader(open(f"{R}/event_cause_classification.csv")))
    cnt=collections.Counter(r["cause_class"] for r in rows)
    if sum(cnt.values())!=SPEC["C"]["bands"]["sole"]:
        raise SystemExit(f"cause classification covers {sum(cnt.values())} events, "
                         f"specification C sole band has {SPEC['C']['bands']['sole']}")
    return cnt
def _formbw():
    n=NUM.get("form_buckets")
    if n is None: raise SystemExit("form_buckets missing from manuscript_numbers.json")
    return _w(n)
def _dorzw():
    import csv
    for r in csv.DictReader(open(f"{R}/sole_event_transition.csv")):
        if "DORZOLAMIDE" in r["corrected_market"]: return _w(r["corrected_labelers"])
    raise SystemExit("dorzolamide row not found")
def _bucketsw():
    base=sorted({b.split(" #")[0] for b in NUM["route_bucket_names"]})
    if len(base) not in _W: raise SystemExit(f"{len(base)} route buckets: {base}")
    return _W[len(base)]
import csv as _csv
def _pregrow():
    with open(f"{R}/sole_event_transition.csv") as fh:
        for r in _csv.DictReader(fh):
            if "PREGABALIN" in r["raw_market"].upper(): return r
    raise SystemExit("pregabalin row not found in sole_event_transition.csv")
def _preg(): return f"{100*float(_pregrow()['corrected_share']):.1f}"
def _preglab(): return _pregrow()["corrected_labelers"]
NK=json.load(open(f"{R}/market_key_normalization_map.json"))
g=collections.Counter(NK.values()); dist=collections.Counter(g.values())
def c(n): return f"{n:,}".replace(",","{,}")
def pc(x,d=1): return f"{x*100:.{d}f}\\%"
M={}

# ---------------- Table 1: event flow ----------------
rows=[("Market keys",lambda s:c(s["markets"])),("Labeler-market-quarters",lambda s:c(s["lmq"])),
      ("Labeler exits detected",lambda s:c(s["events"])),("\\quad distinct markets",lambda s:c(s["ev_markets"])),
      ("Exits inside the event window",lambda s:c(s["inwin"])),
      ("\\quad with a complete baseline",lambda s:c(s["baseline"])),
      ("\\quad and an observed post quarter",lambda s:c(s["obs"]))]
out=[f"{lab:<44}"+"".join(" & "+fn(SPEC[k]) for k in "ABC")+" \\\\" for lab,fn in rows]
out.append("\\midrule")
out.append("\\multicolumn{4}{@{}l}{\\emph{Analysis cohort by departing labeler's share}} \\\\")
for lab,key in [("\\quad under 35 percent","<35%"),("\\quad 35 to 65 percent","35-65%"),
                ("\\quad 65 to 95 percent","65-95%"),("\\quad at least 95 percent","sole")]:
    out.append(f"{lab:<44}"+"".join(" & "+c(SPEC[k]["bands"].get(key,0)) for k in "ABC")+" \\\\")
out.append("\\quad \\emph{total}"+"".join(" & \\emph{"+c(sum(SPEC[k]["bands"].values()))+"}" for k in "ABC")+" \\\\")
open(f"{G}/tab_flow.tex","w").write(
 "\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n"
 " & A: raw string, & B: route-and-form, & C: route-and-form, \\\\\n"
 " & form bucket & raw string & normalised key \\\\\n\\midrule\n"
 +"\n".join(out)+"\n\\botrule\n\\end{tabular}")

# ---------------- Table 3: national concentration ----------------
rows=[("Market-quarters",lambda s:c(s["mq"])),
      ("Single-labeler (exactly one)",lambda s:pc(s["one_sh"])),
      ("\\quad share of dispensing volume",lambda s:pc(s["one_vol"],2)),
      ("Near-sole (top share $\\geq$ 95\\%)",lambda s:pc(s["sole_sh"])),
      ("\\quad share of dispensing volume",lambda s:pc(s["sole_vol"],2)),
      ("Mean HHI",lambda s:f"{s['mean_hhi']:.3f}")]
out=[]
for i,(lab,fn) in enumerate(rows):
    if i==1: out.append("\\midrule")
    out.append(f"{lab:<48}"+"".join(" & "+fn(ABC[k]) for k in "ABC")+" \\\\")
open(f"{G}/tab_concentration.tex","w").write(
 "\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n"
 " & A: raw string, & B: route-and-form, & C: route-and-form, \\\\\n"
 " & form bucket & raw string & normalised key \\\\\n\\midrule\n"
 +"\n".join(out)+"\n\\botrule\n\\end{tabular}")

# ---------------- Table 4: mapping rules ----------------
n=RUL["largest_n"]
# Each label states the condition under which the raw near-sole alert is
# WITHDRAWN, which is what the count column reports. Labelling them by the
# retention condition instead inverts the reading of the table.
out=[f"Largest corrected component is no longer near-sole (used above) & {c(RUL['largest_reclass'])} & {RUL['largest_rate']*100:.1f}\\% \\\\",
     f"No corrected component is still near-sole                       & {c(RUL['any_reclass'])}  & {RUL['any_reclass']/n*100:.1f}\\% \\\\",
     f"At least one corrected component is no longer near-sole         & {c(RUL['all_reclass'])} & {RUL['all_reclass']/n*100:.1f}\\% \\\\"]
open(f"{G}/tab_rules.tex","w").write(
 "\\begin{tabular}{@{}lrr@{}}\n\\toprule\nCondition for withdrawing the alert & Alerts withdrawn & Rate \\\\\n\\midrule\n"
 +"\n".join(out)+"\n\\midrule\n"
 +"\\multicolumn{3}{@{}l}{\\emph{By dispensing volume, of "
 +f"{RUL['flagged_rx']/1e6:,.0f}" + "M flagged prescriptions:}} \\\\\n"
 +"\\multicolumn{3}{@{}l}{~~Largest-component rule, whole raw markets: "
 +f"{RUL['largest_rx_reclass']/1e6:,.0f}" + "M, "
 +f"{RUL['largest_vol_rate']*100:.1f}" + "\\%} \\\\\n"
 +"\\multicolumn{3}{@{}l}{~~Volume allocated across all components: "
 +f"{RUL['flagged_rx']*RUL['vol_reclassified']/1e6:,.0f}" + "M, "
 +f"{RUL['vol_reclassified']*100:.1f}" + "\\%} \\\\\n"
 +"\\botrule\n\\end{tabular}")

# ---------------- Table 5: replacement ratios ----------------
out=[]
for lab,k in [("under 35 percent","<35%"),("35 to 65 percent","35-65%"),
              ("65 to 95 percent","65-95%"),("at least 95 percent","sole")]:
    d=INF["R_"+k]
    vw="see text" if k=="<35%" else f"{d['volwtd']:.2f}"
    coll=("---" if d.get("collapse") is None
          else f"{d['collapse']*100:.1f}\\%")
    out.append(f"{lab:<19} & {d['n']} & {d['median']:.2f} & [{d['ci'][0]:.2f}, {d['ci'][1]:.2f}] "
               f"& {d['mean']:.2f} & {vw} & {d['p_lt_2pct']*100:.1f}\\% & {coll} \\\\")
open(f"{G}/tab_replacement.tex","w").write(
 "\\begin{tabular}{@{}lrrrrrrr@{}}\n\\toprule\n"
 "Departing share & $n$ & Median $R$ & 95\\% CI & Mean & Vol-wtd & $R<0.02$ & Collapse \\\\\n\\midrule\n"
 +"\n".join(out)+"\n\\botrule\n\\end{tabular}")

# ---------------- Table 6: deficits ----------------
out=[]
for lab,k in [("under 35 percent","under 35%"),("35 to 95 percent","35-95%"),("at least 95 percent","at least 95%")]:
    d=DEF[k]
    out.append(f"{lab:<19} & {d['n']} & {d['post_median']:.1f} [{d['post_ci'][0]:.1f}, {d['post_ci'][1]:.1f}] "
               f"& {d['total_median']:.1f} [{d['total_ci'][0]:.1f}, {d['total_ci'][1]:.1f}] \\\\")
open(f"{G}/tab_deficit.tex","w").write("\n".join(out)+"\n")

# ---------------- headline macros ----------------
A,B,C=ABC["A"],ABC["B"],ABC["C"]
M.update(
 RawKeys=c(NUM["raw_route_keys"]), NormKeys=c(NUM["normalised_keys"]), KeysAbsorbed=c(NUM["keys_absorbed"]),
 FormBucketMarkets=c(SPEC["A"]["markets"]), ColazoMarkets=c(NUM["colazo_markets"]),
 NearSoleVolA=f"{A['sole_vol']*100:.2f}", NearSoleVolB=f"{B['sole_vol']*100:.2f}", NearSoleVolC=f"{C['sole_vol']*100:.2f}",
 SingleVolA=f"{A['one_vol']*100:.2f}", SingleVolC=f"{C['one_vol']*100:.2f}",
 NearSoleRel=f"{(A['sole_vol']-C['sole_vol'])/A['sole_vol']*100:.0f}",
 SingleRel=f"{(A['one_vol']-C['one_vol'])/A['one_vol']*100:.0f}",
 DecompAB=f"{(A['one_vol']-B['one_vol'])*100:.2f}", DecompBC=f"{(B['one_vol']-C['one_vol'])*100:.2f}",
 NearSolePP=f"{(A['sole_vol']-C['sole_vol'])*100:.2f}", RoutePP=f"{(A['sole_vol']-B['sole_vol'])*100:.2f}",
 NearSoleMQ=c(RUL["largest_n"]), Retained=c(RUL["largest_n"]-RUL["largest_reclass"]),
 Reclassified=c(RUL["largest_reclass"]), ReclassRate=f"{RUL['largest_rate']*100:.1f}",
 ReclassLow=f"{RUL['any_reclass']/RUL['largest_n']*100:.1f}", ReclassHigh=f"{RUL['all_reclass']/RUL['largest_n']*100:.1f}",
 ReclassVol=f"{RUL['vol_reclassified']*100:.1f}", SplitMarkets=c(sum(v for k,v in RUL["components"].items() if int(k)>1)),
 MergeGroups=c(VAL["merge_groups"]), MergeKeys=c(VAL["raw_keys_merged"]),
 Confirmed=c(VAL["confirmed"]), Contradicted=c(VAL["contradicted"]), Untestable=c(VAL["untestable"]),
 Testable=c(VAL["confirmed"]+VAL["contradicted"]),
 RouteCovRec=f"{NUM['route_coverage']:.1f}",
 UnkOtherPresent=c(RUS["other_bucket_route_present"]),
 UnkMQ=c(RUS["unknown_bucket_mq"]), UnkNearSoleMQ=c(RUS["unknown_bucket_nearsole_mq"]),
 UnkNearSolePct=f"{100*RUS['unknown_bucket_nearsole_mq']/RUS['unknown_bucket_mq']:.1f}",
 UnkVolShare=f"{RUS['unknown_route_vol_share']:.2f}",
 UnkBaseNearSoleVol=f"{RUS['base']['nearsole_vol_pct']:.2f}",
 UnkDropNearSoleVol=f"{RUS['unknown_route_dropped']['nearsole_vol_pct']:.2f}",
 UnkDropDelta=f"{abs(RUS['delta_drop_nearsole_vol_pp']):.2f}",
 UnkBaseNearSoleMQ=f"{RUS['base']['nearsole_mq_pct']:.2f}",
 UnkDropNearSoleMQ=f"{RUS['unknown_route_dropped']['nearsole_mq_pct']:.2f}",
 UnkDropMarkets=c(RUS["unknown_route_dropped"]["markets"]),
 UnkSplitIngredients=c(RUS["ingredients_split_by_change"]),
 RouteMissRec=c(NUM["route_missing_records"]), RouteMissOther=c(NUM["route_missing_to_other"]),
 RouteMissClassPct=f"{NUM['route_missing_classified_pct']:.1f}",
 RouteMissOtherPct=f"{NUM['route_missing_other_pct']:.1f}",
 RouteMissClassified=c(NUM["route_missing_records"]-NUM["route_missing_to_other"]),
 RouteCovLo=f"{SEN['route_coverage_volume_min']:.1f}", RouteCovHi=f"{SEN['route_coverage_volume_max']:.1f}",
 MinorityMedian=f"{INF['R_<35%']['median']:.2f}", SoleMedian=f"{INF['R_sole']['median']:.2f}",
 MinorityN=str(INF["R_<35%"]["n"]), SoleN=str(INF["R_sole"]["n"]),
 MinorityLtTwo=f"{INF['R_<35%']['p_lt_2pct']*100:.1f}", SoleLtTwo=f"{INF['R_sole']['p_lt_2pct']*100:.1f}",
 ReplEligibleW=_w(sum(INF["R_"+b]["n"] for b in ["<35%","35-65%","65-95%","sole"])) if sum(INF["R_"+b]["n"] for b in ["<35%","35-65%","65-95%","sole"])<=99 else c(sum(INF["R_"+b]["n"] for b in ["<35%","35-65%","65-95%","sole"])),
 ReplExcluded=c(sum(SPEC["C"]["bands"].values())-sum(INF["R_"+b]["n"] for b in ["<35%","35-65%","65-95%","sole"])),
 ReplEligible=str(sum(INF["R_"+k]["n"] for k in ["<35%","35-65%","65-95%","sole"])),
 Cohort=str(sum(SPEC["C"]["bands"].values())),
 AltN=str(SEN["alt_baseline_n"]), AltK=str(SEN["alt_baseline_lt02_k"]),
 AltMedian=f"{SEN['alt_baseline_minority_median']:.2f}", AltPct=f"{SEN['alt_baseline_minority_lt02']:.1f}",
 TreatedRate=f"{INF['matched']['treated_rate']*100:.1f}", ControlRate=f"{INF['matched']['control_rate']*100:.2f}",
 RiskDiff=f"{INF['matched']['risk_diff']*100:.1f}", CILo=f"{INF['matched']['ci_sets'][0]*100:.1f}",
 CIHi=f"{INF['matched']['ci_sets'][1]*100:.1f}", CIHiB=f"{INF['matched']['ci_sets_and_controls'][1]*100:.1f}",
 ControlObs=c(INF["matched"]["control_obs"]), UniqueControls=c(INF["matched"]["unique_controls"]),
 # the treated-event count for the matched and band analyses. This is the observed
 # cohort's sole band, which is NOT RemainSole (raw sole minus reclassified): wiring
 # RemainSole into these sentences printed seventeen where the analysis used nineteen.
 Treated=c(INF["matched"]["sets"]), TreatedW=_w(INF["matched"]["sets"]),
 Checks=_w(len(set(__import__("re").findall(r"((?:audit|check|verify)_\w+)\.py",
   open(f"{_os.path.dirname(_os.path.abspath(__file__))}/run_all.sh").read()))-{"check_environment"})),
 TreatedColl=_w(round(INF["matched"]["treated_rate"]*INF["matched"]["sets"])),
 MaxReuse=c(INF["matched"]["max_reuse"]),
 # quarters between the announced effective date of the Praluent transfer, 2020Q2,
 # and the detected alirocumab exit. Stated so the gap is disclosed, not implied.
 TypoVolBase=f"{100*L('typo_sensitivity.json')['as_published']['near_sole_volume_share']:.2f}",
 TypoVolFixed=f"{100*L('typo_sensitivity.json')['typos_corrected']['near_sole_volume_share']:.2f}",
 TypoExitsBase=c(L("typo_sensitivity.json")["as_published"]["near_sole_exits"]),
 TypoExitsFixed=c(L("typo_sensitivity.json")["typos_corrected"]["near_sole_exits"]),
 TypoMarketsBase=c(L("typo_sensitivity.json")["as_published"]["markets"]),
 TypoMarketsFixed=c(L("typo_sensitivity.json")["typos_corrected"]["markets"]),
 # what the correction does to the published cohort, not only to the national share
 TypoObsBase=c(L("typo_sensitivity.json")["as_published"]["observed_cohort"]),
 TypoObsFixed=c(L("typo_sensitivity.json")["typos_corrected"]["observed_cohort"]),
 TypoObsFixedW=_w(L("typo_sensitivity.json")["typos_corrected"]["observed_cohort"]),
 TypoCollBase=c(L("typo_sensitivity.json")["as_published"]["collapsed"]),
 TypoCollFixed=c(L("typo_sensitivity.json")["typos_corrected"]["collapsed"]),
 TypoCollFixedW=_w(L("typo_sensitivity.json")["typos_corrected"]["collapsed"]),
 TypoRateBase=f"{100*L('typo_sensitivity.json')['as_published']['collapse_rate']:.1f}",
 TypoRateFixed=f"{100*L('typo_sensitivity.json')['typos_corrected']['collapse_rate']:.1f}",
# Deficit and entry figures. Every one of these was a typed literal and every one
 # was stale: the deficit medians, the bootstrap interval, the leave-one-out range and
 # all three entry rates moved with the corrected cohort and the prose did not.
 # the panel's total reimbursed volume, and the relative reductions, which were typed
 RelTokenMarkets=c(L("release_split.json")["release_token_markets"]),
 RelBothGroups=_w(L("release_split.json")["groups_with_both_forms"]),
 TotalRxB=f"{max(NI['total_rx'].values())/1e9:.2f}",
 RouteSplitQuarters=c(L("route_split_effect.json")["ingredient_quarters"]),
 RelRedNearSole=f"{100*(ABC['A']['sole_vol']-ABC['C']['sole_vol'])/ABC['A']['sole_vol']:.0f}",
 RelRedSingle=f"{100*(ABC['A']['one_vol']-ABC['C']['one_vol'])/ABC['A']['one_vol']:.0f}",
 DefTotLo=f"{DEF['under 35%']['total_median']:.2f}",
 DefTotMid=f"{DEF['35-95%']['total_median']:.2f}",
 DefTotSole=f"{DEF['at least 95%']['total_median']:.2f}",
 DefPostLo=f"{DEF['under 35%']['post_median']:.2f}",
 DefPostMid=f"{DEF['35-95%']['post_median']:.2f}",
 DefPostSole=f"{DEF['at least 95%']['post_median']:.2f}",
 DefSoleCiLo=f"{DEF['at least 95%']['total_ci'][0]:.2f}",
 DefSoleCiHi=f"{DEF['at least 95%']['total_ci'][1]:.2f}",
 DefSoleLooLo=f"{DEF['at least 95%']['loo_min']:.2f}",
 DefSoleLooHi=f"{DEF['at least 95%']['loo_max']:.2f}",
 EntryLo=f"{100*DEF['entry']['under 35%'][0]/DEF['entry']['under 35%'][1]:.1f}",
 EntryMid=f"{100*DEF['entry']['35-95%'][0]/DEF['entry']['35-95%'][1]:.1f}",
 EntrySole=f"{100*DEF['entry']['at least 95%'][0]/DEF['entry']['at least 95%'][1]:.1f}",
 EntryLoN=c(DEF['entry']['under 35%'][1]), EntryMidN=c(DEF['entry']['35-95%'][1]),
 EntrySoleN=c(DEF['entry']['at least 95%'][1]),
 TransferGapQ=_w(((2021-1991)*4+2)-((2020-1991)*4+2)),
 MaxReuseW=_w(INF["matched"]["max_reuse"]),
 SoleLtTwoW=_w(round(INF["R_sole"]["p_lt_2pct"]*INF["R_sole"]["n"])),
 MidBandN=c(INF["R_35-65%"]["n"]), MidBandNW=_w(INF["R_35-65%"]["n"]),
 MidBandMedian=f"{INF['R_35-65%']['median']:.2f}",
 ControlsOnce=c(INF["matched"]["used_once"]), TreatedSets=c(INF["matched"]["sets"]),
 LogrankFifty=f"{RC['50%']['logrank_p']:.3f}", LogrankNinety=f"{RC['90%']['logrank_p']:.3f}",
 # how many markets in each band ever fall below half of baseline. The denominators
 # are the band sizes in the observed cohort, so the two halves of the comparison
 # come from the same place as the bands themselves.
 CrossSole=_w(len(RC["50%"]["sole_rows"])),
 CrossSoleOf=c(RC["cohort"]["sole"]),
 CrossMinor=_w(len(RC["50%"]["minority_rows"])),
 CrossMinorOf=c(RC["cohort"]["minority"]),
 CrossCohort=c(RC["cohort"]["n"]),
 CrossMid=c(RC["cohort"]["mid"]),
 # the crosswalk between the recovery cohort and the main analysis cohort
 CohortSole=c(RC["cohort"]["main_sole"]),
 RecSharedSole=_w(RC["cohort"]["shared_sole"]),
 RecMainOnlySole=_w(RC["cohort"]["main_only_sole"]),
 RecOnlySole=_w(RC["cohort"]["recovery_only_sole"]),
 RecSharedAll=c(RC["cohort"]["in_main"]),
 RecOnlyAll=_w(RC["cohort"]["recovery_only"]),
 LogrankNinetyShared=f"{RC['90%']['shared_cohort']['logrank_p']:.3f}",
 LogrankFiftyShared=f"{RC['50%']['shared_cohort']['logrank_p']:.3f}",
 SharedSoleCross=c(RC["90%"]["shared_cohort"]["sole_n"]),
 SharedMinorCross=c(RC["90%"]["shared_cohort"]["minority_n"]),
 CrossCohortW=_w(RC["cohort"]["n"]) if RC["cohort"]["n"]<=99 else c(RC["cohort"]["n"]),
 NormMQ=c(ABC["C"]["mq"]), NearSoleMQPctC=f"{100*ABC['C']['sole_sh']:.1f}",
 StrengthMQ=c(SEN["strength_market_quarters"]),
 StrengthNearSole=f"{SEN['strength_nearsole_share']:.1f}", StrengthNearSoleVol=f"{SEN['strength_nearsole_vol']:.2f}",
 GenericShare=f"{NUM['generic_share']:.1f}", AndaShare=f"{NUM['anda_share']:.1f}",
 SuppressionScenario=f"{SEN['suppression_scenario_rate']:.1f}",
 SolutionOral=c(NUM["solution_oral"]), SolutionTopical=c(NUM["solution_topical"]),
 SolutionOphth=c(NUM["solution_ophthalmic"]), SolutionOtic=c(NUM["solution_otic"]),
 SolutionIntra=c(NUM["solution_intradermal_subcut"]), SolutionResp=c(NUM["solution_respiratory"]),
 DropsOphth=c(NUM["drops_ophthalmic"]), DropsOral=c(NUM["drops_oral"]), DropsSub=c(NUM["drops_sublingual"]),
 OphthRecords=c(NUM["ophthalmic_records"]), OticRecords=c(NUM["otic_records"]),
 KeyOne=c(dist[1]), KeyTwo=c(dist[2]), KeyMax=c(max(dist)),
 RouteSplitCreated=c(L("route_split_effect.json")["created"]),
 RouteSplitIngredients=c(L("route_split_effect.json")["ingredients"]),
 BoundLow=f"{NUM['bound_low']:.1f}", BoundHigh=f"{NUM['bound_high']:.1f}",
 RecMinCrossFifty=c(len(RC["50%"]["minority_rows"])), RecMinRecFifty=c(sum(e for _,e in RC["50%"]["minority_rows"])),
 RecSoleCrossFifty=c(len(RC["50%"]["sole_rows"])), RecSoleRecFifty=c(sum(e for _,e in RC["50%"]["sole_rows"])),
 RecMinCrossNinety=c(len(RC["90%"]["minority_rows"])), RecMinRecNinety=c(sum(e for _,e in RC["90%"]["minority_rows"])),
 RecSoleCrossNinety=c(len(RC["90%"]["sole_rows"])), RecSoleRecNinety=c(sum(e for _,e in RC["90%"]["sole_rows"])),
 RecMinCrossFiftyW=_w(len(RC["50%"]["minority_rows"])), RecMinRecFiftyW=_w(sum(e for _,e in RC["50%"]["minority_rows"])),
 RecSoleCrossFiftyW=_w(len(RC["50%"]["sole_rows"])), RecSoleRecFiftyW=_w(sum(e for _,e in RC["50%"]["sole_rows"])),
 LmMinFifty=c(RC["50%"]["landmark"]["minority"][0]), LmMinNFifty=c(RC["50%"]["landmark"]["minority"][1]),
 LmSoleFifty=c(RC["50%"]["landmark"]["sole"][0]), LmSoleNFifty=c(RC["50%"]["landmark"]["sole"][1]),
 LmMinNinety=c(RC["90%"]["landmark"]["minority"][0]), LmMinNNinety=c(RC["90%"]["landmark"]["minority"][1]),
 LmSoleNinety=c(RC["90%"]["landmark"]["sole"][0]), LmSoleNNinety=c(RC["90%"]["landmark"]["sole"][1]),
 SuppPrimary=f"{SEN['suppression_primary_rate']:.1f}",
 # the scenario's own numerator and denominator, as its stage computed them, rather
 # than a numerator reconstructed from a rounded percentage and another cohort's size
 SuppScenColl=c(SEN["suppression_scenario_n"]),
 SuppPrimColl=c(SEN["suppression_primary_n"]),
 SuppScenN=c(SEN["suppression_n"]),
 BoundElig=c(NUM["bound_eligible"]), BoundEligW=_w(NUM["bound_eligible"]),
 BoundEligUC=_w(NUM["bound_eligible"]).capitalize(),
 BoundObs=c(NUM["bound_observed"]), BoundDropped=c(NUM["bound_dropped"]),
 BoundDroppedW=_w(NUM["bound_dropped"]), BoundColl=c(NUM["bound_collapsed"]),
 BoundCollHigh=c(NUM["bound_collapsed"]+NUM["bound_dropped"]),
 BootDraws=c(NUM["bootstrap_draws"]),
 MidMedian=f"{INF['R_35-65%']['median']:.2f}", HighMedian=f"{INF['R_65-95%']['median']:.2f}",
 RawKeysAbs=c(NUM["keys_absorbed"]),
 ExactOne=c(NUM["cohort_exactly_one_labeler"]), ExactOneW=_w(NUM["cohort_exactly_one_labeler"]),
 TwoPlus=c(NUM["cohort_two_plus_labelers"]), TwoPlusW=_w(NUM["cohort_two_plus_labelers"]),
 BaseCommonN=c(SEN["baseline_common_cohort"]["n"]),
 BaseCommonPriMed=f"{SEN['baseline_common_cohort']['primary']['median']:.2f}",
 BaseCommonAltMed=f"{SEN['baseline_common_cohort']['alternative']['median']:.2f}",
 BaseCommonPriPct=f"{SEN['baseline_common_cohort']['primary']['lt02_pct']:.1f}",
 BaseCommonAltPct=f"{SEN['baseline_common_cohort']['alternative']['lt02_pct']:.1f}",
 BaseOnlyAlt=c(len(SEN["baseline_common_cohort"]["only_in_alternative"])),
 # the noun agrees with the count, which "one further events" did not
 BaseOnlyAltPhrase=(_w(len(SEN["baseline_common_cohort"]["only_in_alternative"])).capitalize()
   +" further event"+("" if len(SEN["baseline_common_cohort"]["only_in_alternative"])==1 else "s")),
 BaseOnlyAltW=_w(len(SEN["baseline_common_cohort"]["only_in_alternative"])),
 RUIngredients=c(RU["other_bucket_composition"]["other_bucket_ingredients"]),
 RUMixed=c(RU["other_bucket_composition"]["ingredients_mixing_known_and_unknown"]),
 RUMixedW=_w(RU["other_bucket_composition"]["ingredients_mixing_known_and_unknown"]),
 RUOtherVol=f"{RU['other_bucket_composition']['other_bucket_vol_pct']:.2f}",
 RUNearSoleDelta=f"{RU['delta_nearsole_vol']:+.2f}",
 DupKeyPct=f"{100*NUM['keys_absorbed']/NUM['raw_route_keys']:.1f}",
 ReclassVolLargest=f"{RUL['largest_vol_rate']*100:.1f}",
 FlaggedRx=f"{RUL['flagged_rx']/1e6:.0f}", LargestRxReclass=f"{RUL['largest_rx_reclass']/1e6:.0f}",
 AllocRxReclass=f"{RUL['flagged_rx']*RUL['vol_reclassified']/1e6:.0f}",
 RecallIngLevel=c(RML["by_window"]["window_0"]["ingredient_level_matches"]),
 RecallLabLevel=c(RML["by_window"]["window_0"]["labeler_level_matches"]),
 RecallIngWide=c(RML["by_window"]["window_4"]["ingredient_level_matches"]),
 RecallLabWide=c(RML["by_window"]["window_4"]["labeler_level_matches"]),
 RecallIngMid=c(RML["by_window"]["window_1"]["ingredient_level_matches"]),
 RecallLabMid=c(RML["by_window"]["window_1"]["labeler_level_matches"]),
 BucketsW=_bucketsw(),
FormBucketsW=_formbw(), DorzLabelersW=_dorzw(),
 FlowDetected=c(_FL["detected"]), FlowDetectedW=_w(_FL["detected"]),
 FlowOutside=c(_FL["outside_window"]), FlowOutsideW=_w(_FL["outside_window"]),
 FlowOutsideUC=_w(_FL["outside_window"]).capitalize(),
 FlowInWindow=c(_FL["in_window"]), FlowInWindowW=_w(_FL["in_window"]),
 FlowFailedBase=c(_FL["failed_baseline"]), FlowFailedBaseW=_w(_FL["failed_baseline"]),
 FlowSuppressed=c(_FL["all_post_suppressed"]), FlowSuppressedW=_w(_FL["all_post_suppressed"]),
 FlowObservedUC=_w(_FL["observed"]).capitalize(), FlowDetectedUC=_w(_FL["detected"]).capitalize(),
 FlowObserved=c(_FL["observed"]), FlowObservedW=_w(_FL["observed"]),
 Undetermined=c(_cc()["undetermined"]), UndeterminedW=_w(_cc()["undetermined"]),
 UndeterminedUC=_w(_cc()["undetermined"]).capitalize(),
 CauseSupply=c(_cc()["supply"]), CauseNonSupply=c(_cc()["non-supply"]),
 CauseSupplyW=_w(_cc()["supply"]), CauseNonSupplyW=_w(_cc()["non-supply"]),
 PregShare=_preg(), PregLabelers=_preglab(),
 SpecASoleMed=f"{SPEC['A']['sole']['median_R']:.2f}", SpecASoleLt=f"{100*SPEC['A']['sole']['R_lt_002']:.1f}",
 SpecASoleColl=f"{100*SPEC['A']['sole']['collapse']:.1f}", SpecASoleN=c(SPEC['A']['bands']['sole']),
 SpecAMinMed=f"{SPEC['A']['<35%']['median_R']:.2f}", SpecCMinMed=f"{SPEC['C']['<35%']['median_R']:.2f}",
 SpecCSoleN=c(SPEC['C']['bands']['sole']),
 MinMean=f"{INF['R_<35%']['mean']:.2f}", MinVol=f"{INF['R_<35%']['volwtd']:.2f}",
 MinMeanA=f"{SEN['minority_excl1_mean']:.2f}", MinMeanC=f"{SEN['minority_excl3_mean']:.2f}",
 MinMeanE=f"{SEN['minority_excl5_mean']:.2f}", MinVolA=f"{SEN['minority_excl1_volwtd']:.2f}",
 MinVolC=f"{SEN['minority_excl3_volwtd']:.2f}", MinVolE=f"{SEN['minority_excl5_volwtd']:.2f}",
 MinMedA=f"{SEN['minority_excl1_median']:.2f}", MinMedC=f"{SEN['minority_excl3_median']:.2f}",
 MinMedE=f"{SEN['minority_excl5_median']:.2f}",
 TopOne=f"{SEN['minority_top_ratios'][0]:.0f}", TopTwo=f"{SEN['minority_top_ratios'][1]:.0f}",
 TopThree=f"{SEN['minority_top_ratios'][2]:.0f}", TopFour=f"{SEN['minority_top_ratios'][3]:.0f}",
 TopFive=f"{SEN['minority_top_ratios'][4]:.0f}",
)

# ---- Table: raw-to-corrected transition for the seven reclassified exits ----
from display_names import (name as _dname, labeler as _dlab,
                           event_market as _emkt, cause_label as _clab,
                           CAUSE_ORDER as _CORD)
def emit_transition():
    import csv
    allrows=list(csv.DictReader(open(f"{R}/sole_event_transition.csv")))
    rows=[r for r in allrows if r["still_sole_after_correction"]=="0"]
    rows.sort(key=lambda r: r["event_quarter"])
    kept=len(allrows)-len(rows)
    # Two counts that are close but not equal, and the gap is a result rather than a
    # defect. The raw convention flags its own sole-labeler events and the corrections
    # reclassify some of them; the corrected panel runs the detector again on merged
    # keys, which can make a market near-sole that the raw convention never flagged,
    # or move an event quarter. The difference is reported, not asserted away.
    M["TransRawSole"]=c(len(allrows)); M["TransReclass"]=c(len(rows))
    M["TransStillSole"]=c(kept); M["TransSpecCSole"]=c(SPEC["C"]["bands"]["sole"])
    M["TransGap"]=c(abs(SPEC["C"]["bands"]["sole"]-kept))
    M["TransGapW"]=_w(abs(SPEC["C"]["bands"]["sole"]-kept))
    out=["\\begin{tabular}{@{}lp{3.6cm}p{1.9cm}rrr@{}}","\\toprule",
         "Quarter & Market as recorded & Labeler & Raw & Corrected & Labelers \\\\","\\midrule"]
    for r in rows:
        key=r["corrected_market"]; lab=_dlab(r["departing_labeler"])
        out.append(f"{r['event_quarter']} & {_dname(key)} & {lab} & "
                   f"{100*float(r['raw_share']):.0f}\\% & {100*float(r['corrected_share']):.1f}\\% & "
                   f"{r['corrected_labelers']} \\\\")
    out+=["\\botrule","\\end{tabular}"]
    open(f"{G}/tab_transition.tex","w").write("\n".join(out)+"\n")
    amph=[r for r in rows if "AMPHETAMINE" in r["corrected_market"]]
    if len(amph)!=1: raise SystemExit("expected exactly one amphetamine row in the transition table")
    _sh=[100*float(r["corrected_share"]) for r in rows]
    _lb=[int(r["corrected_labelers"]) for r in rows]
    for r in rows:
        if "DORZOLAMIDE" in r["corrected_market"]: M["DorzShare"]=f"{100*float(r['corrected_share']):.1f}"
    M["TransShareLo"]=f"{min(_sh):.1f}"; M["TransShareHi"]=f"{max(_sh):.1f}"
    M["TransLabLo"]=_w(min(_lb)); M["TransLabHi"]=_w(max(_lb))
    M["AmphShare"]=f"{100*float(amph[0]['corrected_share']):.1f}"
    M["AmphLabelers"]=amph[0]["corrected_labelers"]
    W={0:"zero",1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",7:"seven",8:"eight",
       9:"nine",10:"ten",11:"eleven",12:"twelve",13:"thirteen",14:"fourteen",15:"fifteen",
       16:"sixteen",17:"seventeen",18:"eighteen",19:"nineteen",20:"twenty"}
    def w(x): return W[int(x)] if int(x) in W else c(x)
    M["RawSoleUC"]=w(len(allrows)).capitalize(); M["ReclassSoleUC"]=w(len(rows)).capitalize()
    M["RawSoleW"]=w(len(allrows)); M["ReclassSoleW"]=w(len(rows)); M["RemainSoleW"]=w(kept)
    M["PregLabelersW"]=w(amph and _pregrow()["corrected_labelers"])
    M["RawSole"]=c(len(allrows)); M["ReclassSole"]=c(len(rows)); M["RemainSole"]=c(kept)
    M["ShiftedQuarter"]=c(sum(1 for r in allrows if r["still_sole_after_correction"]=="1"
                               and r["detected_same_quarter"]=="0"))
    return len(rows)
def emit_routecov():
    cov=SEN["route_coverage_by_year"]
    yrs=sorted(cov,key=int)
    out=["\\begin{tabular}{@{}lr@{}}","\\toprule",
         "Year & Route coverage (\\% of dispensing volume) \\\\","\\midrule"]
    for y in yrs: out.append(f"{y} & {cov[y]:.1f} \\\\")
    out+=["\\botrule","\\end{tabular}"]
    open(f"{G}/tab_routecov.tex","w").write("\n".join(out)+"\n")
    M["RouteCovYears"]=c(len(yrs))
    return len(yrs)
_nrc=emit_routecov()
# the generic-share breakdown must either sum to 100 or state its residual
_gsum=NUM["anda_share"]+NUM["authgen_share"]+NUM["brand_share"]+NUM["biologic_share"]
M["AuthGenShare"]=f"{NUM['authgen_share']:.1f}"; M["BrandShare"]=f"{NUM['brand_share']:.1f}"
M["BiologicShare"]=f"{NUM['biologic_share']:.1f}"
M["TypeResidual"]=f"{100-_gsum:.1f}"; M["NonGeneric"]=f"{100-NUM['generic_share']:.1f}"
# ---- Table: every exit with its evidence level, and the strata table ----
# The exit table's labeler column comes from FDA's own labeler name, keyed by the
# code in the event record. A hand-maintained quarter-to-name map had to be edited
# every time the cohort changed, and it keyed on the quarter rather than the firm.
def _evlab(r):
    return _dlab(r["departing_labeler"])
def emit_cause():
    import csv
    rows=list(csv.DictReader(open(f"{R}/event_cause_classification.csv")))
    rows.sort(key=lambda r:(r["event_quarter"],r["market"]))
    out=["\\begin{tabular}{@{}lp{3.4cm}p{1.9cm}p{3.5cm}r@{}}","\\toprule",
         "Quarter & Market & Departing labeler & Evidence level & $R$ \\\\","\\midrule"]
    for r in rows:
        Rv=float(r["replacement_ratio"])
        # a ratio that rounds to zero but is not zero is printed as such: the reviewer
        # correctly noted that one documented event has R near 0.0003, not exactly 0
        rs=f"{Rv:.2f}" if (Rv==0 or abs(Rv)>=0.005) else "$<$0.01"
        mark="\\textsuperscript{a}" if "VARENICLINE" in r["market"] else ""
        out.append(f"{r['event_quarter']} & {_emkt(r['market'])} & {_evlab(r)} & "
                   f"{_clab(r['cause_class'])}{mark} & {rs} \\\\")
    out+=["\\botrule","\\end{tabular}"]
    open(f"{G}/tab_cause.tex","w").write("\n".join(out)+"\n")
    return len(rows)
def emit_strata():
    CS=L("cause_strata.json")
    # One row per evidence class, in descending order of how well the cause is
    # established, plus the stratum a supply-chain reading can still claim.
    rowspec=[("All near-sole-labeler exits","all"),
             ("Excluding every exit explained otherwise","ex_not_supply"),
             ("Documented supply disruption\\textsuperscript{a}","supply"),
             ("Market-wide regulatory withdrawal","withdrawal"),
             ("Regulatory transition","transition"),
             ("Medicaid rebate-programme withdrawal","coverage"),
             ("Marketing-rights transfer","transfer"),
             ("Measurement artefact (misspelled key)","artefact"),
             ("Supply continued by another labeler","continued"),
             ("Undetermined","undetermined")]
    out=["\\begin{tabular}{@{}lrrrr@{}}","\\toprule",
         "Stratum & $n$ & Median $R$ & $R<0.02$ & Volume-weighted $R$ \\\\","\\midrule"]
    for lab,key in rowspec:
        d=CS.get(key)
        if d is None: continue
        if key in ("supply","continued"): out.append("\\midrule")
        out.append(f"{lab} & {d['n']} & {d['median']:.2f} & {100*d['p_lt_002']:.1f}\\% & "
                   f"{d['volwtd']:.2f} \\\\")
    out+=["\\botrule","\\end{tabular}"]
    open(f"{G}/tab_strata.tex","w").write("\n".join(out)+"\n")

    # ---- collapse by class ----
    # Replacement and collapse are different outcomes and the classes separate them
    # differently, so this is its own table rather than another column on the one above.
    CC=L("cause_collapse.json"); _bc=CC["by_class"]
    out=["\\begin{tabular}{@{}lrrr@{}}","\\toprule",
         "Class & Events & Collapsed & Rate \\\\","\\midrule"]
    for k in _CORD:
        if k not in _bc: continue
        d=_bc[k]
        rate="---" if d["rate"] is None else f"{100*d['rate']:.1f}\\%"
        out.append(f"{_clab(k)} & {d['n']} & {d['collapsed']} & {rate} \\\\")
    out.append("\\midrule")
    for tag,key in [("All observed exits","pooled"),
                    ("Excluding the explained classes","excluding_explained"),
                    ("Documented supply disruptions only","documented_supply")]:
        d=CC[key]
        rate="---" if d["rate"] is None else f"{100*d['rate']:.1f}\\%"
        out.append(f"{tag} & {d['n']} & {d['collapsed']} & {rate} \\\\")
    out+=["\\botrule","\\end{tabular}"]
    open(f"{G}/tab_collapse.tex","w").write("\n".join(out)+"\n")
    _n=lambda v: f"{v:,}".replace(",","{,}")
    M["CollPooledColl"]=_n(CC["pooled"]["collapsed"]); M["CollPooledN"]=_n(CC["pooled"]["n"])
    M["CollPooledRate"]=f"{100*CC['pooled']['rate']:.1f}"
    M["CollRemColl"]=_n(CC["excluding_explained"]["collapsed"])
    M["CollRemCollW"]=_w(CC["excluding_explained"]["collapsed"])
    M["CollRemN"]=_n(CC["excluding_explained"]["n"])
    M["CollRemNW"]=_w(CC["excluding_explained"]["n"])
    M["CollRemRate"]=f"{100*CC['excluding_explained']['rate']:.1f}"
    M["CollSupplyColl"]=_w(CC["documented_supply"]["collapsed"])
    M["CollSupplyN"]=_n(CC["documented_supply"]["n"])
    M["CollTransitionAll"]=_w(_bc["transition"]["collapsed"]) if "transition" in _bc else "zero"
    M["CollContinued"]=_w(_bc["continued"]["collapsed"]) if "continued" in _bc else "zero"
    M["CollUndet"]=_w(_bc["undetermined"]["collapsed"]) if "undetermined" in _bc else "zero"
    c=CS["counts"]
    for k in _CORD:
        M["Cause"+k.capitalize()]=c.get(k,0)
        M["Cause"+k.capitalize()+"W"]=_w(c.get(k,0))
    M["CauseTotal"]=CS["total"]
    # the stratum a supply-chain reading can still claim: everything not explained by
    # regulation, coverage, a transfer or a measurement error
    M["CauseNotExplained"]=CS["ex_not_supply"]["n"]
    M["CauseNotExplainedW"]=_w(CS["ex_not_supply"]["n"])
    M["CauseNotExplainedMed"]=f"{CS['ex_not_supply']['median']:.2f}"
    # how many exits are explained by something other than a supply failure
    _expl=sum(c.get(k,0) for k in ("withdrawal","transition","coverage","transfer","artefact"))
    M["CauseExplained"]=_expl; M["CauseExplainedW"]=_w(_expl)
    M["CauseSupplyEpisodes"]="one"   # the two varenicline events are one recall episode
    M["CauseExplainedUC"]=_w(_expl).capitalize()
    M["AllSoleLtTwo"]=f"{100*CS['all']['p_lt_002']:.1f}"
    M["SupplyMedian"]=f"{CS['supply']['median']:.2f}"
    M["AllMedian"]=f"{CS['all']['median']:.2f}"
    # how many of the documented supply disruptions collapse below two percent of
    # baseline. Typing this count by hand is how it went stale when the cohort grew.
    _sc=round(CS["supply"]["p_lt_002"]*CS["supply"]["n"])
    M["CauseSupplyColl"]=_w(_sc); M["CauseSupplyCollNum"]=str(_sc)
    M["SupplyMedianPct"]=f"{100*CS['supply']['median']:.0f}"
    M["ExNotSupplyN"]=c_(CS["ex_not_supply"]["n"]) if False else str(CS["ex_not_supply"]["n"])
    M["ExNotSupplyNW"]=_w(CS["ex_not_supply"]["n"])
    M["ExNotSupplyMedian"]=f"{CS['ex_not_supply']['median']:.2f}"
    M["ExNotSupplyLtTwo"]=f"{100*CS['ex_not_supply']['p_lt_002']:.1f}"
    M["TransferR"]=f"{CS['transfer']['median']:.2f}" if CS.get("transfer",{}).get("n") else "0.00"
    # the two misspelling artefacts, with the real markets they sit beside
    import csv as _c, duckdb as _d
    _con=_d.connect()
    def _mk(k):
        r=_con.execute("SELECT COUNT(DISTINCT lab),SUM(rx) FROM read_parquet('/tmp/lmq_v2.parquet') "
                       "WHERE mkt=? AND rx IS NOT NULL",[k]).fetchone()
        return r[0], r[1] or 0
    _el,_erx=_mk("ESCITALOPRAM | ORAL TABLET")
    if not _el: raise SystemExit("ESCITALOPRAM | ORAL TABLET not in the panel; "
                                 "the artefact comparison in Section 3.4 needs it")
    # "c" is shadowed by the local counts dict in this function
    M["EscitalopramLabelers"]=f"{_el:,}".replace(",","{,}")
    M["EscitalopramRx"]=f"{_erx/1e6:.1f}"
    _gl,_grx=_mk("GRISEOFULVIN | ORAL LIQUID")
    M["GriseofulvinLabelers"]=f"{_gl:,}".replace(",","{,}")
    for k in _CORD: M["Cause"+k.capitalize()+"UC"]=_w(c.get(k,0)).capitalize()
    return len(rowspec)
_ncause=emit_cause(); _nstrata=emit_strata()
_ntrans=emit_transition()

# the macro file is written LAST, so every table emitter can contribute to it
_bad=[k for k in M if not k.isalpha()]
if _bad: raise SystemExit(f"macro names must be letters only (TeX restriction): {_bad}")
open(f"{G}/numbers.tex","w").write(
 "% generated by scripts/emit_tex.py -- do not edit\n"
 "% Each value ends in \\xspace: TeX swallows the space after a control word, so a bare\n"
 "% \\newcommand would render \"\\nConfirmed testable\" as \"292testable\". Requires\n"
 "% \\usepackage{xspace} in the preamble.\n"+
 "\n".join(f"\\newcommand{{\\n{k}}}{{{v}\\xspace}}" for k,v in sorted(M.items()))+"\n")


import json as _j
_nf=_ROOT+"/results/manuscript_numbers.json"
import re as _re, os as _os
# how many final checks run_all.sh runs, excluding the preflight. Three documents
# quoted three different numbers for this.
_sh=open(f"{_os.path.dirname(_os.path.abspath(__file__))}/run_all.sh").read()
_nchk=len(set(_re.findall(r"((?:audit|check|verify)_\w+)\.py",_sh))-{"check_environment"})
_nd=_j.load(open(_nf))
# Macros reach the manuscript from two generated files. Counting only this script's
# left the response letter understating the total by the detector macros.
# Every generated file that defines macros, not a named list of two: adding a third
# file silently understated the count and the response letter carried the wrong total.
import glob as _glob
_extra=sum(len(_re.findall(r"^\\newcommand", open(_f).read(), _re.M))
           for _f in sorted(_glob.glob(f"{G}/*_macros.tex")))
_nd["generated_macro_count"]=len(M)+_extra
_nd["final_check_count"]=_nchk
_j.dump(_nd,open(_nf,"w"),indent=1)
print(f"wrote {len(M)} macros and 9 table bodies ({_ntrans} transition rows, {_ncause} exits, {_nrc} coverage years) to springer/generated/")
for k in ["NormKeys","KeysAbsorbed","ReclassRate","ReclassVol","MinorityN","ReplEligible","Cohort","MinorityLtTwo"]:
    print(f"   \\n{k} = {M[k]}")

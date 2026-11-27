"""The two appendix tables, generated from the analysis outputs.

Both were hand-typed until now. The evidence table was typed against a thirteen-event
cohort and silently went stale when the corrected detector found nineteen, which is
exactly the failure a generated table cannot have: it is written from
results/event_cause_classification.csv, so it either matches the cohort or the run
fails.
"""
import csv, json, os, sys
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import display_names as D

def esc(x):
    for a,b in (("&",r"\&"),("%",r"\%"),("#",r"\#"),("_",r"\_")):
        x=x.replace(a,b)
    return x

G=f"{R}/springer/generated"
os.makedirs(G,exist_ok=True)

# ---- Table: evidence behind each classification ----
rows=list(csv.DictReader(open(f"{R}/results/event_cause_classification.csv")))
if not rows: sys.exit("event_cause_classification.csv is empty")
out=[r"\begin{tabular}{@{}lp{2.9cm}p{1.7cm}p{3.9cm}p{1.5cm}@{}}",r"\toprule",
     r"Quarter & Market & Firm & Regulatory record & Link \\",r"\midrule"]
for r in rows:
    rec=r["record_short"] or "None found"
    out.append(" & ".join([r["event_quarter"],
                           esc(D.event_market(r["market"])),
                           esc(D.labeler(r["departing_labeler"])),
                           esc(rec),
                           esc(r["evidence_link"] or "---")])+r" \\")
out+= [r"\botrule",r"\end{tabular}"]
open(f"{G}/tab_audit.tex","w").write("\n".join(out)+"\n")
# The same rows without the tabular wrapper. Nineteen rows do not fit in a fixed float,
# which pushed the last row and the page number past the bottom of the text block, so
# the manuscript sets this table as a longtable and supplies its own header.
rows_only=[l for l in out if l.endswith(r"\\") and "&" in l
           and not l.startswith("Quarter &")]
open(f"{G}/tab_audit_rows.tex","w").write("\n".join(rows_only)+"\n")

# ---- Table: how many events each detector specification admits ----
V=json.load(open(f"{R}/results/detector_variants.json"))
LAB=[("rows_sparse","Row-counted windows, observed quarters only"),
     ("range_sparse","Calendar windows, observed quarters only"),
     ("range_dense","Calendar windows on a dense grid"),
     ("range_dense_persist","Calendar windows, dense grid, persistence required")]
d=[r"\begin{tabular}{@{}lrr@{}}",r"\toprule",
   r"Detector specification & Events & Near-sole exits \\",r"\midrule"]
for k,lab in LAB:
    mark=r"\textsuperscript{a}" if k=="range_dense_persist" else ""
    ev=f"{V[k]['events']:,}".replace(",","{,}")
    sl=f"{V[k]['near_sole']:,}".replace(",","{,}")
    d.append(f"{lab}{mark} & {ev} & {sl} "+r"\\")
d+=[r"\botrule",r"\end{tabular}"]
open(f"{G}/tab_detvar.tex","w").write("\n".join(d)+"\n")

# Macros the prose cites, so no count in the text can drift from this table.
m=[]
for k,_ in LAB:
    n=k.title().replace("_","")
    m.append(r"\newcommand{\nDet%s}{%s\xspace}"%(n,f"{V[k]['events']:,}".replace(",","{,}")))
    m.append(r"\newcommand{\nDetSole%s}{%s\xspace}"%(n,V[k]["near_sole"]))
_pw=V["persistence_window"]
for k,nm in (("events","PwEvents"),("full_twelve_quarters","PwFull"),("truncated","PwTrunc"),
             ("near_sole_events","PwNsEvents"),("near_sole_full_twelve","PwNsFull"),
             ("near_sole_truncated","PwNsTrunc")):
    m.append(r"\newcommand{\n%s}{%s\xspace}"%(nm,f"{_pw[k]:,}".replace(",","{,}")))
# the suppression and persistence sensitivities
SS=V["suppression_sensitivity"]; PW=V["persistence_window"]
m.append(r"\newcommand{\nFillFiveEvents}{%s\xspace}"%f"{SS['events'][1]:,}".replace(",","{,}"))
m.append(r"\newcommand{\nFillTenEvents}{%s\xspace}"%f"{SS['events'][2]:,}".replace(",","{,}"))
m.append(r"\newcommand{\nFillTenSole}{%s\xspace}"%SS["near_sole"][2])
m.append(r"\newcommand{\nFillFiveSole}{%s\xspace}"%SS["near_sole"][1])
m.append(r"\newcommand{\nFillObserved}{%s\xspace}"%SS["observed"][2])
m.append(r"\newcommand{\nFillCollapsed}{%s\xspace}"%SS["collapsed"][2])
m.append(r"\newcommand{\nPersistFull}{%s\xspace}"%PW["full_twelve_quarters"])
m.append(r"\newcommand{\nPersistTrunc}{%s\xspace}"%PW["truncated"])
m.append(r"\newcommand{\nPersistSoleFull}{%s\xspace}"%PW["near_sole_full_twelve"])
m.append(r"\newcommand{\nPersistSoleTrunc}{%s\xspace}"%PW["near_sole_truncated"])
m.append(r"\newcommand{\nPersistFullOnly}{%s\xspace}"%PW["events_full_window_only"])
m.append(r"\newcommand{\nGappyPct}{%s\xspace}"%("%.1f"%V["gappy_pct"]))
m.append(r"\newcommand{\nVanishUndetected}{%s\xspace}"%V["vanished_undetected"])
m.append(r"\newcommand{\nDetDipsRemoved}{%s\xspace}"%
         (V["range_dense"]["events"]-V["range_dense_persist"]["events"]))
m.append(r"\newcommand{\nDetDenseGain}{%s\xspace}"%
         (V["range_dense"]["events"]-V["range_sparse"]["events"]))
open(f"{G}/detector_macros.tex","w").write("\n".join(m)+"\n")
print(f"wrote tab_audit.tex ({len(rows)} events), tab_detvar.tex, detector_macros.tex")

# ---- Table: the exclusion ladder, as named populations ----
# Each row is a population the prose cites by name. The previous version described one
# population's median as another's, which every check passed because the macro was
# correct and only the sentence was wrong.
CS=json.load(open(f"{R}/results/cause_strata.json"))
LAD=CS["ladder"]
ORDER=["all","ex_withdrawal","ex_withdrawal_transition","ex_strong_evidence",
       "ex_all_explained","supply_only"]
LABEL={"all":"Every observed near-sole exit",
       "ex_withdrawal":"Excluding the market-wide withdrawal",
       "ex_withdrawal_transition":"Excluding the withdrawal and the three transitions",
       "ex_strong_evidence":"Excluding only market-wide or product-and-firm explanations",
       "ex_all_explained":"Excluding every alternative-explanation class",
       "supply_only":"Documented supply disruptions only"}
l=[r"\begin{tabular}{@{}lrrrr@{}}",r"\toprule",
   r"Population & Events & Median $R$ & Collapsed & Rate \\",r"\midrule"]
for k in ORDER:
    v=LAD[k]
    l.append(f"{LABEL[k]} & {v['n']} & {v['median']:.2f} & "
             f"{v['collapsed']} & {100*v['collapse_rate']:.1f}\\% "+r"\\")
l+= [r"\botrule",r"\end{tabular}"]
open(f"{G}/tab_ladder.tex","w").write("\n".join(l)+"\n")

# Macros so no sentence can attach one population's statistic to another's name.
lm=[]
_W={2:"two",11:"eleven",15:"fifteen",18:"eighteen",19:"nineteen"}
for k in ORDER:
    v=LAD[k]; nm="".join(w.capitalize() for w in k.split("_"))
    lm.append(r"\newcommand{\nLad%sN}{%d\xspace}"%(nm,v["n"]))
    lm.append(r"\newcommand{\nLad%sNW}{%s\xspace}"%(nm,_W.get(v["n"],str(v["n"]))))
    lm.append(r"\newcommand{\nLad%sMed}{%.2f\xspace}"%(nm,v["median"]))
    lm.append(r"\newcommand{\nLad%sColl}{%d\xspace}"%(nm,v["collapsed"]))
    lm.append(r"\newcommand{\nLad%sRate}{%.1f\xspace}"%(nm,100*v["collapse_rate"]))
open(f"{G}/ladder_macros.tex","w").write("\n".join(lm)+"\n")
print(f"wrote tab_ladder.tex and ladder_macros.tex ({len(ORDER)} populations)")

# ---- Table: product-level evidence on the composition tie-break ----
import csv as _csv2
_ndc=list(_csv2.DictReader(open(f"{R}/results/ndc_composition_audit.csv")))
_te=[r for r in _ndc if r["group"]=="trace elements"]
_t=[r"\begin{tabular}{@{}llp{3.1cm}p{3.4cm}@{}}",r"\toprule",
    r"NDC & Route & FDA active substances & Final market key \\",r"\midrule"]
for r in sorted(_te,key=lambda x:x["ndc"]):
    _t.append(" & ".join([r["ndc"], esc(r["route"].title()),
        esc(r["substance_set"].replace("; ",", ").title()),
        esc(r["final_market_key"].replace(" | "," / "))])+r" \\")
_t+= [r"\botrule",r"\end{tabular}"]
open(f"{G}/tab_ndc.tex","w").write("\n".join(_t)+"\n")
_na=json.load(open(f"{R}/results/ndc_composition_audit.json"))
m.append(r"\newcommand{\nNdcCodes}{%s\xspace}"%f"{_na['product_codes']:,}".replace(",","{,}"))
m.append(r"\newcommand{\nNdcCombos}{%s\xspace}"%_na["name_route_combinations"])
m.append(r"\newcommand{\nNdcMulti}{%s\xspace}"%_na["combinations_with_multiple_substance_sets"])
open(f"{G}/detector_macros.tex","w").write("\n".join(m)+"\n")
print(f"wrote tab_ndc.tex ({len(_te)} trace-element product codes)")

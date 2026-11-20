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
m.append(r"\newcommand{\nGappyPct}{%s\xspace}"%("%.1f"%V["gappy_pct"]))
m.append(r"\newcommand{\nVanishUndetected}{%s\xspace}"%V["vanished_undetected"])
m.append(r"\newcommand{\nDetDipsRemoved}{%s\xspace}"%
         (V["range_dense"]["events"]-V["range_dense_persist"]["events"]))
m.append(r"\newcommand{\nDetDenseGain}{%s\xspace}"%
         (V["range_dense"]["events"]-V["range_sparse"]["events"]))
open(f"{G}/detector_macros.tex","w").write("\n".join(m)+"\n")
print(f"wrote tab_audit.tex ({len(rows)} events), tab_detvar.tex, detector_macros.tex")

"""Assert that every headline number in manuscript.tex matches the computed
results, and that the embedded figures agree with the tables.

Runs against the LaTeX SOURCE, not extracted PDF text: line wrapping in
pdftotext broke exact-string matching and let stale numbers survive a check
three times.
"""
import json, os, re, subprocess, sys
ROOT=os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
TEX=open(f"{ROOT}/springer/manuscript.tex").read()
flat=re.sub(r"\s+"," ",TEX)
# treat "12.3\%" and "12.3 percent" as the same token
flat=flat.replace("\\%"," percent")
INF=json.load(open(f"{ROOT}/results/inference_normalized.json"))
RC=json.load(open(f"{ROOT}/results/recovery_censored.json"))
DE=json.load(open(f"{ROOT}/results/deficit_entry_normalized.json"))
fails=[]; checks=0
def must(label, needle):
    global checks; checks+=1
    if needle.lower() not in flat.lower(): fails.append(f"MISSING  {label}: {needle!r}")
def must_not(label, needle):
    global checks; checks+=1
    if needle.lower() in flat.lower(): fails.append(f"STALE    {label}: {needle!r}")

# --- replacement ratios, from inference_normalized.json ---
for b,lab in [("<35%","under 35"),("65-95%","65 to 95"),("sole","at least 95")]:
    d=INF[f"R_{b}"]
    must(f"R median {b}", f"{d['median']:.2f}")
    must(f"R n {b}", str(d['n']))
    must(f"R collapse {b}", f"{d['p_lt_2pct']*100:.1f} percent")
# --- matched comparison ---
m=INF["matched"]
must("matched control obs", f"{m['control_obs']}")
must("unique controls", f"{m['unique_controls']}")
must("risk difference", f"{m['risk_diff']*100:.1f}")
must("matched CI low", f"{m['ci_sets'][0]*100:.1f}")
must("matched CI high", f"{m['ci_sets'][1]*100:.1f}")
# --- recovery ---
must("logrank 50", f"{RC['50%']['logrank_p']:.3f}")
must("logrank 90", f"{RC['90%']['logrank_p']:.3f}")
# --- deficits ---
for k,lab in [("under 35%","0.2"),("35-95%","5.6"),("at least 95%","10.4")]:
    must(f"deficit total {k}", DE[k]["total_median"] and f"{DE[k]['total_median']:.1f}")
must("deficit post sole", f"{DE['at least 95%']['post_median']:.1f}")
must("deficit LOO low", f"{DE['at least 95%']['loo_min']:.1f}")
must("deficit LOO high", f"{DE['at least 95%']['loo_max']:.1f}")
# --- entry ---
for k in ["under 35%","35-95%","at least 95%"]:
    a,b=DE["entry"][k]; must(f"entry {k}", f"{a/b*100:.1f} percent")
# --- structural claims ---
for n in ["3{,}342","2{,}913","429","3{,}168","2{,}581","6.4 percent","19","1.1 percent","28.0 percent"]:
    must("structural", n)
# --- numbers that must NOT survive from the previous framing ---
for n in ["1.45","3{,}344 markets","45.0 percent","0.00005","10.7 quarters","118-market","21 sole"]:
    must_not("prior-version number", n)
# --- figures must agree with the tables ---
for fig,need in [("fig1",["6% of 19 labelers","100% of 1 labeler"]),
                 ("fig2",["n=14","n=76"]),
                 ("fig3",[f"p = {RC['90%']['logrank_p']:.3f}",f"p = {RC['50%']['logrank_p']:.3f}"])]:
    txt=subprocess.run(["pdftotext",f"{ROOT}/springer/{fig}.pdf","-"],capture_output=True,text=True).stdout
    t=re.sub(r"\s+"," ",txt)
    for s in need:
        checks+=1
        if s.lower() not in t.lower(): fails.append(f"FIGURE   {fig}.pdf does not contain {s!r}")
print(f"{checks} checks run")
if fails:
    print(f"\n{len(fails)} FAILED:")
    for f in fails: print("  "+f)
    sys.exit(1)
print("ALL CHECKS PASS: manuscript, results files and figures agree.")

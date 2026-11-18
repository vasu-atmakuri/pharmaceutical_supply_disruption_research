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
for n in ["3{,}342","2{,}911","383","3{,}294","16.1 percent","8.9 percent","2.1 percent",
          "99.7 percent","1{,}727","293","83.4 percent","14.71","10.53","27.0 percent",
          "34.3 percent","26.3 to 57.9","85.6 percent","1.25"]:
    must("structural", n)
# --- numbers that must NOT survive from the previous framing ---
for n in ["1.45","0.00005","118-market","21 sole","2{,}913","2{,}870","1.73","1.77","35.7","0.053",
          "fourteen sole-labeler exits","four documented supply","96.5 percent","424 of",
          "Six of twenty apparent","is an upper bound on manufacturing","Twenty less six","20.5 percent","32.2 percent","860","should be treated as an upper bound"]:
    must_not("prior-version number", n)
# --- figures must agree with the tables ---
for fig,need in [("fig1",["16% of 19 labelers","100% of 1 labeler"]),
                 ("fig2",["n=13","n=76","n=78"]),
                 ("fig3",[f"p = {RC['90%']['logrank_p']:.3f}",f"p = {RC['50%']['logrank_p']:.3f}"])]:
    txt=subprocess.run(["pdftotext",f"{ROOT}/springer/{fig}.pdf","-"],capture_output=True,text=True).stdout
    t=re.sub(r"\s+"," ",txt)
    for s in need:
        checks+=1
        if s.lower() not in t.lower(): fails.append(f"FIGURE   {fig}.pdf does not contain {s!r}")

# --- the abstract must carry the SAME values as the results files, not merely
# --- contain them somewhere. A silent no-match patch left 38.5/15.4/61.5 in the
# --- abstract for two rounds while the results said 38.2/15.1/68.0.
ab=flat[flat.lower().index("\\abstract"):flat.lower().index("\\keywords")] if "\\keywords" in flat else flat[:4000]
m=INF["matched"]
for label,needle in [("abstract risk difference", f"{m['risk_diff']*100:.1f} points"),
                     ("abstract control rate",    f"{m['control_rate']*100:.2f} percent"),
                     ("abstract CI low",          f"{m['ci_sets'][0]*100:.1f}"),
                     ("abstract CI high",         f"{m['ci_sets'][1]*100:.1f}")]:
    checks+=1
    if needle.lower() not in ab.lower(): fails.append(f"ABSTRACT {label}: expected {needle!r}")
for stale in ["38.5 points","15.4 to 61.5","0.0 percent among"]:
    checks+=1
    if stale.lower() in ab.lower(): fails.append(f"ABSTRACT stale value {stale!r}")

print(f"{checks} checks run")
if fails:
    print(f"\n{len(fails)} FAILED:")
    for f in fails: print("  "+f)
    sys.exit(1)
print("ALL CHECKS PASS: manuscript, results files and figures agree.")

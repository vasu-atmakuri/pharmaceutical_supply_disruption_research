"""Structural verification of the manuscript.

Numeric agreement is no longer checked here: every reported quantity is a macro
emitted from the results files by emit_tex.py, so a stale number is not
representable. What remains checkable is structure: that the abstract carries no
hand-typed figure, that every cross-reference and citation resolves, that each
figure and table is referenced in the text, and that the compiled PDF is current.
"""
import os, re, subprocess, sys, json, time
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
R=_ROOT+""
S=f"{R}/springer"; TEX=open(f"{S}/manuscript.tex").read()
fails=[]; n=0
def ck(l,c,d=""):
    global n; n+=1
    if not c: fails.append(f"{l}: {d}")

# 1. the abstract must contain no literal statistic
ab=TEX[TEX.index("\\abstract{"):]; ab=ab[:ab.index("\\keywords")]
body=re.sub(r"\\n[A-Za-z]+","",ab)
lits=[x for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])",body)
      if x not in ("1","2","2016","2026","4","5","02","0","35","65","90","95",
                   "0.02")]  # band and threshold definitions, not results
ck("abstract carries no hand-typed statistic", not lits, f"literals: {lits}")

ck("no double-escaped macros", not re.search(r"\\\\\\\\n[A-Z]",TEX),
   f"found: {re.findall(chr(92)*4+'n[A-Za-z]+',TEX)[:5]}")

# 2. every \ref resolves to a \label, every \cite to a bib entry
labels=set(re.findall(r"\\label\{([^}]+)\}",TEX))
refs=set(re.findall(r"\\ref\{([^}]+)\}",TEX))
ck("all refs resolve", refs<=labels, f"dangling: {sorted(refs-labels)}")
bib=open(f"{S}/refs.bib").read()
keys=set(re.findall(r"@\w+\{([^,]+),",bib))
cited=set(k.strip() for g in re.findall(r"\\cite[tp]?\{([^}]+)\}",TEX) for k in g.split(","))
ck("all citations resolve", cited<=keys, f"missing: {sorted(cited-keys)}")
ck("no uncited references", not (keys-cited), f"uncited: {sorted(keys-cited)}")

# 3. every float is referenced in the text, and no \ref is broken in the PDF
for lab in sorted(l for l in labels if l.startswith(("fig:","tab:"))):
    ck(f"{lab} referenced in text", f"\\ref{{{lab}}}" in TEX)
pdf=subprocess.run(["pdftotext",f"{S}/manuscript.pdf","-"],capture_output=True,text=True).stdout
ck("no broken references in the PDF", "??" not in pdf and "efsubsec" not in pdf and "efsec" not in pdf)
ck("no undefined macro text in the PDF", not re.search(r"\\n[A-Z]",pdf))


# 6. the RENDERED PDF must not join a number to the following word. TeX swallows the
# space after a control word, so a macro defined without \xspace silently produces
# "292testable" throughout. Reading extracted text for presence does not catch this.
WORDS=("percent","testable","matched","points","markets","market","events","event","exits",
       "exit","buckets","labeler","labelers","groups","keys","minority","control","controls",
       "sole","raw","of","in","and","observations","prescriptions","quarters","ingredient")
joined=re.findall(r"\b\d[\d.,]*(?:"+"|".join(WORDS)+r")\b",pdf)
ck("no number joined to a word in the rendered PDF", not joined,
   f"{len(joined)} found, e.g. {sorted(set(joined))[:6]}")
_nums=[l for l in open(f"{S}/generated/numbers.tex").read().splitlines()
       if l.startswith("\\newcommand")]
_noxs=[l for l in _nums if not l.rstrip().endswith("\\xspace}")]
ck("every macro definition carries xspace", not _noxs,
   f"{len(_noxs)} of {len(_nums)} lack it, e.g. {_noxs[:3]}")
ck("xspace package loaded", "\\usepackage{xspace}" in TEX)

# 4. the PDF must be newer than the sources it was built from
pt=os.path.getmtime(f"{S}/manuscript.pdf")
for f in ["manuscript.tex","generated/numbers.tex","generated/tab_flow.tex","generated/tab_concentration.tex",
          "generated/tab_rules.tex","generated/tab_replacement.tex","fig1.pdf","fig2.pdf","fig3.pdf"]:
    ck(f"PDF newer than {f}", pt>=os.path.getmtime(f"{S}/{f}")-1,
       f"{f} is {(os.path.getmtime(f'{S}/{f}')-pt)/60:.1f} min newer than the PDF")

# 5. the figures must be newer than the panel they are drawn from
for f in ["fig1.pdf","fig2.pdf","fig3.pdf"]:
    ck(f"{f} newer than the results files",
       os.path.getmtime(f"{S}/{f}")>=os.path.getmtime(f"{R}/results/inference_normalized.json")-1,
       f"{f} predates inference_normalized.json")


# ---- no page's content runs past the bottom of the text block ----
# A nineteen-row table in a fixed float cannot break across pages, so it overran the
# footer: the page number sat on top of the last row and the row's descenders were
# clipped. Every other check passed, because nothing here had ever looked at where the
# ink lands. This reads each page's lowest text and flags a page that reaches
# meaningfully below the line the footer sits on, which is the same on every page.
_bb=subprocess.run(["pdftotext","-bbox-layout",f"{S}/manuscript.pdf","-"],
                   capture_output=True,text=True).stdout
if _bb:
    import collections as _col
    _pages=re.findall(r'<page width="[\d.]+" height="([\d.]+)">(.*?)</page>', _bb, re.S)
    _bot=[]
    for _i,(_h,_body) in enumerate(_pages,1):
        _ys=[float(_m) for _m in re.findall(r'yMax="([\d.]+)"', _body)]
        _bot.append((_i, max(_ys) if _ys else 0.0))
    if _bot:
        _modal=_col.Counter(round(_b) for _,_b in _bot).most_common(1)[0][0]
        _over=[(i,b) for i,b in _bot if b > _modal+6]
        ck("no page overflows the text block", not _over,
           "; ".join(f"page {i} reaches {b-_modal:.0f}pt past the footer line"
                     for i,b in _over))
else:
    print("   (page-overflow check skipped: pdftotext -bbox-layout produced nothing)")

print(f"{n} structural checks run")
if fails:
    print(f"\n{len(fails)} FAILED:")
    for f in fails: print("   "+f)
    sys.exit(1)
print("ALL STRUCTURAL CHECKS PASS")

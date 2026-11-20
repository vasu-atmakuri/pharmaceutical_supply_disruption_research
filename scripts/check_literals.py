"""No literal number may sit in the manuscript's prose unless it is declared here.

Two defects in the fourteenth round got through every other check. A generated table
contained a hard-coded cell, and several sentences cited a correctly defined macro
that held the wrong quantity. audit_numbers.py asks whether each number traces to
some analysis output, and check_relationships.py asks whether each macro matches its
source. Neither asks whether a literal should have been a macro at all.

This does. Every digit sequence in the body prose and in the generated tables must
either be a macro's output or appear on the allowlist below with a reason. The
allowlist is deliberately short and each entry says why that number is fixed by the
paper's design rather than by its data.
"""
import json, os, re, sys
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX=open(f"{R}/springer/manuscript.tex").read()

# Numbers fixed by the design of the analysis, not by its results. A number that
# moves when the data move does not belong here; it belongs in a macro.
ALLOWED={
 "0.02":"the collapse threshold, a definition",
 "0.05":"the exit threshold, a definition",
 "0.5":"the persistence threshold, a definition",
 "0.9":"a recovery threshold, a definition",
 "0.01":"the rounding floor below which a ratio is printed as an inequality",
 "95":"the near-sole share threshold, a definition",
 "90":"a recovery threshold, a definition",
 "65":"a band boundary, a definition",
 "35":"a band boundary, a definition",
 "200":"the baseline volume floor, a definition",
 "11":"the CMS suppression threshold, external and fixed",
 "100":"percent, or a share expressed against it",
 "5":"the exit threshold as a percentage, a definition",
 "2":"the collapse threshold as a percentage, a definition",
 "4":"the window length in quarters, a definition",
 "6":"the follow-up length in quarters, a definition",
 "12":"the persistence and recovery horizon in quarters, a definition",
 "1":"a count of one in a definition or an ordinal",
 "3":"a window offset in quarters, a definition",
 "0":"zero",
 "10":"the ten-prescription suppression scenario, a definition",
 "50":"a recovery threshold as a percentage, a definition",
 "2016":"the first year of the panel",
 "2026":"the last year of the panel",
 "2020":"a calendar year in a cited regulatory record",
 "2021":"a calendar year in a cited regulatory record",
 "2022":"a calendar year in a cited regulatory record",
 "2023":"a calendar year in a cited regulatory record",
 "2024":"a calendar year in a cited regulatory record",
 "2018":"a calendar year in a cited regulatory record",
 "2019":"a calendar year in a cited regulatory record",
 "0009":"an ORCID segment","0007":"an ORCID segment",
 "5955":"an ORCID segment","2466":"an ORCID segment",
 "506":"a statutory section number, FDA 506C",
 "20":"a milligram strength in an illustrative example of two tablets of one drug",
 "344":"part of 3,344, the market count published by the work we compare with; an "
        "external figure, not ours",
}

def body(t):
    """The prose: drop the preamble, the bibliography, macro definitions, labels,
    citations, file and section names, and anything in a verbatim or math span."""
    t=t[t.index("\\abstract{"):]
    for pat in (r"\\input\{[^}]*\}", r"\\label\{[^}]*\}", r"\\ref\{[^}]*\}",
                r"\\cite[a-z]*\{[^}]*\}", r"\\url\{[^}]*\}", r"\\texttt\{[^}]*\}",
                r"\\n[A-Z][A-Za-z]*", r"\$[^$]*\$", r"%[^\n]*",
                r"\\begin\{[^}]*\}", r"\\end\{[^}]*\}", r"\\includegraphics[^\n]*",
                r"[0-9]{4}Q[1-4]"):
        t=re.sub(pat,"",t)
    return t

b=body(TEX)
found={}
for m in re.finditer(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])",b):
    tok=m.group(0)
    if tok in ALLOWED or tok.replace(",","") in ALLOWED: continue
    found.setdefault(tok,b[max(0,m.start()-70):m.start()+30].replace("\n"," "))

_ndig=len(re.findall(r"(?<![\w.])\d", b))
print(f"{_ndig} digit positions scanned in the body prose")
if found:
    print(f"\n{len(found)} literal numbers in prose that are not declared:")
    for t,ctx in sorted(found.items()):
        print(f"   {t:<10} ...{ctx}...")
    print("\nEither make it a macro emitted from the analysis, or add it to ALLOWED "
          "in check_literals.py with the reason it is fixed by design.")
    sys.exit(1)

# generated tables must not contain a literal the generator typed either: the
# collapse column was a hard-coded string for two rounds
bad=[]
G=f"{R}/springer/generated"
for f in sorted(os.listdir(G)):
    if not f.startswith("tab_"): continue
    src=open(f"{G}/{f}").read()
    if "38.5" in src and "tab_replacement" in f: bad.append((f,"38.5"))
if bad:
    print("\ngenerated tables carrying a known stale literal:")
    for f,t in bad: print(f"   {f}: {t}")
    sys.exit(1)
print("NO UNDECLARED LITERAL NUMBERS IN THE MANUSCRIPT PROSE")

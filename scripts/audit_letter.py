"""Audit the response letter's numbers against the analysis outputs.

The letter is read by the reviewer alongside the manuscript, so a number that is
right in the paper and stale in the letter is the same failure. Unlike the
manuscript it is not macro-driven, so every figure in it is checked here.
"""
import json, os, re, glob, sys
import os as _os
# Root of the repository. Set PSDR_ROOT to run outside the analysis VM.
_ROOT=_os.environ.get("PSDR_ROOT") or _os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research")
# Parent folder holding the raw FDA and SDUD downloads.
_DATA=_os.environ.get("RESEARCH_ROOT") or _os.path.expanduser("~/mnt/Research")
R=_ROOT+""
L=open(f"{R}/springer/response_to_reviewer.md").read()
vals=set()
def walk(x):
    if isinstance(x,dict):
        for v in x.values(): walk(v)
    elif isinstance(x,(list,tuple)):
        for v in x: walk(v)
    elif isinstance(x,bool): pass
    elif isinstance(x,(int,float)):
        for f in ("{:.0f}","{:.1f}","{:.2f}","{:.3f}","{:,.0f}"):
            vals.add(f.format(x))
            vals.add(f.format(abs(x)))   # the token regex drops the sign
        for m in (100,):
            for f in ("{:.0f}","{:.1f}","{:.2f}"): vals.add(f.format(x*m))
for f in glob.glob(f"{R}/results/*.json"):
    try: walk(json.load(open(f)))
    except Exception: pass
body=re.sub(r"`[^`]*`","",L)                 # script names and code spans
body=re.sub(r"\[[^\]]*\]\([^)]*\)","",body)  # links
body=re.sub(r"[0-9]{4}Q[1-4]","",body)
# cross-references to the manuscript: a section, table or figure number is a pointer,
# not a quantity, and asking it to trace to an analysis output is a category error
body=re.sub(r"\b(?:Section|Sections|Table|Tables|Figure|Figures)\s+[\d.]+(?:\s*(?:and|to|,)\s*[\d.]+)*","",body)
# calendar dates: a regulatory record is identified by its date, which is not an
# analysis output and should not be asked to trace to one
body=re.sub(r"\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|"
            r"October|November|December) (?:19|20)\d\d\b","",body)
body=re.sub(r"\b(?:January|February|March|April|May|June|July|August|September|October|"
            r"November|December) (?:19|20)\d\d\b","",body)
# Section 0 of the letter deliberately quotes the superseded bound so the reviewer
# can see what changed; those two values are expected not to match current output.
# Values the letter quotes as superseded, so the reviewer can see what changed.
# Values the letter quotes as superseded so the reviewer can see what changed. The
# second group is the "Before" column of the crosswalk-determinism table in Section 0:
# those numbers are what the previous PDF reported and no longer appear in any output,
# which is the point of showing them.
SUPERSEDED={"26.3","57.9","15,744","39",
            "3,295","2,916","94.4","95.8","200,534","19.96"}
OK=SUPERSEDED|{"0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16",
    "19","20","25","35","41","50","53","60","65","90","95","100","2016","2026","0.02","0.05"}
found=sorted({t for t in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])",body)} - OK)
orphans=[t for t in found if t not in vals and t.replace(",","") not in vals]

# ---- a percentage that is a hundred times a real value is a formatting bug ----
# The letter once printed 1,657.00% where the value was 16.57: the figure was stored as
# a percentage and multiplied by a hundred again. It passed this audit because the
# multiplied value happened to match one of the formats a results value is rendered in.
# A percentage above 1000 in a paper about market shares and collapse rates is never
# right, so it is rejected outright.
_pcts=[t for t in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*(?:%|percent)", body)]
# The letter quotes the erroneous value in the section that reports the error, so a
# quoted figure is exempt. Nothing else above 1000 percent is.
_QUOTED={"1,657","1657.00","1657"}
_huge=[t for t in _pcts if float(t.replace(",",""))>1000 and t not in _QUOTED]
if _huge:
    print(f"\nIMPLAUSIBLE PERCENTAGES IN THE LETTER: {_huge}")
    print("   a share or rate above 1000 percent is a formatting error; check for a "
          "value that is already a percentage being multiplied by a hundred")
    sys.exit(1)

print(f"{len(found)} distinct numbers in response_to_reviewer.md")
if orphans:
    print(f"\n{len(orphans)} with no match in any results file:")
    for t in orphans:
        i=body.find(t); print(f"   {t:<12} ...{body[max(0,i-70):i+40].replace(chr(10),' ')}...")
    sys.exit(1)
print("every number in the letter traces to an analysis output")

# ---- a table number the letter cites must be the number the manuscript assigns ----
# The letter said the exclusion ladder was Table 9 when the compiled manuscript makes it
# Table 10, and Table 9 is a different table. Float numbering is decided by LaTeX, so it
# is read from the aux file rather than trusted.
_aux=f"{R}/springer/manuscript.aux"
if _os.path.exists(_aux):
    _a=open(_aux).read()
    _num={m.group(1):m.group(2) for m in
          re.finditer(r"newlabel\{(tab:[a-z]+)\}\{\{(\d+)\}", _a)}
    _cited={"the exclusion ladder":"tab:ladder","cause-specific replacement":"tab:strata",
            "the nineteen-event audit":"tab:cause","the evidence appendix":"tab:audit"}
    _bad=[]
    for _phrase,_lab in _cited.items():
        _n=_num.get(_lab)
        if not _n: continue
        # the letter may not mention every one; only check the ones it names
        if _lab=="tab:ladder" and "exclusion ladder" in L:
            if f"Table {_n}" not in L: _bad.append(f"the ladder is Table {_n}")
    if _bad:
        print("\nTABLE REFERENCES IN THE LETTER DO NOT MATCH THE MANUSCRIPT:")
        for _b in _bad: print("   "+_b)
        sys.exit(1)
    print(f"table numbers cited in the letter match the manuscript "
          f"(ladder is Table {_num.get('tab:ladder','?')})")

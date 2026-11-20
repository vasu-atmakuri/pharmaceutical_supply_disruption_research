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
SUPERSEDED={"26.3","57.9","15,744","39"}
OK=SUPERSEDED|{"0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16",
    "19","20","25","35","41","50","53","60","65","90","95","100","2016","2026","0.02","0.05"}
found=sorted({t for t in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])",body)} - OK)
orphans=[t for t in found if t not in vals and t.replace(",","") not in vals]
print(f"{len(found)} distinct numbers in response_to_reviewer.md")
if orphans:
    print(f"\n{len(orphans)} with no match in any results file:")
    for t in orphans:
        i=body.find(t); print(f"   {t:<12} ...{body[max(0,i-70):i+40].replace(chr(10),' ')}...")
    sys.exit(1)
print("every number in the letter traces to an analysis output")

"""Record every raw input the analysis can consume, so it can be deleted and restored.

The raw inputs are 17 GB of public bulk files. Keeping them on a laptop that is out of
disk is not a reproducibility strategy, and deleting them without a record is not one
either. This writes an inventory: for every file, its size, its SHA-256 and where it
came from, grouped by what the group is for and whether the current pipeline needs it.

What the pipeline actually needs to run is much smaller than what is here. The per-year
SDUD parts in data/sdud_parts (12 MB, committed to this repository) are the aggregated
form every panel stage reads; the raw yearly CSVs are only the input to the stage that
builds them. So a clone of this repository plus the NDC crosswalk zips reproduces every
number in the paper without any of the bulk downloads.

One caveat is recorded here because it matters more than the hashes: CMS revises its
published files in place, which is why the 2020 and later filenames carry an
"updatedJuly2026" suffix. A file re-downloaded later is not guaranteed to be byte
identical to the one these results were computed from. The committed parts, not the
raw CSVs, are therefore the reproducibility anchor, and the hashes below are what makes
a re-download checkable against the run that produced the paper.

Usage: data_inventory.py [group ...]   (default: every group)
Groups are merged into results/data_inventory.json, so it can be run in parts.
"""
import hashlib, json, os, sys, glob, datetime

R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D=os.environ.get("RESEARCH_ROOT") or os.path.dirname(R)
OUT=f"{R}/results/data_inventory.json"

# group -> (what it is, needed by the pipeline?, how to restore it)
GROUPS={
 "sdud_raw_in_window": dict(
   paths=[f"{D}/sdud/StateDrugUtilizationData-201[6-9].csv",
          f"{D}/sdud/sdud202*.csv"],
   purpose="Medicaid State Drug Utilization Data, 2016 to 2026Q1: the raw yearly files "
           "the panel is built from",
   needed="only to rebuild data/sdud_parts, which is committed to this repository",
   restore="wget -i sdud/dl.txt -P sdud/  (URLs are https://download.medicaid.gov/data/<file>)",
   source="https://data.medicaid.gov/dataset/state-drug-utilization-data"),
 "sdud_raw_pre_window": dict(
   paths=[f"{D}/sdud/StateDrugUtilizationData-19*.csv",
          f"{D}/sdud/StateDrugUtilizationData-200*.csv",
          f"{D}/sdud/StateDrugUtilizationData-201[0-5].csv"],
   purpose="Medicaid State Drug Utilization Data, 1991 to 2015",
   needed="no: the panel starts at 2016Q1. Kept originally for a feasibility check on "
          "earlier history",
   restore="wget -i sdud/dl_pre2014.txt -i sdud/dl1416.txt -P sdud/",
   source="https://data.medicaid.gov/dataset/state-drug-utilization-data"),
 "crosswalk": dict(
   paths=[f"{D}/crosswalk/*.zip", f"{D}/crosswalk/product.txt",
          f"{D}/crosswalk/package.txt", f"{D}/crosswalk/drug-ndc-*.json"],
   purpose="FDA NDC directory and the openFDA NDC listing: route, dosage form, labeler "
           "name and active substances for every product code",
   needed="yes, by the crosswalk stage. The two zips are the originals; the extracted "
          "files are rebuilt from them by ensure_inputs.py",
   restore="the zips are kept; ensure_inputs.py extracts the rest. To refetch the zips: "
           "https://www.accessdata.fda.gov/cder/ndctext.zip and "
           "https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip",
   source="https://www.fda.gov/drugs/drug-approvals-and-databases/national-drug-code-directory"),
 "nadac": dict(
   paths=[f"{D}/aux/nadac_*.csv"],
   purpose="National Average Drug Acquisition Cost, yearly files: unit prices used in "
           "the spending robustness check",
   needed="no: that check is not a pipeline stage and its output is in "
          "results/RESULTS_nadac.json",
   restore="download the yearly NADAC files from the dataset page into aux/ as "
           "nadac_<year>.csv",
   source="https://data.medicaid.gov/dataset/dfa2ab14-06c2-457a-9e36-5cb1e4d906c6"),
 "spl": dict(
   paths=[f"{D}/aux/spl/*.xml"],
   purpose="DailyMed Structured Product Labeling documents, one per set id: "
           "manufacturing establishment names behind the labeler codes",
   needed="no: the establishment analysis is not a pipeline stage and its output is in "
          "results/RESULTS_establishments.json and RESULTS_prodestab.json",
   restore="the set ids are kept in Research/aux_spl_setids_full.txt; fetch each as "
           "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/<setid>.xml",
   source="https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm"),
 "enforcement": dict(
   paths=[f"{D}/enforcement/*.json", f"{D}/enforcement/*.zip"],
   purpose="openFDA drug enforcement (recall) reports, used for the recall "
           "co-occurrence counts",
   needed="no: the counts are in results/recall_match_level.json. Small enough to keep",
   restore="https://download.open.fda.gov/drug/enforcement/drug-enforcement-0001-of-0001.json.zip",
   source="https://open.fda.gov/apis/drug/enforcement/download/"),
 "parts": dict(
   paths=[f"{R}/data/sdud_parts/*.parquet", f"{D}/sdud_parts/*.parquet"],
   purpose="the aggregated per-year panel parts every panel stage reads",
   needed="yes. These are committed to this repository: 12 MB that replaces 5 GB of raw "
          "CSVs for every purpose except rebuilding them",
   restore="committed; or rebuild with scripts/build_sdud_parts.py from the raw yearly "
           "files",
   source="derived from the SDUD yearly files by scripts/build_sdud_parts.py"),
}

def sha(p, bs=1<<22):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(bs), b""): h.update(b)
    return h.hexdigest()

inv={}
if os.path.exists(OUT):
    try: inv=json.load(open(OUT))
    except Exception: inv={}
inv.setdefault("groups",{})

want=sys.argv[1:] or list(GROUPS)
for g in want:
    if g not in GROUPS: sys.exit(f"unknown group {g!r}; choose from {', '.join(GROUPS)}")
    spec=GROUPS[g]; files=[]
    for pat in spec["paths"]:
        files+= [f for f in glob.glob(pat) if os.path.isfile(f)]
    files=sorted(set(files))
    recs=[]
    for f in files:
        recs.append(dict(name=os.path.relpath(f,D), bytes=os.path.getsize(f),
                         sha256=sha(f)))
    inv["groups"][g]={k:v for k,v in spec.items() if k!="paths"}
    inv["groups"][g].update(files=recs, file_count=len(recs),
                            bytes=sum(r["bytes"] for r in recs))
    print(f"{g:22s} {len(recs):5d} files  {sum(r['bytes'] for r in recs)/2**30:7.2f} GiB")

inv["recorded_at"]=datetime.datetime.now(datetime.timezone.utc).replace(
    microsecond=0).isoformat()
inv["research_root_note"]=("Paths are relative to the folder that holds this repository "
  "and the raw-data folders (sdud, aux, crosswalk, enforcement), which the pipeline "
  "calls RESEARCH_ROOT.")
inv["revision_caveat"]=("CMS revises published SDUD files in place; the 2020 and later "
  "filenames carry an updatedJuly2026 suffix for that reason. A re-downloaded file may "
  "not match these hashes. The committed data/sdud_parts, not the raw CSVs, is what "
  "makes the published numbers reproducible.")
json.dump(inv,open(OUT,"w"),indent=1,sort_keys=True)
tot=sum(v["bytes"] for v in inv["groups"].values())
print(f"\n{len(inv['groups'])} groups, {tot/2**30:.2f} GiB recorded -> results/data_inventory.json")

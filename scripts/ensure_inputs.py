"""Put the pipeline's inputs in place, extracting from the kept archives if needed.

Three of the crosswalk inputs are extracted copies of files inside two zips that are
kept beside them: product.txt and package.txt come from ndctext.zip, and the openFDA
NDC listing comes from openfda_ndc.json.zip. Together the extracted copies are 300 MB
and the zips are 38 MB, so the extracted copies are not worth storing. This extracts
them when they are missing and does nothing when they are present, which makes the
disk cleanup invisible to every stage that reads them.

It also points at the panel parts. The parts committed to this repository under
data/sdud_parts are the ones the published numbers were computed from; a copy in
RESEARCH_ROOT/sdud_parts, if present, is used in preference only because that is where
build_sdud_parts.py writes a fresh build. Neither is rebuilt here.
"""
import os, sys, zipfile, glob

R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D=os.environ.get("RESEARCH_ROOT") or os.path.dirname(R)
C=f"{D}/crosswalk"

# extracted file -> archive it lives in
FROM_ZIP={
 "product.txt": "ndctext.zip",
 "package.txt": "ndctext.zip",
 "drug-ndc-0001-of-0001.json": "openfda_ndc.json.zip",
}

missing_zip=[]
for name, zname in FROM_ZIP.items():
    target=f"{C}/{name}"
    if os.path.exists(target):
        continue
    zpath=f"{C}/{zname}"
    if not os.path.exists(zpath):
        missing_zip.append((name, zname)); continue
    with zipfile.ZipFile(zpath) as z:
        inner=[n for n in z.namelist() if os.path.basename(n)==name]
        if not inner:
            missing_zip.append((name, zname)); continue
        with z.open(inner[0]) as src, open(target,"wb") as dst:
            while True:
                b=src.read(1<<22)
                if not b: break
                dst.write(b)
    print(f"   extracted {name} from {zname} ({os.path.getsize(target)/2**20:.0f} MiB)")

if missing_zip:
    for name, zname in missing_zip:
        print(f"   MISSING {name}, and {zname} is not in {C}")
    print("   see DATA.md for where to download the NDC archives")
    sys.exit(1)

# where the parts are, in preference order
cands=[f"{D}/sdud_parts", f"{R}/data/sdud_parts"]
found=next((p for p in cands if glob.glob(f"{p}/*.parquet")), None)
if not found:
    print(f"   no panel parts in {' or '.join(cands)}")
    print("   see DATA.md: the committed parts are data/sdud_parts in this repository")
    sys.exit(1)
n=len(glob.glob(f"{found}/*.parquet"))
print(f"   inputs ready: crosswalk extracted, {n} panel parts in "
      f"{os.path.relpath(found, D)}")

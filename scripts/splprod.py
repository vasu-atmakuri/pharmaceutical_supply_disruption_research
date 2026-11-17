import glob, os, json
import xml.etree.ElementTree as ET
NS={'v3':'urn:hl7-org:v3'}
files=sorted(glob.glob(os.path.expanduser("~/mnt/Research/aux/spl/*.xml")))
rows=[]; noprod=0
for f in files:
    labcode=os.path.basename(f).split("_")[0]
    try: root=ET.parse(f).getroot()
    except Exception: continue
    au=root.find('.//v3:author/v3:assignedEntity/v3:representedOrganization',NS)
    if au is None: continue
    for ent in au.iter('{urn:hl7-org:v3}assignedEntity'):
        org=ent.find('v3:assignedOrganization',NS)
        if org is None: continue
        oid=org.find('v3:id',NS); onm=org.find('v3:name',NS)
        if oid is None or oid.get('extension') is None: continue
        est=oid.get('extension'); enm=(onm.text or '').strip() if onm is not None else ''
        for perf in ent.findall('v3:performance',NS):
            c=perf.find('v3:actDefinition/v3:code',NS)
            op=c.get('displayName').upper() if (c is not None and c.get('displayName')) else None
            if not op: continue
            prods=perf.findall('.//v3:manufacturedMaterialKind/v3:code',NS)
            if not prods: noprod+=1; continue
            for p in prods:
                pn=p.get('code')
                if not pn or '-' not in pn: continue
                a,b=pn.split('-')[0],pn.split('-')[1]
                rows.append((labcode,est,enm,op,a.zfill(5),b.zfill(4)))
print(f"product-level establishment rows: {len(rows):,}   performances with no product code: {noprod:,}",flush=True)
import duckdb
con=duckdb.connect(); con.execute("SET memory_limit='1200MB'")
con.execute("CREATE TABLE pe(labcode VARCHAR,est VARCHAR,estname VARCHAR,op VARCHAR,lab VARCHAR,pcode VARCHAR)")
con.executemany("INSERT INTO pe VALUES (?,?,?,?,?,?)",rows)
con.execute("COPY (SELECT * FROM pe) TO '/tmp/prodestab.parquet' (FORMAT PARQUET)")
r=con.execute("""SELECT COUNT(DISTINCT lab||pcode), COUNT(DISTINCT est) FROM pe
  WHERE op LIKE '%MANUFACTURE%' AND op<>'API MANUFACTURE'""").fetchone()
print(f"distinct products with a manufacture site: {r[0]:,}   distinct sites: {r[1]:,}",flush=True)
print("\n=== coverage against the dispensing panel ===",flush=True)
con.execute("""CREATE OR REPLACE TABLE pm AS SELECT DISTINCT lab,pcode,est FROM pe
  WHERE op LIKE '%MANUFACTURE%' AND op<>'API MANUFACTURE'""")
r=con.execute("""SELECT COUNT(*) tot, SUM(CASE WHEN m.est IS NOT NULL THEN 1 ELSE 0 END) hit FROM
 (SELECT DISTINCT lpad(lab,5,'0') lab, lpad(pcode,4,'0') pcode FROM read_parquet('/tmp/pq_app.parquet') LIMIT 0) x
 LEFT JOIN pm m ON m.lab=x.lab AND m.pcode=x.pcode""").fetchone()
# proper coverage: products actually dispensing in cohort markets
print("built /tmp/prodestab.parquet",flush=True)

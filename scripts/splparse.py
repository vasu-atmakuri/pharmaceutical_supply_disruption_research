import glob, os, re, json, collections
import xml.etree.ElementTree as ET
NS={'v3':'urn:hl7-org:v3'}
files=sorted(glob.glob(os.path.expanduser("~/mnt/Research/aux/spl/*.xml")))
print(f"files: {len(files)}",flush=True)
rows=[]; bad=0
for f in files:
    lab_code=os.path.basename(f).split("_")[0]
    try: root=ET.parse(f).getroot()
    except Exception: bad+=1; continue
    au=root.find('.//v3:author/v3:assignedEntity/v3:representedOrganization',NS)
    if au is None: continue
    lid=au.find('v3:id',NS); lname=au.find('v3:name',NS)
    ldu=lid.get('extension') if lid is not None else None
    lnm=(lname.text or '').strip() if lname is not None else None
    # establishments: assignedOrganization nodes that carry an id and a performance sibling
    for ent in au.iter('{urn:hl7-org:v3}assignedEntity'):
        org=ent.find('v3:assignedOrganization',NS)
        if org is None: continue
        oid=org.find('v3:id',NS); onm=org.find('v3:name',NS)
        if oid is None or oid.get('extension') is None: continue
        ops=set()
        for perf in ent.findall('v3:performance',NS):
            c=perf.find('v3:actDefinition/v3:code',NS)
            if c is not None and c.get('displayName'): ops.add(c.get('displayName').upper())
        if not ops: continue
        rows.append((lab_code, ldu, lnm, oid.get('extension'),
                     (onm.text or '').strip() if onm is not None else '', "|".join(sorted(ops))))
print(f"parse failures: {bad}   establishment rows: {len(rows):,}",flush=True)
import duckdb
con=duckdb.connect(); con.execute("SET memory_limit='1200MB'")
con.execute("CREATE TABLE e(labcode VARCHAR,lab_duns VARCHAR,lab_name VARCHAR,est_duns VARCHAR,est_name VARCHAR,ops VARCHAR)")
con.executemany("INSERT INTO e VALUES (?,?,?,?,?,?)",rows)
con.execute("COPY (SELECT * FROM e) TO '/tmp/estab.parquet' (FORMAT PARQUET)")
print("\n=== operations observed ===",flush=True)
for r in con.execute("""SELECT op, COUNT(*) n FROM (SELECT unnest(str_split(ops,'|')) op FROM e)
  GROUP BY 1 ORDER BY n DESC LIMIT 12""").fetchall(): print(f"  {r[0]:<34}{r[1]:>8,}",flush=True)
print("\n=== coverage ===",flush=True)
r=con.execute("SELECT COUNT(DISTINCT labcode), COUNT(DISTINCT est_duns) FROM e").fetchone()
print(f"  labeler codes with establishment data: {r[0]}   distinct establishments: {r[1]:,}",flush=True)
r=con.execute("""SELECT COUNT(DISTINCT labcode), COUNT(DISTINCT est_duns) FROM e
  WHERE ops LIKE '%MANUFACTURE%' AND ops NOT LIKE '%API MANUFACTURE%'""").fetchone()
print(f"  with a MANUFACTURE operation: {r[0]} labelers, {r[1]:,} establishments",flush=True)
print("\n=== most shared establishments (contract manufacturers) ===",flush=True)
for r in con.execute("""SELECT any_value(est_name) nm, COUNT(DISTINCT labcode) nlab FROM e
  WHERE ops LIKE '%MANUFACTURE%' GROUP BY est_duns HAVING nlab>1 ORDER BY nlab DESC LIMIT 12""").fetchall():
    print(f"  {r[0][:52]:<54}{r[1]:>4} labeler codes",flush=True)
print("\nwrote /tmp/estab.parquet",flush=True)

import csv,os,json,duckdb,re,numpy as np
C=os.path.expanduser("~/mnt/Research/crosswalk")
def norm(s):
    s=(s or '').upper()
    s=re.sub(r'[^A-Z0-9 ]',' ',s)
    for w in (' INC',' LLC',' LTD',' CORP',' CORPORATION',' COMPANY',' CO',' LP',' PLC',' GMBH',
              ' PHARMACEUTICALS',' PHARMACEUTICAL',' PHARMA',' LABORATORIES',' LABORATORY',' LABS',' LAB',
              ' USA',' US',' AMERICA',' HEALTHCARE',' HEALTH',' GROUP',' HOLDINGS',' OPERATING',' PVT',' PRIVATE',' LIMITED'):
        s=s.replace(w,' ')
    return re.sub(r'\s+',' ',s).strip()
lab2name={}
with open(C+"/product.txt",encoding='latin-1') as f:
    for r in csv.DictReader(f,delimiter='\t'):
        ndc=(r.get('PRODUCTNDC') or '').strip()
        if '-' not in ndc: continue
        L=ndc.split('-')[0].zfill(5)
        nm=norm(r.get('LABELERNAME'))
        if nm: lab2name.setdefault(L,set()).add(nm)
with open(C+"/drug-ndc-0001-of-0001.json",encoding='utf-8',errors='replace') as f: dd=json.load(f)
for r in dd.get('results',[]):
    ndc=(r.get('product_ndc') or '')
    if '-' not in ndc: continue
    L=ndc.split('-')[0].zfill(5); nm=norm(r.get('labeler_name'))
    if nm: lab2name.setdefault(L,set()).add(nm)
print("labelers with a name:",len(lab2name),flush=True)
p=os.path.expanduser("~/mnt/Research/enforcement/drug-enforcement-0001-of-0001.json")
rec=[]
for r in json.load(open(p,encoding='utf-8',errors='replace'))['results']:
    rd=str(r.get('recall_initiation_date') or r.get('report_date') or '')
    if len(rd)!=8: continue
    yr,mo=int(rd[:4]),int(rd[4:6])
    rec.append((norm(r.get('recalling_firm')),(yr-2014)*4+((mo-1)//3+1),
                r.get('classification') or '', (r.get('reason_for_recall') or '')[:400]))
print("recalls with usable date:",len(rec),flush=True)
name2lab={}
for L,ns in lab2name.items():
    for n in ns:
        if len(n)>=4: name2lab.setdefault(n,set()).add(L)
hits=[]
for fn,tq,cls,reason in rec:
    if not fn or len(fn)<4: continue
    for L in name2lab.get(fn,()): hits.append((L,tq,cls,reason))
print("recall-to-labeler matches by exact normalised name:",len(hits),flush=True)
con=duckdb.connect()
con.execute("CREATE TABLE rc(lab VARCHAR,tq INT,cls VARCHAR,reason VARCHAR)")
con.executemany("INSERT INTO rc VALUES (?,?,?,?)",hits)
con.execute("COPY (SELECT * FROM rc) TO '/tmp/recalls2.parquet' (FORMAT PARQUET)")
print("distinct labelers matched:",con.execute("SELECT COUNT(DISTINCT lab) FROM rc").fetchone()[0],flush=True)

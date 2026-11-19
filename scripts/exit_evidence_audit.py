"""Evidence inputs for classifying each observed near-sole exit.

Three signals are computed from the panel itself, before any external record is
consulted, because each distinguishes a supply failure from something that only
looks like one:

1. Successor dispensing. If a labeler that was absent before the exit supplies the
   market afterwards, the market was not left unsupplied. In SDUD a transfer of
   marketing rights, a divestiture or a relabelling is indistinguishable from an
   exit, because the labeler code is the identity.

2. A near-identical market key. A misspelling in FDA's free-text ingredient name
   creates a separate market with one labeler beside the real one. The
   normalisation merges only exact token sets after cleaning, so it cannot catch a
   misspelling, and the apparent sole supplier is a measurement artefact.

3. Whether the departing labeler ever returns, which separates an exit from a
   suppression gap.

These are inputs to the classification, not the classification itself; the cause
still rests on public records naming the firm and the period.
"""
import duckdb, csv, json, os, sys, difflib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
_ROOT=os.environ.get("PSDR_ROOT") or os.path.expanduser(
    "~/mnt/Research/pharmaceutical_supply_disruption_research")
con=duckdb.connect(); con.execute("SET memory_limit='2000MB'")
con.execute("CREATE VIEW lmq AS SELECT * FROM read_parquet('/tmp/lmq_v2.parquet')")
keys=[r[0] for r in con.execute("SELECT DISTINCT mkt FROM lmq").fetchall()]
rows=[r for r in csv.DictReader(open(f"{_ROOT}/results/near_sole_event_flow.csv"))
      if r["stage"]=="observed"]
out=[]
for r in rows:
    t=int(r["event_tq"]); m=r["market"]; dl=r["departing_labeler"]
    post,nlab=con.execute("""SELECT COALESCE(SUM(rx),0),COUNT(DISTINCT lab) FROM lmq
      WHERE mkt=? AND lab<>? AND tq BETWEEN ?+1 AND ?+6 AND rx IS NOT NULL""",
      [m,dl,t,t]).fetchone()
    pre=con.execute("""SELECT COALESCE(SUM(rx),0) FROM lmq
      WHERE mkt=? AND lab<>? AND tq BETWEEN ?-4 AND ?-1 AND rx IS NOT NULL""",
      [m,dl,t,t]).fetchone()[0]
    back=con.execute("""SELECT COALESCE(MAX(rx),0) FROM lmq
      WHERE mkt=? AND lab=? AND tq>?+3 AND rx IS NOT NULL""",[m,dl,t]).fetchone()[0]
    # a near-identical key: same route bucket, ingredient string within one or two edits
    ing,buck=m.split(" | ",1)
    twins=[]
    for k in keys:
        if k==m or " | " not in k: continue
        i2,b2=k.split(" | ",1)
        if b2.split(" #")[0]!=buck.split(" #")[0]: continue
        if abs(len(i2)-len(ing))>2: continue
        rat=difflib.SequenceMatcher(None,ing,i2).ratio()
        if rat>=0.9 and i2!=ing:
            n2,rx2=con.execute("""SELECT COUNT(DISTINCT lab),SUM(rx) FROM lmq
              WHERE mkt=? AND rx IS NOT NULL""",[k]).fetchone()
            twins.append(dict(key=k,labelers=n2,rx=round(rx2 or 0,1),similarity=round(rat,3)))
    out.append(dict(market=m,event_quarter=r["event_quarter"],departing_labeler=dl,
        successor_rx_post=round(post,1), successor_labelers_post=nlab,
        other_labeler_rx_pre=round(pre,1),
        new_labeler_appears=bool(post>0 and pre==0),
        departing_labeler_returns=bool(back>0),
        near_identical_keys=sorted(twins,key=lambda x:-x["similarity"])))
json.dump(out,open(f"{_ROOT}/results/exit_evidence_audit.json","w"),indent=1)
n_new=sum(1 for x in out if x["new_labeler_appears"])
n_twin=sum(1 for x in out if x["near_identical_keys"])
print(f"{len(out)} observed near-sole exits audited")
print(f"  a labeler absent before the exit supplies the market after : {n_new}")
print(f"  any successor dispensing at all                            : {sum(1 for x in out if x['successor_rx_post']>0)}")
print(f"  a near-identical market key exists (likely missed merge)    : {n_twin}")
for x in out:
    if x["near_identical_keys"]:
        tw=x["near_identical_keys"][0]
        print(f"\n  {x['market']}")
        print(f"    resembles {tw['key']} ({tw['labelers']} labelers, {tw['rx']:,.0f} rx, "
              f"similarity {tw['similarity']})")

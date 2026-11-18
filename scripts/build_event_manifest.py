import duckdb, os, csv, numpy as np
con = duckdb.connect(); con.execute("SET memory_limit='1500MB'")
MQ = {}
for m, t, r in con.execute("SELECT mol,tq,rx FROM read_parquet('/tmp/molq_nat.parquet')").fetchall():
    MQ.setdefault(m, {})[t] = r
META = {m: (g, f, e) for m, g, f, e in con.execute("SELECT mol,gen,frm,epc FROM read_parquet('/tmp/meta_nat.parquet')").fetchall()}
TMAX = max(t for d in MQ.values() for t in d)
YMIN = (2016 - 1991) * 4 + 1
B0, B1 = -6, -2
SL = con.execute("SELECT mol,lab,t,shr FROM read_parquet('/tmp/sl_nat.parquet')").fetchall()
first = {}
for m, l, t, s in sorted(SL, key=lambda x: x[2]):
    if m not in first: first[m] = (t, s, l)
def basec(m, t):
    p = [MQ[m].get(t + k) for k in range(B0, B1)]
    return None if any(v is None or v <= 0 for v in p) else float(np.mean(p))
def postobs(m, t, H): return any(MQ[m].get(t + k) is not None for k in range(1, H + 1))
def band(s): return "minority" if s < .35 else ("mid" if s < .95 else "sole")
def cal(tq): return f"{1991 + (tq - 1) // 4}Q{(tq - 1) % 4 + 1}"
LOr = YMIN - B0 + 2
COH = [(m, v[0], v[1], v[2]) for m, v in first.items()
       if v[0] >= LOr and v[0] + 11 <= TMAX and basec(m, v[0]) is not None and postobs(m, v[0], 12)]
COH.sort()
PRIM = {m for m, v in first.items() if v[0] >= LOr and basec(m, v[0]) is not None and postobs(m, v[0], 6)}
H = 12
rows = []
for m, t, s, lab in COH:
    bl = basec(m, t)
    traj = [MQ[m].get(t + k) for k in range(1, H + 1)]
    obs = [v for v in traj if v is not None]
    r = dict(market=m, ingredient=META.get(m, ("","",""))[0], dosage_form=META.get(m, ("","",""))[1],
             est_pharm_class=META.get(m, ("","",""))[2], departing_labeler=lab, event_quarter=cal(t),
             event_tq=t, departing_share=round(s,4), band=band(s), in_primary_cohort=int(m in PRIM),
             baseline_rx=round(bl,1), n_post_observed=len(obs))
    for k in range(1, H+1):
        v = traj[k-1]
        r[f"rx_t{k}"] = "" if v is None else round(v,1)
        r[f"ratio_t{k}"] = "" if v is None else round(v/bl,4)
    for thr, tag in [(0.5,"50"), (0.9,"90")]:
        d = next((k for k in range(1,H+1) if (MQ[m].get(t+k) or 0) < thr*bl), None)
        r[f"first_cross_{tag}"] = d if d is not None else ""
        if d is None:
            r[f"first_recover_{tag}"]=""; r[f"time_to_recover_{tag}"]=""
            r[f"followup_after_cross_{tag}"]=""; r[f"censored_{tag}"]=""
        else:
            rq = next((k for k in range(d+1,H+1) if (MQ[m].get(t+k) or 0) >= thr*bl), None)
            r[f"first_recover_{tag}"] = rq if rq is not None else ""
            r[f"time_to_recover_{tag}"] = (rq-d) if rq is not None else ""
            r[f"followup_after_cross_{tag}"] = H-d
            r[f"censored_{tag}"] = 0 if rq is not None else 1
    defs = [max(bl-(MQ[m].get(t+k) or 0.0),0)/bl for k in range(0,H)]
    r["deficit_total_12q"] = round(sum(defs),3)
    r["deficit_post_detection"] = round(sum(defs[4:]),3)
    rows.append(r)
out = os.path.expanduser("~/mnt/Research/pharmaceutical_supply_disruption_research/results/event_level_cohort_manifest.csv")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out,"w",newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
import collections
print(f"events: {len(rows)}")
print("bands:", dict(collections.Counter(r['band'] for r in rows)))
print("in primary cohort:", sum(r['in_primary_cohort'] for r in rows))
print("\nsole events (the 16):")
for r in rows:
    if r["band"]=="sole":
        print(f"  {r['event_quarter']}  share={r['departing_share']:.3f}  base={r['baseline_rx']:>9.1f}  {r['market'][:52]:<52} | {r['departing_labeler'][:34]}")
print("\nwrote", out)

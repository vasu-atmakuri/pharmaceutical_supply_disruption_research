"""Build the clinical plausibility adjudication sheet.

The normalisation rule merges raw market keys whose ingredient token sets agree after
counterion stripping. RxNorm tests that against a terminology authority
(rxnorm_market_equivalence.py). This stage prepares the other test: whether a clinician
reading the two product descriptions would treat them as one market, which is a question
about substitutability rather than about ingredient identity.

One row per merge group. The adjudicator sees only what a clinician needs to judge the
merge: the raw ingredient strings, the route-and-form bucket, and the dispensing volume
each raw key carried. The pipeline's verdict is deliberately withheld from the sheet so
that the adjudication is not anchored on it; it is in the key file, which the analysis
joins afterwards.

Writes results/clinical_adjudication_sheet.csv (to send out) and
results/clinical_adjudication_key.csv (kept back until the sheet comes in).
"""
import os, sys, json, csv, collections, hashlib

R = os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XW = os.environ.get("PSDR_XW", "/tmp/xw_route.parquet")
MAP_PATH = f"{R}/results/market_key_normalization_map.json"

nmap = json.load(open(MAP_PATH))
groups = collections.defaultdict(list)
for raw, final in nmap.items():
    groups[final].append(raw)
merged = {f: sorted(ks) for f, ks in groups.items() if len(ks) > 1}

# dispensing volume per raw key, so the adjudicator can see which merges carry weight
vol = {}
try:
    import duckdb
    con = duckdb.connect()
    con.execute("SET threads TO 4")
    rows = con.execute(f"""
      WITH xw AS (SELECT lab, pcode, generic, form, route FROM read_parquet('{XW}')),
      p AS (SELECT lab, pcode, SUM(rx) rx FROM read_parquet('{R}/data/sdud_parts/*.parquet')
            GROUP BY 1,2)
      SELECT x.generic AS g, SUM(p.rx) AS rx
      FROM p JOIN xw x USING (lab, pcode)
      GROUP BY 1""").fetchall()
    vol = {g: rx for g, rx in rows if g}
except Exception as e:
    print(f"  dispensing volume unavailable ({type(e).__name__}); the sheet will omit it")


def ing(k):
    return k.split("|")[0].strip()


def buck(k):
    return k.split("|", 1)[1].strip() if "|" in k else ""


sheet, key = [], []
for final in sorted(merged):
    ks = merged[final]
    rid = "M" + hashlib.sha1(final.encode()).hexdigest()[:6].upper()
    names = [ing(k) for k in ks]
    v = [vol.get(n) for n in names]
    sheet.append({
        "merge_id": rid,
        "route_and_form": buck(ks[0]),
        "n_products_merged": len(ks),
        "product_names_as_reported": " || ".join(names),
        "medicaid_prescriptions_2016_2026": " || ".join(
            f"{int(x):,}" if x else "not available" for x in v),
        "same_market": "",
        "confidence": "",
        "why": "",
    })
    key.append({"merge_id": rid, "normalised_key": final,
                "raw_keys": " || ".join(ks), "n_raw_keys": len(ks)})

os.makedirs(f"{R}/results", exist_ok=True)
for name, data in [("clinical_adjudication_sheet", sheet), ("clinical_adjudication_key", key)]:
    with open(f"{R}/results/{name}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
        w.writeheader()
        w.writerows(data)

print(f"{len(sheet)} merge groups to adjudicate, covering "
      f"{sum(r['n_products_merged'] for r in sheet)} reported product names")
print("wrote results/clinical_adjudication_sheet.csv (send this one)")
print("wrote results/clinical_adjudication_key.csv  (keep this one back)")

# An .xlsx alongside the CSV, because the adjudicator fills this in by hand: the verdict
# and confidence columns are dropdowns, so the returned file needs no cleaning.
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Adjudication"
    HEAD = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    BODY = Font(name="Arial", size=10)
    HFILL = PatternFill("solid", fgColor="2F4F6F")
    YOURS = PatternFill("solid", fgColor="FFF6CC")
    THIN = Border(bottom=Side(style="thin", color="D9D9D9"))

    note = ("Fill in the three shaded columns. same_market: yes, no or unsure. "
            "confidence: high, medium or low. why: one short line, and required only "
            "when same_market is no or unsure.")
    ws["A1"] = note
    ws["A1"].font = Font(name="Arial", size=10, italic=True)
    ws.merge_cells("A1:H1")
    ws.row_dimensions[1].height = 30
    ws["A1"].alignment = Alignment(wrap_text=True, vertical="center")

    cols = ["merge_id", "route_and_form", "n_products_merged", "product_names_as_reported",
            "medicaid_prescriptions_2016_2026", "same_market", "confidence", "why"]
    widths = [11, 20, 9, 62, 26, 13, 12, 44]
    for j, (c, wd) in enumerate(zip(cols, widths), 1):
        cell = ws.cell(row=2, column=j, value=c)
        cell.font = HEAD
        cell.fill = HFILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(j)].width = wd
    ws.freeze_panes = "A3"

    for i, r in enumerate(sheet, start=3):
        for j, c in enumerate(cols, 1):
            cell = ws.cell(row=i, column=j, value=r[c])
            cell.font = BODY
            cell.border = THIN
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if c in ("same_market", "confidence", "why"):
                cell.fill = YOURS

    last = len(sheet) + 2
    dv1 = DataValidation(type="list", formula1='"yes,no,unsure"', allow_blank=True, showDropDown=False)
    dv2 = DataValidation(type="list", formula1='"high,medium,low"', allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv1)
    ws.add_data_validation(dv2)
    dv1.add(f"F3:F{last}")
    dv2.add(f"G3:G{last}")

    wb.save(f"{R}/results/clinical_adjudication_sheet.xlsx")
    print("wrote results/clinical_adjudication_sheet.xlsx (send this one instead of the CSV)")
except ImportError:
    print("  openpyxl unavailable; the CSV is the only sheet written")

"""Human-readable names for the corrected market keys that appear in the paper.

Both the reclassification table and Figure 1(a) label the same seven events. Keeping
two copies of the mapping let the table say "capsule" while the figure said "tablet"
for the same amphetamine market. This is the single source; both import it and both
fail loudly on a key it does not cover.
"""
DISPLAY={
 "BENZTROPINE | ORAL TABLET":"Benztropine, tablet",
 "RANITIDINE | ORAL CAPSULE":"Ranitidine, capsule",
 "AMPHETAMINE,ASPARTATE,DEXTROAMPHETAMINE,SACCHARATE,SULFATE | ORAL CAPSULE":
     "Mixed amphetamine salts, capsule",
 "TERBINAFINE | ORAL TABLET":"Terbinafine, tablet",
 "DORZOLAMIDE,HYDROCHLORIDE,MALEATE,TIMOLOL | OPHTHALMIC":"Dorzolamide and timolol, ophthalmic",
 "PREGABALIN | ORAL CAPSULE":"Pregabalin, capsule",
 "TARTRATE,VARENICLINE | OTHER":"Varenicline, other",
 "TARTRATE,VARENICLINE | ORAL TABLET":"Varenicline, oral tablet",
}
LABELER={"69097":"Cipla","55111":"Dr. Reddy's","27241":"Ajanta","42858":"Rhodes",
         "69315":"Leading","00069":"Pfizer"}

def name(corrected_market):
    if corrected_market not in DISPLAY:
        raise SystemExit(f"display_names.py has no entry for corrected market "
                         f"{corrected_market!r}; add it rather than labelling by hand")
    return DISPLAY[corrected_market]

def labeler(code):
    c=str(code).zfill(5)
    if c not in LABELER:
        raise SystemExit(f"display_names.py has no entry for labeler code {c!r}")
    return LABELER[c]

# Labels for the four evidence levels in the exit classification, ordered weakest
# claim to strongest. The level names are what cause_strata.py writes; these are what
# the paper prints, and they must say what the evidence does and does not establish.
CAUSE_LABEL={
 "supply":      "documented supply disruption",
 "withdrawal":  "market-wide regulatory withdrawal",
 "transition":  "regulatory-transition-associated",
 "undetermined":"undetermined",
}
CAUSE_ORDER=["supply","withdrawal","transition","undetermined"]
# Market names as they appear in the exit table, keyed by the normalised market key.
EVENT_MARKET={
 "ACETATE,ACID,ALPHA,ASCORBIC,BETA,BIOTIN,CAROTENE,CHOLECALCIFEROL,CUPRIC,CYANOCOBALAMIN,FLUORIDE,FOLIC,GLUCONATE,GLUCOSAMINE,LEVOMEFOLATE,NIACINAMIDE,OXIDE,PYRIDOXINE,RIBOFLAVIN,SODIUM,THIAMINE,TOCOPHEROL,VITAMIN,ZINC | ORAL TABLET":
   "Multivitamin with minerals, oral tablet",
 "ACID,FOLIC,IRON,MINERAL,SUPPLEMENT,VITAMIN | OTHER":"Iron, folic acid, vitamin, other",
 "ACETIC,ACID,HYDROCORTISONE | OTIC":"Hydrocortisone and acetic acid, otic",
 "DICLOFENAC,POTASSIUM | ORAL TABLET":"Diclofenac potassium, oral tablet",
 "RANITIDINE | ORAL TABLET":"Ranitidine, oral tablet",
 "BRIMONIDINE,BRINZOLAMIDE,TARTRATE | OPHTHALMIC":"Brinzolamide and brimonidine, ophthalmic",
 "HYDROCHLORIDE,OLOPATADINE | OPHTHALMIC":"Olopatadine, ophthalmic",
 "TARTRATE,VARENICLINE | OTHER":"Varenicline, other",
 "VARENICLINE | ORAL TABLET":"Varenicline, oral tablet",
 "GOSERELIN | INJECTABLE":"Goserelin, injectable",
 "TRIMETHOPRIM | ORAL TABLET":"Trimethoprim, oral tablet",
 "ALCAFTADINE | OPHTHALMIC":"Alcaftadine, ophthalmic",
 "GRISOFULVIN | ORAL LIQUID":"Griseofulvin, oral liquid",
}
EVENT_LABELER={"BonGeo":"BonGeo"}

def event_market(key):
    if key not in EVENT_MARKET:
        raise SystemExit(f"display_names.py has no event-table name for {key!r}")
    return EVENT_MARKET[key]
def cause_label(level):
    if level not in CAUSE_LABEL:
        raise SystemExit(f"display_names.py has no label for cause level {level!r}")
    return CAUSE_LABEL[level]

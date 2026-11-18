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

#!/bin/bash
# One pipeline, in dependency order. Three ordering rules are enforced here rather
# than remembered:
#   1. figures are built AFTER every panel rebuild, which is what let Figure 1(b)
#      and Figure 2(b) lag the market panel;
#   2. the LaTeX macros and tables are emitted after every results file is written,
#      so no reported number is ever typed by hand;
#   3. the manuscript is compiled before the checks, and the checks run last.
set -e
cd "$(dirname "$0")"
# Every stage lives in this folder. Set PSDR_ROOT and RESEARCH_ROOT to run outside
# the analysis VM; they default to the VM's mount points.
W="$(pwd)"
export PSDR_ROOT="${PSDR_ROOT:-$(cd .. && pwd)}"
export RESEARCH_ROOT="${RESEARCH_ROOT:-$(cd ../.. && pwd)}"
echo "repo:  $PSDR_ROOT"
echo "data:  $RESEARCH_ROOT"
for f in rebuild_xw_route natpanel_route build_v2 validate_normalization national_impact \
         concentration_abc reclass_multi inference cause_strata recovery_censored deficit_entry \
         threespec transition sole_flow_manifest recall_matchlevel sensitivities \
         collect_numbers build_figures emit_tex; do
  [ -f "$W/$f.py" ] || { echo "missing stage: $W/$f.py"; exit 1; }
done
S="$PSDR_ROOT/springer"

echo "== 1. crosswalk with route =="        ; python3 $W/rebuild_xw_route.py       >/dev/null
echo "== 2. route-aware panel =="           ; python3 $W/natpanel_route.py         >/dev/null
echo "== 3. normalised panel + events =="   ; python3 $W/build_v2.py               | head -3
echo "== 4. normalisation validation =="    ; python3 $W/validate_normalization.py | head -6
echo "== 5. national concentration =="      ; python3 $W/national_impact.py        >/dev/null
echo "== 6. A/B/C decomposition =="         ; python3 $W/concentration_abc.py      >/dev/null
echo "== 7. mapping rules =="               ; python3 $W/reclass_multi.py          | tail -5
echo "== 8. inference =="                   ; python3 $W/inference.py              | tail -4
echo "== 9. cause strata =="                ; python3 $W/cause_strata.py           >/dev/null
echo "==10. recovery =="                    ; python3 $W/recovery_censored.py      >/dev/null
echo "==11. deficits and entry =="          ; python3 $W/deficit_entry.py          >/dev/null
echo "==12. three specifications =="        ; python3 $W/threespec.py              >/dev/null
echo "==13. event transition =="            ; python3 $W/transition.py             | tail -3
echo "==13b. near-sole flow manifest ==" ; python3 $W/sole_flow_manifest.py | tail -6
echo "==14. recall match level =="          ; python3 $W/recall_matchlevel.py      | tail -4
echo "==15. sensitivities =="               ; python3 $W/sensitivities.py          >/dev/null
echo "==16. collected numbers =="           ; python3 $W/collect_numbers.py        >/dev/null
echo "==17. FIGURES (after the panel) =="   ; python3 $W/build_figures.py          | tail -4
echo "==18. LaTeX macros and tables =="     ; python3 $W/emit_tex.py               | head -1

echo "==19. compile the manuscript =="
cd "$S"
rm -f manuscript.aux manuscript.bbl manuscript.blg
pdflatex -interaction=nonstopmode manuscript.tex >/tmp/tex1.log 2>&1
bibtex manuscript >/tmp/bib.log 2>&1
pdflatex -interaction=nonstopmode manuscript.tex >/tmp/tex2.log 2>&1
pdflatex -interaction=nonstopmode manuscript.tex >/tmp/tex3.log 2>&1
E=$(grep -c '^!' /tmp/tex3.log || true)
echo "   LaTeX errors: $E, pages: $(pdfinfo manuscript.pdf | awk '/Pages/{print $2}')"
if [ "$E" != "0" ]; then grep -A3 '^!' /tmp/tex3.log | head -20; exit 1; fi
cd - >/dev/null

echo "==20. CHECKS (last, always) =="
python3 audit_numbers.py
python3 verify_manuscript.py
python3 check_relationships.py
python3 audit_letter.py
python3 check_determinism.py

# Note: stages 1 to 6 rebuild the panels from the raw SDUD and FDA listings and take
# the bulk of the runtime. Running the whole file takes roughly 6 to 8 minutes on a
# warm machine; it must be run in a session that stays alive for its duration.

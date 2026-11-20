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
# Interpreter. A repo-local .venv wins if present, because Homebrew python3 refuses
# pip installs under PEP 668 and may be missing packages the pipeline needs. Override
# with PY=/path/to/python.
if [ -z "$PY" ]; then
  if   [ -x "$(cd .. && pwd)/.venv/bin/python" ]; then PY="$(cd .. && pwd)/.venv/bin/python"
  else PY="python3"; fi
fi
export PY
echo "python: $PY"
export PSDR_ROOT="${PSDR_ROOT:-$(cd .. && pwd)}"
export RESEARCH_ROOT="${RESEARCH_ROOT:-$(cd ../.. && pwd)}"
# Where the per-year SDUD parquet parts live. Stage 0 builds them if absent.
export SDUD_PARTS="${SDUD_PARTS:-$RESEARCH_ROOT/sdud_parts/*.parquet}"
echo "repo:  $PSDR_ROOT"
echo "data:  $RESEARCH_ROOT"
echo "parts: $SDUD_PARTS"
for f in build_sdud_parts rebuild_xw_route xwalk natpanel natpanel_route build_v2 validate_normalization national_impact \
         concentration_abc reclass_multi inference cause_strata recovery_censored deficit_entry \
         threespec transition sole_flow_manifest recall_matchlevel sensitivities \
         route_unknown_sensitivity exit_evidence_audit detector_variants collect_numbers \
         build_figures emit_tex emit_appendix_tables emit_letter_numbers; do
  [ -f "$W/$f.py" ] || { echo "missing stage: $W/$f.py"; exit 1; }
done
S="$PSDR_ROOT/springer"

echo "== preflight: interpreter, packages, TeX =="
"$PY" "$W/check_environment.py" || exit 1

echo "== 0. SDUD year parts (skips what exists) ==" ; "$PY" $W/build_sdud_parts.py | tail -3
echo "== 1a. crosswalk with route =="      ; "$PY" $W/rebuild_xw_route.py    >/dev/null
echo "== 1b. form-only crosswalk =="       ; "$PY" $W/xwalk.py               | tail -1
echo "== 2a. form-based panel (spec A) ==" ; "$PY" $W/natpanel.py             >/dev/null
echo "== 2b. route-aware panel (spec B) ==" ; "$PY" $W/natpanel_route.py       >/dev/null
echo "== 3. normalised panel + events =="   ; "$PY" $W/build_v2.py               | head -3
echo "== 4. normalisation validation =="    ; "$PY" $W/validate_normalization.py | head -6
echo "== 5. national concentration =="      ; "$PY" $W/national_impact.py        >/dev/null
echo "== 6. A/B/C decomposition =="         ; "$PY" $W/concentration_abc.py      >/dev/null
echo "== 7. mapping rules =="               ; "$PY" $W/reclass_multi.py          | tail -5
echo "== 8. inference =="                   ; "$PY" $W/inference.py              | tail -4
echo "== 9. cause strata =="                ; "$PY" $W/cause_strata.py           >/dev/null
echo "==10. recovery =="                    ; "$PY" $W/recovery_censored.py      >/dev/null
echo "==11. deficits and entry =="          ; "$PY" $W/deficit_entry.py          >/dev/null
echo "==12. three specifications =="        ; "$PY" $W/threespec.py              >/dev/null
echo "==13. event transition =="            ; "$PY" $W/transition.py             | tail -3
echo "==13b. near-sole flow manifest ==" ; "$PY" $W/sole_flow_manifest.py | tail -6
echo "==13d. exit evidence audit ==" ; "$PY" $W/exit_evidence_audit.py | head -4
echo "==13c. unknown-route sensitivity ==" ; "$PY" $W/route_unknown_sensitivity.py | tail -4
echo "==13e. detector window variants ==" ; "$PY" $W/detector_variants.py | tail -5
echo "==14. recall match level =="          ; "$PY" $W/recall_matchlevel.py      | tail -4
echo "==15. sensitivities =="               ; "$PY" $W/sensitivities.py          >/dev/null
echo "==16. collected numbers =="           ; "$PY" $W/collect_numbers.py        >/dev/null
echo "==17. FIGURES (after the panel) =="   ; "$PY" $W/build_figures.py          | tail -4
echo "==18. LaTeX macros and tables =="     ; "$PY" $W/emit_tex.py               | head -1
echo "==18a. appendix tables ==" ; "$PY" $W/emit_appendix_tables.py | tail -1
echo "==18b. response-letter numbers =="     ; "$PY" $W/emit_letter_numbers.py   | tail -1

# The document build needs a TeX distribution and poppler. Both are large and the
# analysis needs neither, so their absence skips the compile and the two checks that
# read a PDF rather than failing the run. SKIP_DOC_BUILD=1 forces that path.
HAVE_TEX=0; HAVE_POPPLER=0
command -v pdflatex >/dev/null 2>&1 && command -v bibtex >/dev/null 2>&1 && HAVE_TEX=1
command -v pdftotext >/dev/null 2>&1 && command -v pdfinfo >/dev/null 2>&1 && HAVE_POPPLER=1
if [ -n "$SKIP_DOC_BUILD" ]; then HAVE_TEX=0; HAVE_POPPLER=0; fi

if [ "$HAVE_TEX" = 1 ] && [ "$HAVE_POPPLER" = 1 ]; then
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
else
echo "==19. compile the manuscript == SKIPPED"
echo "   pdflatex or poppler is not on PATH, so the PDF is not rebuilt here. Every"
echo "   analysis result and every generated number above is still current; only the"
echo "   compiled document is stale. See SETUP.md."
fi

echo "==20. CHECKS (last, always) =="
"$PY" audit_numbers.py
if [ "$HAVE_TEX" = 1 ] && [ "$HAVE_POPPLER" = 1 ]; then "$PY" verify_manuscript.py
else echo "verify_manuscript.py SKIPPED (needs pdflatex and poppler: it inspects the rendered PDF)"; fi
if [ "$HAVE_POPPLER" = 1 ]; then "$PY" check_relationships.py
else echo "check_relationships.py SKIPPED (needs poppler: it reads the figure PDFs)"; fi
"$PY" audit_letter.py
"$PY" check_pipeline_closure.py
"$PY" check_stage_portability.py
"$PY" check_released_files.py
"$PY" check_readme.py
"$PY" check_determinism.py

echo
if [ "$HAVE_TEX" = 1 ] && [ "$HAVE_POPPLER" = 1 ]; then
  echo "ALL STAGES AND CHECKS COMPLETE"
else
  echo "ANALYSIS COMPLETE; THE DOCUMENT BUILD WAS SKIPPED"
  echo "  Install poppler (brew install poppler) to enable check_relationships.py,"
  echo "  and a TeX distribution to compile the manuscript and run verify_manuscript.py."
fi

# Note: stages 1 to 6 rebuild the panels from the raw SDUD and FDA listings and take
# the bulk of the runtime. Running the whole file takes roughly 6 to 8 minutes on a
# warm machine; it must be run in a session that stays alive for its duration.

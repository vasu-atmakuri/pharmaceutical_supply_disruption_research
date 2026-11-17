# Springer manuscript: compile instructions

## Files
- `manuscript.tex` the manuscript
- `refs.bib` references (11 entries, all verified against publisher records)
- `fig1.pdf` Figure 1, vector
- `sn-jnl.cls` Springer Nature class
- `sn-vancouver-num.bst` Vancouver numbered style (health sciences)
- `sn-basic.bst` alternative Springer basic style
- `manuscript.pdf` compiled output, 11 pages

## Compile, about 20 seconds
```
pdflatex manuscript && bibtex manuscript && pdflatex manuscript && pdflatex manuscript
```

Or on Overleaf: upload all files, set `manuscript.tex` as the main document.

## Before submitting
1. Replace `INSERT-CORRESPONDING-EMAIL` on line 19 with the corresponding author email.
2. Add Souseelya's affiliation details on the `\affil[2]` line if she wants more than
   "Independent Researcher".
3. Add ORCIDs with `\orcid{...}` inside each `\author` block once the ORCID record is public.
4. Switch reference style if the target journal requires it: change the class option
   `sn-vancouver-num` and the `\bibliographystyle` line together.

## Notes on the class
The class is loaded with `natbib` in numbers mode. The class does not load natbib itself, and
the `.bst` emits author-year `\bibitem` labels, so without natbib the citation numbers render
empty. Keep that `\usepackage[numbers,sort&compress]{natbib}` line.

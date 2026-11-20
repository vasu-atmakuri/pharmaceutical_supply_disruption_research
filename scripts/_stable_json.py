"""Store computed floats at a precision the pipeline can actually reproduce.

The panels are built by a parallel aggregation whose float summation order is not
fixed, so rebuilding them from the same raw files can move a sum by one unit in the
last place. That is invisible in anything the paper reports, but it propagated into
the sixteenth and seventeenth digits of stored means, HHIs and p-values, which made
artifacts differ from a fresh run and the determinism check fail for a reason that
had nothing to do with the analysis.

Rounding to twelve significant digits absorbs that noise. The paper reports at most
four, so this cannot conceal a change that matters: a difference the rounding hides is
at least eight orders of magnitude smaller than anything printed. Counts and integers
pass through untouched.
"""
SIGDIGITS = 12

def stable(x, nd=SIGDIGITS):
    """Recursively round every float in a JSON-ready structure to nd significant digits."""
    if isinstance(x, bool) or x is None or isinstance(x, int):
        return x
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            return x
        return float(f"{x:.{nd}g}")
    if isinstance(x, dict):
        return {k: stable(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [stable(v, nd) for v in x]
    return x

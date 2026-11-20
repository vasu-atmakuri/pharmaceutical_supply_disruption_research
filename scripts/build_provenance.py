"""Record which commit produced this build, so the paper can be pinned to it.

A reproducibility package that does not say which version it is cannot be checked
against the paper: a reader who clones the repository gets whatever is on the branch
today, which may be a later revision or an earlier one. This writes the commit the
build ran from, the remote it came from, and whether the working tree had uncommitted
changes at the time. The last field is the one that matters: a build from a dirty
tree is not reproducible from any commit, and saying so is more useful than omitting
it.

The submission procedure is in SETUP.md: commit everything, run this stage again, and
commit the file it writes. That final commit is the one the paper cites.
"""
import json, os, subprocess, sys, datetime
R=os.environ.get("PSDR_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def git(*a):
    p=subprocess.run(["git","-C",R,*a],capture_output=True,text=True)
    return p.stdout.strip() if p.returncode==0 else None

commit=git("rev-parse","HEAD")
if not commit:
    print("not a git repository; writing no provenance")
    sys.exit(0)
status=git("status","--porcelain") or ""
dirty=[l for l in status.splitlines() if l.strip()]
out={
 "commit": commit,
 "commit_short": commit[:12],
 "branch": git("rev-parse","--abbrev-ref","HEAD"),
 "remote": git("config","--get","remote.origin.url"),
 "commit_date": git("log","-1","--format=%cI"),
 "built_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
 "working_tree_clean": not dirty,
 "uncommitted_paths": sorted(l[3:] for l in dirty)[:40],
 "uncommitted_count": len(dirty),
 "note": ("The commit this build ran from. working_tree_clean is false when the build "
          "included changes that are not in any commit, in which case the build is not "
          "reproducible from this commit and the paper should not cite it. Re-run this "
          "stage after committing and commit the result."),
}
p=f"{R}/results/build_provenance.json"
json.dump(out,open(p,"w"),indent=1,sort_keys=True)
print(f"commit {out['commit_short']} on {out['branch']}, "
      f"working tree {'clean' if out['working_tree_clean'] else f'DIRTY ({len(dirty)} paths)'}")
print("wrote results/build_provenance.json")

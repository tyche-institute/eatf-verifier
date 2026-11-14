"""Static count for a candidate, with the toolkit's own enumerators: the
checks (all, and reachable from the named entry points) and the negative-test
blocks (all, calling an entry point, included). No target, no run.

    python3 -I survey.py TOOLKIT CLONE PACKAGE ENTRY[,ENTRY] BASE[,BASE] TESTS[,TESTS] [--checks] [--blocks]

CLONE is the directory that holds the import package; TESTS are relative to it.
Classes are labelled as in checks.json (a bare name when no other class
statement of the package has it, else `<module>.<qualified name>`; an imported
class from outside the package by its dotted path). A rejection base that is
neither a built-in class nor the label of exactly 1 package class stops the
count of that candidate; the reason is printed and the exit status stays 0, so
that a recount goes on with the next candidate.
"""
import sys
from collections import Counter
from pathlib import Path

toolkit, clone, package, entries, bases, tests = sys.argv[1:7]
sys.path.insert(0, toolkit)
from reach.blocks import enumerate_blocks  # noqa: E402
from reach.checks import enumerate_checks  # noqa: E402

clone = Path(clone)
pkg = clone.joinpath(*package.split("."))
files = sorted(p.relative_to(clone).as_posix() for p in pkg.rglob("*.py"))
subject = {"name": "draft", "package": package, "source_root": ".", "subject_files": files,
           "observed_files": [], "entry_points": entries.split(","),
           "rejection_bases": bases.split(","), "tests": tests.split(",")}
try:
    checks = enumerate_checks(subject, clone)
except SystemExit as stop:
    print(f"package files {len(files)}; stopped: {stop}")
    sys.exit(0)
blocks = enumerate_blocks(subject, clone, checks)
cs = checks["checks"]
print(f"package files {len(files)}; checks {len(cs)}; reachable {sum(c['reachable'] for c in cs)}; "
      f"rejection classes {len(checks['rejection_classes'])}")
print("reachable checks by class:", dict(Counter(c["class"] for c in cs if c["reachable"]).most_common(12)))
print("blocks", blocks["counts"], "in", len(blocks["test_files"]), "test files")
inc = [b for b in blocks["blocks"] if b["included"]]
print("included by file:", dict(Counter(b["file"] for b in inc)))
print("included by expected:", dict(Counter(" | ".join(b["expected"]) for b in inc).most_common(20)))
msg = sum(1 for b in inc if b["match"] is not None or b["match_unparsed"] or b["post"] or b["post_unparsed"])
print(f"included asserting more than the class: {msg} of {len(inc)}")
called = [b for b in blocks["blocks"] if b["entry_calls"] and not b["included"]]
print("entry-point blocks not included:", dict(Counter("; ".join(b["exclusion"]) for b in called).most_common(20)))
if "--checks" in sys.argv:
    for c in cs:
        if c["reachable"]:
            print("   check", c["id"], c["class"], repr(c["template"])[:60], "raise statements:", len(c["lines"]))
if "--blocks" in sys.argv:
    for b in inc:
        print("   block", b["key"], b["expected"], b["entry_calls"])

"""Judge a vectors report against the declared exclusions in conformance_exclusions.json.

Exit 0 when the run is complete and every failing vector is a declared exclusion.
Exit 1 on an undeclared failure, an incomplete run, or a declared exclusion that now passes.
"""
import json
import pathlib
import sys


def main(report_path):
    here = pathlib.Path(__file__).resolve().parent
    declared = json.loads((here / "conformance_exclusions.json").read_text(encoding="utf-8"))
    excluded = {row["id"]: row["reason"] for row in declared["exclusions"]}
    report = json.loads(pathlib.Path(report_path).read_text(encoding="utf-8"))
    totals = report["totals"]
    rows = {row["id"]: row for row in report["vectors"]}
    problems = []
    if len(rows) != totals["vectors"] or totals["suiteRefusals"] != 0:
        problems.append("the run is incomplete: %d of %d vectors, %d suite refusals"
                        % (len(rows), totals["vectors"], totals["suiteRefusals"]))
    for vid, row in sorted(rows.items()):
        failed = row["status"] != "PASS"
        if failed and vid not in excluded:
            problems.append("undeclared failure %s: %s" % (vid, "; ".join(row["reasons"])))
        if not failed and vid in excluded:
            problems.append("declared exclusion %s now passes; remove it from conformance_exclusions.json" % vid)
    for vid in sorted(set(excluded) - set(rows)):
        problems.append("declared exclusion %s is not in the corpus" % vid)
    for vid, reason in sorted(excluded.items()):
        print("declared exclusion %s: %s See %s" % (vid, reason, declared["docs"]))
    for line in problems:
        print("::error::" + line)
    print("%d of %d vectors pass, %d declared exclusions" % (totals["pass"], totals["vectors"], len(excluded)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

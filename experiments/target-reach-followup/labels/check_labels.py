"""Validate a labels file against a reading pack.

    python3 -I -B labels/check_labels.py --pack <pack> --labels <labels.tsv> [--json <report.json>]

First the pack is checked against its MANIFEST.txt (no file changed, missing
or added). Then the labels file must hold the columns block, label, basis,
quote, note, and:

- every included block of blocks.tsv exactly once, and no other block;
- label: a check id of checks.tsv, the word `none`, or `by-param <name>:
  <value>=<id or none>; ...` for a block whose described check depends on a
  parameter of the test (at least 2 values);
- basis: `none`, or a combination of `class`, `assert` and `name` joined by
  `+`; label `none` goes with basis `none` and the reason in the note, and a
  label that names a check goes with a basis other than `none`.

Reported apart, and allowed: labels whose check raises a class that is
neither an expected class of the block nor a subclass of one (classes.tsv
gives the declared bases; a built-in class gives the bases of the
interpreter), and labels with a basis but no quote (warnings).

Exit status 0 when the file is valid, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from labelslib import Universe, label_text, read_tsv, report_text, validate_labels  # noqa: E402
from prepare import verify_manifest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pack", required=True, type=Path)
    ap.add_argument("--labels", required=True, type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    problems = verify_manifest(a.pack)
    if problems:
        print("check_labels: the pack does not match its MANIFEST.txt:\n  " + "\n  ".join(problems))
        return 1
    uni = Universe.from_pack(a.pack)
    header, rows = read_tsv(a.labels)
    result = validate_labels(header, rows, uni)
    print(report_text(result, a.labels.name), end="")
    if a.json:
        doc = {k: v for k, v in result.items() if k not in ("labels", "bases")}
        doc["labels"] = {k: label_text(v) for k, v in sorted(result["labels"].items())}
        doc["bases"] = {k: "+".join(v) for k, v in sorted(result["bases"].items())}
        a.json.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())

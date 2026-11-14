"""Verify the transcriptions of the first reading of the flags.

    python3 -I -B labels/check_first.py [name ...]

For each name (default: jwcrypto, google-auth, oauthlib, authlib, joserfc),
reads labels/first/<name>.tsv and, from ../target-reach/, the files
generated/<name>/flags.csv, generated/<name>/cases.csv,
subjects/<name>/checks.json and readings/<name>/FLAGS.md, and checks that:

1. the rows list the flags of flags.csv in its order: the same block,
   index, target and deciding check;
2. the test node of each row is a case of cases.csv with that block and
   index whose raise site is not its target, and no case is listed twice;
3. the class is A, B, C or D, and the counts per class equal the line
   "Counts: A n, B n, C n, D n." of FLAGS.md;
4. the described check is empty (and then the note is not) or a check id of
   checks.json;
5. every quote occurs in FLAGS.md, white space collapsed;
6. every quote names the described check in backquotes: by its full id, by
   a suffix of the id that starts after a '.', or, for the identifiers that
   FLAGS.md shortens with a prefix such as `ac.`, by the part after that
   prefix as such a suffix.

Exit status 0 when every check holds for every name.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
E = HERE.parent.parent / "target-reach"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from labelslib import normalize_ws, read_csv, read_tsv  # noqa: E402

NAMES = ["jwcrypto", "google-auth", "oauthlib", "authlib", "joserfc"]
COLUMNS = ["block", "index", "test_node", "class", "target", "deciding_check", "described_check", "quote", "note"]


def names_check(quote: str, cid: str) -> bool:
    for t in re.findall(r"`([^`]+)`", quote):
        if t == cid or cid.endswith("." + t):
            return True
        head, dot, rest = t.partition(".")
        if dot and rest and cid.endswith("." + rest):
            return True
    return False


def check(name: str, toolkit: Path = E, first_dir: Path = HERE / "first") -> list[str]:
    problems = []
    header, rows = read_tsv(first_dir / f"{name}.tsv")
    if header != COLUMNS:
        return [f"{name}: header {header}, expected {COLUMNS}"]
    flags = read_csv(toolkit / "generated" / name / "flags.csv")
    cases = read_csv(toolkit / "generated" / name / "cases.csv")
    ids = {c["id"] for c in json.loads((toolkit / "subjects" / name / "checks.json")
                                       .read_text(encoding="utf-8"))["checks"]}
    md_raw = (toolkit / "readings" / name / "FLAGS.md").read_text(encoding="utf-8")
    md = normalize_ws(md_raw)
    if [(r["block"], r["index"], r["target"], r["deciding_check"]) for r in rows] != \
            [(f["block"], f["index"], f["target"], f["deciding_check"]) for f in flags]:
        problems.append(f"{name}: the rows do not list the flags of flags.csv in order")
    flagged = {(c["test_node"], c["block"], c["index"]) for c in cases
               if c["target"] and c["baseline_site"] != c["target"]}
    seen = set()
    for r in rows:
        line = r["__line__"]
        k = (r["test_node"], r["block"], r["index"])
        if k not in flagged:
            problems.append(f"{name} line {line}: {k} is not a flagged case of cases.csv")
        if k in seen:
            problems.append(f"{name} line {line}: case listed twice")
        seen.add(k)
        if r["class"] not in ("A", "B", "C", "D"):
            problems.append(f"{name} line {line}: class {r['class']!r}")
        cid = r["described_check"]
        if not cid and not r["note"].strip():
            problems.append(f"{name} line {line}: empty described check without a note")
        if cid and cid not in ids:
            problems.append(f"{name} line {line}: {cid} is not a check id of checks.json")
        if normalize_ws(r["quote"]) not in md:
            problems.append(f"{name} line {line}: the quote does not occur in FLAGS.md")
        if cid and not names_check(r["quote"], cid):
            problems.append(f"{name} line {line}: the quote does not name {cid}")
    m = re.search(r"Counts: A (\d+), B (\d+), C (\d+), D (\d+)\.", md_raw)
    got = Counter(r["class"] for r in rows)
    if not m:
        problems.append(f"{name}: no line of counts in FLAGS.md")
    elif [int(x) for x in m.groups()] != [got.get(c, 0) for c in "ABCD"]:
        problems.append(f"{name}: counts per class {dict(got)} differ from FLAGS.md {m.group(0)}")
    return problems


def main(argv: list[str] | None = None) -> int:
    names = (argv if argv is not None else sys.argv[1:]) or NAMES
    failed = False
    for name in names:
        problems = check(name)
        _, rows = read_tsv(HERE / "first" / f"{name}.tsv")
        per = Counter(r["class"] for r in rows)
        empty = sum(1 for r in rows if not r["described_check"])
        print(f"check_first: {name}: {len(rows)} flags, classes "
              + ", ".join(f"{c} {per.get(c, 0)}" for c in "ABCD")
              + f", {empty} without a described check id; {len(problems)} problems")
        for p in problems:
            print(f"  {p}")
        failed |= bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

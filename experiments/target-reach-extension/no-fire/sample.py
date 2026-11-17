#!/usr/bin/env python3
"""The reachability sample of the checks that fire in no case: 5 per library, 20 in all.

    python3 -I -B sample.py [--generated DIR] [--subjects DIR] [--out FILE] [--expect-total N]

Population. For each of the 4 held-out libraries of the toolkit (google-auth,
oauthlib, authlib, joserfc), the rows of `<generated>/<name>/checks.csv` with
`reachable` = `yes` and `cases_fired` = `0` (default `<generated>` is
`../../target-reach/generated`). The script prints the size of each
population and stops, before drawing, when their sum is not `--expect-total`
(default 103).

Draw. For each library, in the order above, a fresh `random.Random(20261117)`
draws 5 check ids with `.sample(population, 5)`, where `population` is the
list of the library's check ids sorted as Python sorts strings. The draw reads
nothing but `checks.csv`; a fresh generator per library makes the draw of a
library independent of the other libraries and of their order.

Output. `--out` (default `sample.csv` next to this file), 1 row per drawn
check, the libraries in the order above and the checks of a library in the
order of the draw, with the columns

    library, check, file, line, function, class, template, reachable

`file`, `function`, `class`, `template` and `reachable` are the values of
`checks.csv`. `line` is the first line of each raise statement of the check,
joined by `;`, from `lines` of `<subjects>/<name>/checks.json` (the definitions
written by the toolkit's `define`; default `<subjects>` is
`../../target-reach/subjects`); it is read after the draw and does not take
part in it. The script stops when a drawn check is missing from `checks.json`
or when its file or function there differ from `checks.csv`.

The script prints the SHA-256 of every file it reads, the population sizes,
the Python version and the drawn ids.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLKIT = HERE.parents[1] / "target-reach"
LIBRARIES = ("google-auth", "oauthlib", "authlib", "joserfc")
SEED = 20261117
PER_LIBRARY = 5
EXPECT_TOTAL = 103
COLUMNS = ("library", "check", "file", "line", "function", "class", "template", "reachable")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def population(rows: list[dict]) -> list[dict]:
    """The rows of checks.csv for checks that are statically reachable and fire in no case."""
    return [r for r in rows if r["reachable"] == "yes" and r["cases_fired"] == "0"]


def draw(ids: list[str], seed: int = SEED, k: int = PER_LIBRARY) -> list[str]:
    """k ids drawn by a fresh random.Random(seed) from the sorted ids."""
    return random.Random(seed).sample(sorted(ids), k)


def raise_lines(check: dict) -> str:
    """The first line of each raise statement of a check of checks.json."""
    return ";".join(str(start) for start, _end in check["lines"])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--generated", default=str(TOOLKIT / "generated"))
    parser.add_argument("--subjects", default=str(TOOLKIT / "subjects"))
    parser.add_argument("--out", default=str(HERE / "sample.csv"))
    parser.add_argument("--libraries", nargs="+", default=list(LIBRARIES))
    parser.add_argument("--expect-total", type=int, default=EXPECT_TOTAL)
    args = parser.parse_args(argv)
    generated, subjects = Path(args.generated), Path(args.subjects)

    print(f"python {platform.python_implementation()} {platform.python_version()}; seed {SEED}; "
          f"{PER_LIBRARY} per library")
    pops: dict[str, list[dict]] = {}
    for name in args.libraries:
        path = generated / name / "checks.csv"
        rows = read_rows(path)
        pops[name] = population(rows)
        print(f"{name}: {path} sha256 {sha256(path)}; {len(rows)} rows, "
              f"{len(pops[name])} with reachable yes and cases_fired 0")
    total = sum(len(p) for p in pops.values())
    print(f"total: {total}")
    if total != args.expect_total:
        raise SystemExit(f"the population holds {total} checks, not {args.expect_total}: no draw")

    out_rows = []
    for name in args.libraries:
        by_id = {r["check"]: r for r in pops[name]}
        if len(by_id) != len(pops[name]):
            raise SystemExit(f"{name}: a check id occurs twice in checks.csv")
        drawn = draw(list(by_id))
        print(f"{name}: drawn {drawn}")
        defs_path = subjects / name / "checks.json"
        print(f"{name}: {defs_path} sha256 {sha256(defs_path)}")
        defs = {c["id"]: c for c in json.loads(defs_path.read_text(encoding="utf-8"))["checks"]}
        for cid in drawn:
            row, check = by_id[cid], defs.get(cid)
            if check is None:
                raise SystemExit(f"{name}: {cid} is not in {defs_path}")
            if check["file"] != row["file"] or check["function"] != row["function"]:
                raise SystemExit(f"{name}: {cid}: file or function differ between checks.csv and checks.json")
            out_rows.append({"library": name, "check": cid, "file": row["file"], "line": raise_lines(check),
                             "function": row["function"], "class": row["class"], "template": row["template"],
                             "reachable": row["reachable"]})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"wrote {out}: {len(out_rows)} rows, sha256 {sha256(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

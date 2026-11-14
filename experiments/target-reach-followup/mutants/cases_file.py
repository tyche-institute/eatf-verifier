"""The shadowed cases of a subject, the files to mutate and the cases file.

    python3 -I -B mutants/cases_file.py --subject NAME_OR_SUBJECT_JSON
        [--outcomes CSV] [--first TSV] [--variants TSV] [--deposited DIR] [--out DIR]

Inputs:

- outcomes.csv of labels/analyse_labels.py (default
  generated/labels/<name>/outcomes.csv): the cases with an agreed label that
  names a check, and their outcome;
- the transcription of the first reading of the flags (default
  labels/first/<name>.tsv; not needed);
- cases.csv, pinning.csv and SHA256SUMS of the toolkit's deposited outputs of
  the subject, and its checks.json;
- a variants file (default repaired/<name>/variants.tsv; not needed):
  tab-separated, header case, described, variant; a variant is the end of the
  id of 1 extra test.

A case is shadowed

- by the labels, when its outcome is "label does not fire and decides once
  the deciding check is deleted"; the described check is the agreed label;
- by the first reading, when that reading puts its flag in class A; the
  described check is the target of the rule. The program then requires from
  the deposit what the outcome requires from a label: the target is not the
  deciding check of the case and is not among its fired checks, and on the
  copy without the deciding check the case is observed and the target decides
  it. A class-A row that does not meet this stops the program.

A case that both sources show with the same described check gives 1 row; with
2 different described checks it gives 2 rows.

The files to mutate are the files of the described and of the deciding check
of every shadowed row. The comparison cases are the cases of cases.csv with a
target that is their deciding check, whose target lies in a file to mutate,
and that are not shadowed.

Outputs, in --out (default generated/mutants/<name>/):

- shadowed.csv: 1 row per shadowed row: case, block, index, test_node,
  described, described_file, deciding, deciding_file, source, variant;
- mutated-files.txt: the files to mutate, 1 per line, sorted (the --files of
  materialize.py);
- cases.tsv: the cases file of at_check.py (case, described, kind, variant),
  shadowed rows first (kind "shadowed (<source>)"), then the comparison cases
  (kind "comparison") in the order of cases.csv;
- SHA256SUMS, written again for every file of the folder.

Without a shadowed row the files are still written (the first 3 hold no
row), and the last line printed says so.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import EXPERIMENT, TOOLKIT, load_json, subject_paths  # noqa: E402

SHADOWED = "label does not fire and decides once the deciding check is deleted"
LABELS, FIRST = "labels", "first reading"
OUTCOME_COLUMNS = {"block", "index", "test_node", "label", "deciding", "outcome"}
FIRST_COLUMNS = {"block", "index", "class", "target", "deciding_check", "described_check"}
VARIANT_COLUMNS = ["case", "described", "variant"]


def read_table(path: Path, dialect: str) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, dialect=dialect)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def key_of(test_node: str, block: str, index: str) -> str:
    """The key of a case, as reach.study.case_key gives it."""
    return f"{test_node}|{block}|{index}"


def check_deposit(deposited: Path, names: list[str]) -> None:
    """The deposited files read here have the digests of SHA256SUMS."""
    sums = {}
    for line in (deposited / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        sums[name.strip()] = digest.strip()
    for n in names:
        got = hashlib.sha256((deposited / n).read_bytes()).hexdigest()
        if sums.get(n) != got:
            raise SystemExit(f"{deposited / n} does not have the digest of SHA256SUMS")


def shadowed_rows(cases: list[dict], pinning: list[dict], outcomes: list[dict], first: list[dict],
                  check_file: dict[str, str]) -> list[dict]:
    """The shadowed rows, in the order of cases.csv and then by described check."""
    by_case = {(r["block"], r["index"]): r for r in cases}
    pin = {(r["block"], r["index"]): r for r in pinning}
    found: dict[tuple[str, str, str], dict] = {}

    def add(block: str, index: str, described: str, deciding: str, source: str) -> None:
        c = by_case.get((block, index))
        if c is None:
            raise SystemExit(f"{source}: no case {block} {index} in cases.csv")
        if c["baseline_site"] != deciding:
            raise SystemExit(f"{source}: the deciding check of {block} {index} is {c['baseline_site']} in "
                             f"cases.csv, not {deciding}")
        for x in (described, deciding):
            if x not in check_file:
                raise SystemExit(f"{source}: {x} is no check of checks.json")
        k = (block, index, described)
        if k in found:
            found[k]["sources"].append(source)
            return
        found[k] = {"case": key_of(c["test_node"], block, index), "block": block, "index": index,
                    "test_node": c["test_node"], "described": described,
                    "described_file": check_file[described], "deciding": deciding,
                    "deciding_file": check_file[deciding], "sources": [source]}

    for r in outcomes:
        if r["outcome"] == SHADOWED:
            add(r["block"], r["index"], r["label"], r["deciding"], LABELS)
    for r in first:
        if r["class"] != "A":
            continue
        block, index, target, deciding = r["block"], r["index"], r["target"], r["deciding_check"]
        c, p = by_case.get((block, index)), pin.get((block, index))
        problems = []
        if c is None or p is None:
            problems.append("no row in cases.csv or pinning.csv")
        else:
            if r["described_check"] != target or c["target"] != target:
                problems.append("the described check is not the target of cases.csv")
            if target == deciding or c["baseline_site"] != deciding:
                problems.append("the deciding check is the target, or is not that of cases.csv")
            if target in [x for x in c["fired"].split("; ") if x] or c["target_fired"] == "yes":
                problems.append("the target fires in the baseline")
            if p["deleted_check"] != deciding or p["status"] != "observed" or p["site"] != target:
                problems.append("on the copy without the deciding check the target does not decide the case")
        if problems:
            raise SystemExit(f"{FIRST}: class-A row {block} {index}: " + "; ".join(problems))
        add(block, index, target, deciding, FIRST)

    order = {(r["block"], r["index"]): n for n, r in enumerate(cases)}
    return sorted(found.values(), key=lambda e: (order[(e["block"], e["index"])], e["described"]))


def comparison_rows(cases: list[dict], files: set[str], check_file: dict[str, str],
                    shadowed: set[str]) -> list[dict]:
    """The cases with a target that decides them, in the files to mutate."""
    rows = []
    for c in cases:
        k = key_of(c["test_node"], c["block"], c["index"])
        if c["target"] and c["baseline_site"] == c["target"] and check_file[c["target"]] in files \
                and k not in shadowed:
            rows.append({"case": k, "described": c["target"]})
    return rows


def text(header: list[str], rows: list[list[str]], dialect: str) -> str:
    out = io.StringIO()
    w = csv.writer(out, dialect=dialect, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return out.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--subject", required=True)
    parser.add_argument("--outcomes")
    parser.add_argument("--first")
    parser.add_argument("--variants")
    parser.add_argument("--deposited")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    subject_path, subject = subject_paths(args.subject)
    name = subject["name"]
    deposited = Path(args.deposited) if args.deposited else TOOLKIT / "generated" / name
    out = Path(args.out) if args.out else EXPERIMENT / "generated" / "mutants" / name
    outcomes_path = Path(args.outcomes) if args.outcomes else EXPERIMENT / "generated" / "labels" / name / "outcomes.csv"
    first_path = Path(args.first) if args.first else EXPERIMENT / "labels" / "first" / f"{name}.tsv"
    variants_path = Path(args.variants) if args.variants else EXPERIMENT / "repaired" / name / "variants.tsv"

    check_deposit(deposited, ["cases.csv", "pinning.csv"])
    cases = read_table(deposited / "cases.csv", "excel")[1]
    pinning = read_table(deposited / "pinning.csv", "excel")[1]
    check_file = {c["id"]: c["file"] for c in load_json(subject_path.parent / "checks.json")["checks"]}

    header, outcomes = read_table(outcomes_path, "excel")
    if not OUTCOME_COLUMNS <= set(header):
        raise SystemExit(f"{outcomes_path}: the columns {sorted(OUTCOME_COLUMNS)} are needed")
    first: list[dict] = []
    if first_path.is_file():
        header, first = read_table(first_path, "excel-tab")
        if not FIRST_COLUMNS <= set(header):
            raise SystemExit(f"{first_path}: the columns {sorted(FIRST_COLUMNS)} are needed")
    elif args.first:
        raise SystemExit(f"{first_path}: no such file")
    variants: dict[tuple[str, str], str] = {}
    if variants_path.is_file():
        header, rows = read_table(variants_path, "excel-tab")
        if header != VARIANT_COLUMNS:
            raise SystemExit(f"{variants_path}: the header {VARIANT_COLUMNS} is needed")
        for r in rows:
            if (r["case"], r["described"]) in variants or not r["variant"]:
                raise SystemExit(f"{variants_path}: {r['case']} with {r['described']} 2 times, or no variant")
            variants[(r["case"], r["described"])] = r["variant"]
    elif args.variants:
        raise SystemExit(f"{variants_path}: no such file")

    shadowed = shadowed_rows(cases, pinning, outcomes, first, check_file)
    unused = set(variants) - {(e["case"], e["described"]) for e in shadowed}
    if unused:
        raise SystemExit(f"{variants_path}: no shadowed row for {sorted(unused)}")
    for e in shadowed:
        e["source"] = " and ".join(s for s in (LABELS, FIRST) if s in e["sources"])
        e["variant"] = variants.get((e["case"], e["described"]), "")
    files = sorted({e["described_file"] for e in shadowed} | {e["deciding_file"] for e in shadowed})
    comparison = comparison_rows(cases, set(files), check_file, {e["case"] for e in shadowed})

    out.mkdir(parents=True, exist_ok=True)
    columns = ["case", "block", "index", "test_node", "described", "described_file", "deciding",
               "deciding_file", "source", "variant"]
    (out / "shadowed.csv").write_text(text(columns, [[e[c] for c in columns] for e in shadowed], "excel"),
                                      encoding="utf-8")
    (out / "mutated-files.txt").write_text("".join(f + "\n" for f in files), encoding="utf-8")
    rows = [[e["case"], e["described"], f"shadowed ({e['source']})", e["variant"]] for e in shadowed]
    rows += [[r["case"], r["described"], "comparison", ""] for r in comparison]
    (out / "cases.tsv").write_text(text(["case", "described", "kind", "variant"], rows, "excel-tab"),
                                   encoding="utf-8")
    sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
            for p in sorted(out.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    by_source = {s: sum(1 for e in shadowed if s in e["sources"]) for s in (LABELS, FIRST)}
    print(f"cases_file: {name}: {len(shadowed)} shadowed rows in {len({e['case'] for e in shadowed})} cases "
          f"(by the labels {by_source[LABELS]}, by the first reading {by_source[FIRST]}), "
          f"{sum(1 for e in shadowed if e['variant'])} with a variant; {len(files)} files to mutate; "
          f"{len(comparison)} comparison cases" + ("" if shadowed else "; no shadowed case: nothing to mutate"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

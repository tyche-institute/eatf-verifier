"""Tests of cases_file.py on synthetic tables."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import cases_file  # noqa: E402
from cases_file import FIRST, LABELS, SHADOWED, comparison_rows, key_of, shadowed_rows  # noqa: E402

CHECK_FILE = {"m.f#1": "pkg/m.py", "m.f#2": "pkg/m.py", "n.g#1": "pkg/n.py", "o.h#1": "pkg/o.py",
              "o.h#2": "pkg/o.py"}


def case(block, target, site, fired="", target_fired="no"):
    return {"block": block, "index": "0", "test_node": "::".join(block.split("#")[0].rsplit(".", 1)),
            "baseline_site": site, "target": target, "fired": fired, "target_fired": target_fired}


def pin(block, deleted, site, status="observed"):
    return {"block": block, "index": "0", "deleted_check": deleted, "status": status, "site": site}


CASES = [
    case("t.py::T.a#0", "m.f#2", "m.f#1", fired="m.f#1"),            # class A: the target decides without m.f#1
    case("t.py::T.b#0", "n.g#1", "n.g#1", fired="n.g#1", target_fired="yes"),   # decided by its target, pkg/n.py
    case("t.py::T.c#0", "m.f#1", "m.f#1", fired="m.f#1", target_fired="yes"),   # decided by its target, pkg/m.py
    case("t.py::T.d#0", "", "o.h#1", fired="o.h#1"),                 # no target; shadowed by the labels
    case("t.py::T.e#0", "o.h#2", "o.h#2", fired="o.h#2", target_fired="yes"),   # decided by its target, pkg/o.py
]
PINNING = [pin("t.py::T.a#0", "m.f#1", "m.f#2"), pin("t.py::T.b#0", "n.g#1", ""),
           pin("t.py::T.c#0", "m.f#1", ""), pin("t.py::T.d#0", "o.h#1", "o.h#2"),
           pin("t.py::T.e#0", "o.h#2", "")]


def outcome(block, label, deciding, text=SHADOWED):
    return {"block": block, "index": "0", "test_node": "", "label": label, "deciding": deciding, "outcome": text}


def first(block, cls, target, deciding, described=None):
    return {"block": block, "index": "0", "class": cls, "target": target, "deciding_check": deciding,
            "described_check": target if described is None else described}


def test_shadowed_rows_and_comparison():
    outcomes = [outcome("t.py::T.d#0", "o.h#2", "o.h#1"),
                outcome("t.py::T.b#0", "n.g#1", "n.g#1", "decided by its label")]
    firsts = [first("t.py::T.a#0", "A", "m.f#2", "m.f#1"), first("t.py::T.e#0", "C", "o.h#2", "o.h#1")]
    rows = shadowed_rows(CASES, PINNING, outcomes, firsts, CHECK_FILE)
    assert [(e["block"], e["described"], e["deciding"], e["sources"]) for e in rows] == [
        ("t.py::T.a#0", "m.f#2", "m.f#1", [FIRST]), ("t.py::T.d#0", "o.h#2", "o.h#1", [LABELS])]
    assert rows[0]["case"] == "t.py::T::a|t.py::T.a#0|0" == key_of("t.py::T::a", "t.py::T.a#0", "0")
    assert rows[0]["described_file"] == "pkg/m.py" and rows[1]["deciding_file"] == "pkg/o.py"
    files = {e["described_file"] for e in rows} | {e["deciding_file"] for e in rows}
    comparison = comparison_rows(CASES, files, CHECK_FILE, {e["case"] for e in rows})
    # T.b is decided by its target in a file that is not mutated; T.a and T.d are shadowed
    assert [(r["case"].split("|")[1], r["described"]) for r in comparison] == [
        ("t.py::T.c#0", "m.f#1"), ("t.py::T.e#0", "o.h#2")]


def test_both_sources():
    # the labels and the first reading name the same described check: 1 row with both sources
    rows = shadowed_rows(CASES, PINNING, [outcome("t.py::T.a#0", "m.f#2", "m.f#1")],
                         [first("t.py::T.a#0", "A", "m.f#2", "m.f#1")], CHECK_FILE)
    assert len(rows) == 1 and rows[0]["sources"] == [LABELS, FIRST]
    # another described check by the labels: 2 rows of 1 case
    cases = CASES + [case("t.py::T.f#0", "m.f#2", "m.f#1", fired="m.f#1")]
    pinning = PINNING + [pin("t.py::T.f#0", "m.f#1", "m.f#2")]
    rows = shadowed_rows(cases, pinning, [outcome("t.py::T.f#0", "n.g#1", "m.f#1")],
                         [first("t.py::T.f#0", "A", "m.f#2", "m.f#1")], CHECK_FILE)
    assert [(e["described"], e["sources"]) for e in rows] == [("m.f#2", [FIRST]), ("n.g#1", [LABELS])]


@pytest.mark.parametrize("change, text", [
    ({"pin": pin("t.py::T.a#0", "m.f#1", "n.g#1")}, "does not decide"),          # another check decides then
    ({"pin": pin("t.py::T.a#0", "m.f#1", "m.f#2", status="crashed")}, "does not decide"),
    ({"case": case("t.py::T.a#0", "m.f#2", "m.f#1", fired="m.f#1; m.f#2")}, "fires"),
    ({"case": case("t.py::T.a#0", "m.f#2", "m.f#2", fired="m.f#2", target_fired="yes")}, "deciding check"),
    ({"first": first("t.py::T.a#0", "A", "m.f#2", "m.f#1", described="n.g#1")}, "not the target"),
])
def test_class_a_row_must_meet_the_condition(change, text):
    cases = [change.get("case", CASES[0])] + CASES[1:]
    pinning = [change.get("pin", PINNING[0])] + PINNING[1:]
    row = change.get("first", first("t.py::T.a#0", "A", "m.f#2", "m.f#1"))
    with pytest.raises(SystemExit) as e:
        shadowed_rows(cases, pinning, [], [row], CHECK_FILE)
    assert text in str(e.value)


def test_label_row_must_match_the_deposit():
    with pytest.raises(SystemExit) as e:
        shadowed_rows(CASES, PINNING, [outcome("t.py::T.d#0", "o.h#2", "m.f#1")], [], CHECK_FILE)
    assert "deciding check" in str(e.value)
    with pytest.raises(SystemExit) as e:
        shadowed_rows(CASES, PINNING, [outcome("t.py::T.d#0", "x.y#9", "o.h#1")], [], CHECK_FILE)
    assert "no check" in str(e.value)


def write(path: Path, header: list[str], rows: list[dict], dialect: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, header, dialect=dialect, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def test_main(tmp_path, capsys):
    subject_dir, deposited, out = tmp_path / "subjects" / "toy", tmp_path / "generated", tmp_path / "out"
    for d in (subject_dir, deposited):
        d.mkdir(parents=True)
    (subject_dir / "subject.json").write_text(json.dumps({"name": "toy"}), encoding="utf-8")
    (subject_dir / "checks.json").write_text(json.dumps(
        {"checks": [{"id": k, "file": v} for k, v in CHECK_FILE.items()]}), encoding="utf-8")
    write(deposited / "cases.csv", list(CASES[0]), CASES, "excel")
    write(deposited / "pinning.csv", list(PINNING[0]), PINNING, "excel")
    (deposited / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256((deposited / n).read_bytes()).hexdigest()}  {n}\n" for n in ("cases.csv", "pinning.csv")),
        encoding="utf-8")
    outcomes = [outcome("t.py::T.d#0", "o.h#2", "o.h#1")]
    write(tmp_path / "outcomes.csv", list(outcomes[0]), outcomes, "excel")
    firsts = [first("t.py::T.a#0", "A", "m.f#2", "m.f#1")]
    write(tmp_path / "first.tsv", list(firsts[0]), firsts, "excel-tab")
    key_a = key_of(CASES[0]["test_node"], "t.py::T.a#0", "0")
    write(tmp_path / "variants.tsv", ["case", "described", "variant"],
          [{"case": key_a, "described": "m.f#2", "variant": "test_x.T::test_a_repaired"}], "excel-tab")
    argv = ["--subject", str(subject_dir / "subject.json"), "--outcomes", str(tmp_path / "outcomes.csv"),
            "--first", str(tmp_path / "first.tsv"), "--variants", str(tmp_path / "variants.tsv"),
            "--deposited", str(deposited), "--out", str(out)]
    assert cases_file.main(argv) == 0
    assert "2 shadowed rows in 2 cases (by the labels 1, by the first reading 1), 1 with a variant; 2 files" \
        in capsys.readouterr().out
    assert (out / "mutated-files.txt").read_text() == "pkg/m.py\npkg/o.py\n"
    sums = dict(line.split("  ")[::-1] for line in (out / "SHA256SUMS").read_text().splitlines())
    assert sorted(sums) == ["cases.tsv", "mutated-files.txt", "shadowed.csv"]
    assert all(hashlib.sha256((out / n).read_bytes()).hexdigest() == d for n, d in sums.items())
    rows = list(csv.DictReader(open(out / "cases.tsv", newline=""), dialect="excel-tab"))
    assert [(r["described"], r["kind"], r["variant"]) for r in rows] == [
        ("m.f#2", "shadowed (first reading)", "test_x.T::test_a_repaired"), ("o.h#2", "shadowed (labels)", ""),
        ("m.f#1", "comparison", ""), ("o.h#2", "comparison", "")]
    shadowed = list(csv.DictReader(open(out / "shadowed.csv", newline="")))
    assert [r["source"] for r in shadowed] == ["first reading", "labels"]
    first_text = (out / "cases.tsv").read_bytes()
    assert cases_file.main(argv) == 0 and (out / "cases.tsv").read_bytes() == first_text
    # a deposited file that changed stops the program
    (deposited / "pinning.csv").write_text((deposited / "pinning.csv").read_text() + "\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        cases_file.main(argv)

"""Unit tests of ../no-fire/sample.py on synthetic checks.csv and checks.json files."""
from __future__ import annotations

import csv
import json
import random

import pytest

from conftest import T, X, load

sample = load("x_sample", "no-fire/sample.py")

CSV_COLUMNS = ["check", "file", "function", "class", "template", "reachable", "cases_fired"]


def write_library(root, name: str, n_unfired: int) -> list[str]:
    """generated/<name>/checks.csv and subjects/<name>/checks.json with n_unfired reachable
    checks that fire in no case, 2 reachable checks that fire and 2 unreachable ones."""
    rows, checks, ids = [], [], []
    for i in range(n_unfired + 4):
        cid = f"m.f{i:02d}#1"
        reachable = "no" if i >= n_unfired + 2 else "yes"
        fired = "3" if n_unfired <= i < n_unfired + 2 else "0"
        rows.append({"check": cid, "file": "pkg/m.py", "function": f"f{i:02d}", "class": "ValueError",
                     "template": "bad {*}", "reachable": reachable, "cases_fired": fired})
        checks.append({"id": cid, "file": "pkg/m.py", "function": f"f{i:02d}", "lines": [[10 + i, 10 + i], [50 + i, 51 + i]]})
        if reachable == "yes" and fired == "0":
            ids.append(cid)
    (root / "generated" / name).mkdir(parents=True)
    with (root / "generated" / name / "checks.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    (root / "subjects" / name).mkdir(parents=True)
    (root / "subjects" / name / "checks.json").write_text(json.dumps({"checks": checks}), encoding="utf-8")
    return ids


def args(root, *extra):
    return ["--generated", str(root / "generated"), "--subjects", str(root / "subjects"),
            "--out", str(root / "sample.csv"), *extra]


def test_population_is_reachable_and_unfired():
    rows = [{"reachable": "yes", "cases_fired": "0", "check": "a"}, {"reachable": "yes", "cases_fired": "2", "check": "b"},
            {"reachable": "no", "cases_fired": "0", "check": "c"}, {"reachable": "yes", "cases_fired": "0", "check": "d"}]
    assert [r["check"] for r in sample.population(rows)] == ["a", "d"]


def test_draw_ignores_the_order_of_the_input():
    ids = [f"c{i}" for i in range(30)]
    drawn = sample.draw(ids)
    assert drawn == sample.draw(list(reversed(ids))) == random.Random(20261117).sample(sorted(ids), 5)
    assert len(set(drawn)) == 5 and set(drawn) <= set(ids)


def test_main_writes_5_rows_per_library(tmp_path, capsys):
    ids_a = write_library(tmp_path, "a", 7)
    ids_b = write_library(tmp_path, "b", 6)
    assert sample.main(args(tmp_path, "--libraries", "a", "b", "--expect-total", "13")) == 0
    with (tmp_path / "sample.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == list(sample.COLUMNS)
    assert [r["library"] for r in rows] == ["a"] * 5 + ["b"] * 5
    assert [r["check"] for r in rows[:5]] == sample.draw(ids_a)
    assert [r["check"] for r in rows[5:]] == sample.draw(ids_b)
    first = rows[0]
    i = int(first["check"][3:5])
    assert first["line"] == f"{10 + i};{50 + i}" and first["reachable"] == "yes"
    assert "total: 13" in capsys.readouterr().out


def test_draw_of_a_library_does_not_depend_on_the_others(tmp_path):
    write_library(tmp_path, "a", 7)
    write_library(tmp_path, "b", 6)
    sample.main(args(tmp_path, "--libraries", "a", "b", "--expect-total", "13"))
    both = (tmp_path / "sample.csv").read_text(encoding="utf-8").splitlines()
    sample.main(args(tmp_path, "--libraries", "b", "a", "--expect-total", "13"))
    swapped = (tmp_path / "sample.csv").read_text(encoding="utf-8").splitlines()
    assert sorted(both[1:]) == sorted(swapped[1:])


def test_main_stops_before_the_draw_on_another_total(tmp_path):
    write_library(tmp_path, "a", 7)
    with pytest.raises(SystemExit, match="holds 7 checks, not 8"):
        sample.main(args(tmp_path, "--libraries", "a", "--expect-total", "8"))
    assert not (tmp_path / "sample.csv").exists()


def test_main_stops_when_checks_json_lacks_a_drawn_check(tmp_path):
    write_library(tmp_path, "a", 5)
    path = tmp_path / "subjects" / "a" / "checks.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["checks"] = doc["checks"][1:]
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(SystemExit, match="is not in"):
        sample.main(args(tmp_path, "--libraries", "a", "--expect-total", "5"))


def test_the_deposited_sample_is_reproduced(tmp_path):
    """sample.csv of ../no-fire is what the script gives on the toolkit's deposited files."""
    out = tmp_path / "again.csv"
    assert sample.main(["--out", str(out)]) == 0
    assert out.read_bytes() == (X / "no-fire" / "sample.csv").read_bytes()
    assert (T / "generated").is_dir()

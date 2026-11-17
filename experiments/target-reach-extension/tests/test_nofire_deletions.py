"""Unit and end-to-end tests of ../no-fire/nofire_deletions.py on the toolkit's toy package."""
from __future__ import annotations

import csv
import json
import subprocess
import sys

import pytest

from conftest import T, TOY, load

nofire = load("x_nofire_deletions", "no-fire/nofire_deletions.py")
rm = nofire.load_toolkit(T)

# In the toy, deleting _check_version#1 leaves every test passing, deleting
# _check_signature#1 does not (the toolkit's own end-to-end test, tests/test_reach.py).
UNFIRED = ("core._check_version#1", "core._check_signature#1")


def write_generated(root, rows) -> None:
    (root / "toy").mkdir(parents=True)
    with (root / "toy" / "checks.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "file", "reachable", "cases_fired"])
        writer.writeheader()
        writer.writerows(rows)


def unfired_rows(extra=()):
    rows = [{"check": c, "file": "toyverify/core.py", "reachable": "yes", "cases_fired": "0"} for c in UNFIRED]
    rows += [{"check": "core._parse#1", "file": "toyverify/core.py", "reachable": "yes", "cases_fired": "4"},
             {"check": "core.encode#1", "file": "toyverify/core.py", "reachable": "no", "cases_fired": "0"}]
    return rows + list(extra)


def test_population_and_total(tmp_path, toy_subjects, capsys):
    write_generated(tmp_path, unfired_rows())
    found = nofire.population(tmp_path, toy_subjects, ["toy"], 2)
    assert [c["id"] for c in found["toy"]] == sorted(UNFIRED)
    assert "toy: 2 of the 4 rows" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="number 2, not 3"):
        nofire.population(tmp_path, toy_subjects, ["toy"], 3)


def test_population_refuses_a_check_that_is_not_reachable(tmp_path, toy_subjects):
    rows = unfired_rows([{"check": "core.encode#1", "file": "toyverify/core.py", "reachable": "yes",
                          "cases_fired": "0"}])
    write_generated(tmp_path, rows)
    with pytest.raises(SystemExit, match="no reachable subject check"):
        nofire.population(tmp_path, toy_subjects, ["toy"], 3)


class FakeRun:
    """Stands for subprocess.run: notes each call and runs nothing."""

    def __init__(self, returncode=0):
        self.calls, self.returncode = [], returncode

    def __call__(self, cmd, *args, **kwargs):
        self.calls.append({"cmd": cmd, "cwd": str(kwargs.get("cwd")), "env": kwargs.get("env")})
        return subprocess.CompletedProcess(cmd, self.returncode, "", "")


def test_dry_commands_are_those_of_whole_run(tmp_path, toy_subjects, monkeypatch):
    ctx = nofire.make_context(rm, "toy", toy_subjects, tmp_path / "work", str(TOY), sys.executable, 1)
    cwd = tmp_path / "copy"
    fake = FakeRun()
    proxy = type("P", (), {"run": staticmethod(fake), "TimeoutExpired": subprocess.TimeoutExpired})()
    monkeypatch.setattr(rm, "subprocess", proxy)
    result = rm.whole_run(ctx, "x", cwd, 60)
    assert result["no_result"] == ["all"]                    # the fake wrote no result file
    expected = nofire.whole_commands(rm, ctx, "x", cwd)
    assert [{"cmd": c["cmd"], "cwd": c["cwd"], "env": c["env"]} for c in expected] == fake.calls


def test_observer_notes_the_exit_status(tmp_path, toy_subjects, monkeypatch):
    ctx = nofire.make_context(rm, "toy", toy_subjects, tmp_path / "work", str(TOY), sys.executable, 1)
    fake = FakeRun(returncode=1)
    monkeypatch.setattr(nofire.subprocess, "run", fake)
    observer = nofire.Observer(rm)
    observer.install()
    try:
        rm.whole_run(ctx, "x", tmp_path / "copy", 60)
        rm.whole_run(ctx, "x", tmp_path / "copy", 60)
    finally:
        observer.uninstall()
    assert rm.subprocess is subprocess and rm.whole_run is observer.real_whole_run
    assert observer.attempts == {"x": [{"all": 1}, {"all": 1}]}
    assert (ctx.work / "logs" / "whole" / "x.all.attempt-2.log").exists()


def test_dry_mode_lists_checks_and_commands(tmp_path, toy_subjects, capsys):
    generated = tmp_path / "generated"
    write_generated(generated, unfired_rows())
    code = nofire.main(["--dry", "--libraries", "toy", "--expect-total", "2", "--clone", f"toy={TOY}",
                        "--python", f"toy={sys.executable}", "--work", str(tmp_path / "work"),
                        "--subjects", str(toy_subjects), "--generated", str(generated)])
    assert code == 0
    out = capsys.readouterr().out
    calls = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    assert [c["copy"] for c in calls] == ["whole-baseline, unmodified"] * 2 + [
        "whole-deletions, unmodified control"] + [f"whole-deletions, {c}" for c in sorted(UNFIRED)]
    assert "check core._check_signature#1: toyverify/core.py line(s) 34-36" in out
    assert not (tmp_path / "work" / "toy" / "copies").exists()


def test_end_to_end_on_the_toy(tmp_path, toy_subjects):
    generated = tmp_path / "generated"
    write_generated(generated, unfired_rows())
    out, summary_path, records = tmp_path / "deletions.csv", tmp_path / "summary.json", tmp_path / "records"
    # an earlier call that ran another library: its row and summary are kept
    nofire.write_csv(out, [{"library": "other", "check": "_control", "detected": "no"}])
    summary_path.write_text(json.dumps({"libraries": {"other": {"checks": 0}, "toy": {"stale": True}}}),
                            encoding="utf-8")
    code = nofire.main(["--libraries", "toy", "--expect-total", "2", "--clone", f"toy={TOY}",
                        "--python", f"toy={sys.executable}", "--work", str(tmp_path / "work"), "--workers", "2",
                        "--out", str(out), "--summary", str(summary_path), "--records", str(records),
                        "--subjects", str(toy_subjects), "--generated", str(generated)])
    assert code == 0
    with out.open(newline="", encoding="utf-8") as handle:
        every = list(csv.DictReader(handle))
    assert [r["library"] for r in every] == ["toy"] * 3 + ["other"]
    rows = {r["check"]: r for r in every if r["library"] == "toy"}
    assert list(rows) == ["_control", "core._check_signature#1", "core._check_version#1"]
    work_records = tmp_path / "work" / "toy" / "records" / "whole"
    for name in ("base.json", "deletions.json"):
        assert (records / "toy" / "whole" / name).read_bytes() == (work_records / name).read_bytes()
    assert rows["_control"]["detected"] == "no" and rows["_control"]["returncode"] == "all=0"
    assert rows["core._check_version#1"]["detected"] == "no"
    assert rows["core._check_version#1"]["returncode"] == "all=0"
    sig = rows["core._check_signature#1"]
    assert sig["detected"] == "yes" and sig["returncode"] == "all=1" and sig["detected_by_failure"] == "yes"
    assert int(sig["tests_not_passing"]) == int(sig["failed_or_error"]) + int(sig["skipped"]) + int(sig["absent"])
    assert all(r["runs"] == "1" and r["timed_out"] == "no" and r["refused_attempts"] == "0" for r in rows.values())
    libraries = json.loads(summary_path.read_text(encoding="utf-8"))["libraries"]
    assert set(libraries) == {"toy", "other"} and libraries["other"] == {"checks": 0}
    summary = libraries["toy"]
    assert summary["not_detected"] == ["core._check_version#1"] and summary["deposited_whole_baseline"] is None

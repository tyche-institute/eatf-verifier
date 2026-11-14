"""Tests of the 4 comparison scripts of recompute/.

The scripts compare_labels.py, compare_rule3.py, compare_mutants.py and
compare_totals.py each run as a subprocess from the experiment directory.
No script is imported, so no bytecode folder is written.

Each script is tested in 3 ways:

- On the deposited inputs of the held-out libraries, the exit status is 0.
  The summary line reports 0 differences and the number of compared values
  stated in COMPARED below.
- On a perturbed copy of 1 input, the exit status is 1 and the summary line
  reports at least 1 difference.
- With a missing input file, the exit status is 2.

The perturbed copies are written to the temporary folder of pytest only.
Each perturbation changes 1 value of the second output:

- 1 number;
- 1 identifier in a set;
- 1 expectation status, where the second output holds one.

Further perturbations test single fields:

- compare_mutants.py: 1 more for each of the 5 totals of the second output
  (counts.tool_mutants, counts.deletions, and 1 key of each of the tables
  counts.tool_mutants_by_operator, counts.tool_mutants_by_file and
  counts.deletions_by_file), each giving exit status 1.
- compare_rule3.py: 1 changed number in the rule output given with
  --second-targets.
- compare_rule3.py, joserfc: in the field variant of that rule output,
  checks_reachable_under_rule3 plus 1, a changed rule_code and a changed
  reach_json_sha256 each give exit status 1.
  A changed text variant.reachable gives exit status 0, since that text is not
  compared and a printed "not compared" line names it.
- compare_labels.py, joserfc: a category of the first per-flag entry of the
  first reading with "X" appended is a name that FIRST_MAP lacks.
  It gives exit status 1, not 2.
An input file of a library that is absent makes the test fail; no test is
skipped.

Run from the experiment directory:

    PYTHONHASHSEED=0 python -I -B -m pytest -q -p no:cacheprovider recompute/tests

The interpreter needs pytest; the scripts themselves use the standard library
only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

EXPERIMENT = Path(__file__).resolve().parents[2]
LIBRARIES = ["google-auth", "oauthlib", "authlib", "joserfc"]
SUMMARY_LINE = re.compile(r"^(?:(?P<name>[\w-]+): )?compared (?P<compared>\d+), agree (?P<agree>\d+), "
                          r"differ (?P<differ>\d+)$")

# Number of compared values on the deposited inputs. A change of a comparison
# script that adds or drops a compared value changes these numbers.
COMPARED = {
    "labels": {"google-auth": 339, "oauthlib": 1165, "authlib": 501, "joserfc": 1559},
    "rule3": {"google-auth": 320, "oauthlib": 701, "authlib": 380, "joserfc": 964},
    "mutants": {"joserfc": 15488},
    "totals": 1830,
}


def run(args: list[str]) -> tuple[int, str, str]:
    """Run 1 comparison script from the experiment directory."""
    done = subprocess.run([sys.executable, "-I", "-B", *args], cwd=EXPERIMENT, capture_output=True,
                          text=True, timeout=240, check=False)
    return done.returncode, done.stdout, done.stderr


def summary(stdout: str, name: str | None = None) -> dict:
    """Parse the summary line, which is the first line of the output."""
    lines = stdout.splitlines()
    assert lines, "no output"
    m = SUMMARY_LINE.match(lines[0])
    assert m, f"no summary line: {lines[0]!r}"
    if name is not None:
        assert m["name"] == name
    return {k: int(m[k]) for k in ("compared", "agree", "differ")}


def need(rel: str) -> str:
    """Return a relative input path after asserting that the file exists."""
    assert (EXPERIMENT / rel).is_file(), f"input file absent: {rel}"
    return rel


def get(doc, path: list):
    for key in path:
        doc = doc[key]
    return doc


def perturbed(src: str, dst: Path, path: list, kind: str) -> Path:
    """Write a copy of the JSON file src to dst with 1 value changed.

    kind is "number" (add 1), "identifier" (append ".x" to a member of a set,
    given as a list index or as the first key of an object) or "status" (flip
    "held" and "not held", or true and false).
    """
    doc = json.loads((EXPERIMENT / need(src)).read_text(encoding="utf-8"))
    parent, key = get(doc, path[:-1]), path[-1]
    if kind == "number":
        assert isinstance(parent[key], int) and not isinstance(parent[key], bool)
        parent[key] += 1
    elif kind == "identifier" and isinstance(key, int):
        assert isinstance(parent[key], str)
        parent[key] += ".x"
    elif kind == "identifier":
        first = next(iter(parent[key]))
        parent[key][first + ".x"] = parent[key].pop(first)
    elif kind == "status":
        old = parent[key]
        parent[key] = (not old) if isinstance(old, bool) else {"held": "not held", "not held": "held"}[old]
    else:
        raise AssertionError(kind)
    dst.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return dst


def changed(src: str, dst: Path, path: list, change) -> Path:
    """Write a copy of the JSON file src to dst with 1 value replaced by change(value).

    A path item None stands for the first key of an object, in file order.
    """
    doc = json.loads((EXPERIMENT / need(src)).read_text(encoding="utf-8"))
    parent = doc
    keys = []
    for item in path:
        key = next(iter(parent)) if item is None else item
        keys.append(key)
        if len(keys) < len(path):
            parent = parent[key]
    old = parent[keys[-1]]
    new = change(old)
    assert new != old
    parent[keys[-1]] = new
    dst.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return dst


def plus_1(value):
    assert isinstance(value, int) and not isinstance(value, bool)
    return value + 1


def append_x(value):
    assert isinstance(value, str)
    return value + "X"


def assert_agrees(code: int, out: str, err: str, compared: int, name: str | None = None) -> None:
    assert code == 0, err or out
    s = summary(out, name)
    assert s == {"compared": compared, "agree": compared, "differ": 0}


def assert_differs(code: int, out: str, err: str, name: str | None = None) -> None:
    assert code == 1, err or out
    s = summary(out, name)
    assert s["differ"] >= 1 and s["agree"] == s["compared"] - s["differ"]


# compare_labels.py

def labels_args(name: str, second: str) -> list[str]:
    return ["recompute/compare_labels.py", "--second", second,
            "--first-dir", f"generated/labels/{name}",
            "--subject", need(f"../target-reach/subjects/{name}/subject.json"),
            "--shadowed", need(f"generated/mutants/{name}/shadowed.csv"),
            "--summary", need("generated/labels/summary.json")]


@pytest.mark.parametrize("name", LIBRARIES)
def test_labels_deposited_inputs_agree(name):
    for f in ("counts.json", "agreement.csv", "outcomes.csv", "rule-vs-label.csv", "rule-vs-label-blocks.csv"):
        need(f"generated/labels/{name}/{f}")
    code, out, err = run(labels_args(name, need(f"recompute/out/{name}/second_labels.json")))
    assert_agrees(code, out, err, COMPARED["labels"][name], name)


@pytest.mark.parametrize("kind, path", [
    ("number", ["expectations", "L3", "units"]),
    ("identifier", ["expectations", "L3", "units_ids", 0]),
    ("status", ["expectations", "L3", "status"]),
])
@pytest.mark.parametrize("name", LIBRARIES)
def test_labels_perturbed_copy_differs(name, kind, path, tmp_path):
    copy = perturbed(f"recompute/out/{name}/second_labels.json", tmp_path / "second_labels.json", path, kind)
    assert_differs(*run(labels_args(name, str(copy))), name)


def test_labels_unmapped_category_differs(tmp_path):
    copy = changed("recompute/out/joserfc/second_labels.json", tmp_path / "second_labels.json",
                   ["first_reading", "per_flag", None, "category"], append_x)
    code, out, err = run(labels_args("joserfc", str(copy)))
    assert_differs(code, out, err, "joserfc")
    assert "not in FIRST_MAP" in out


@pytest.mark.parametrize("name", LIBRARIES)
def test_labels_missing_input_exits_2(name, tmp_path):
    code, _, _ = run(labels_args(name, str(tmp_path / "absent.json")))
    assert code == 2


# compare_rule3.py

def rule3_args(name: str, second: str, targets: str, class_a: bool = True) -> list[str]:
    args = ["recompute/compare_rule3.py", "--second", second, "--second-targets", targets,
            "--first", f"generated/trace/{name}"]
    if name == "joserfc" and class_a:
        args += ["--class-a-tsv", need("labels/first/joserfc.tsv")]
    return args


def rule3_deposited(name: str) -> tuple[str, str]:
    return need(f"recompute/out/{name}/second_rule3.json"), need(f"recompute/out/{name}/second_targets3.json")


@pytest.mark.parametrize("name", LIBRARIES)
def test_rule3_deposited_inputs_agree(name):
    need(f"generated/trace/{name}/reach.json")
    need("generated/trace/compare.json")
    code, out, err = run(rule3_args(name, *rule3_deposited(name)))
    assert_agrees(code, out, err, COMPARED["rule3"][name], name)


@pytest.mark.parametrize("which, kind, path", [
    ("second", "number", ["counts", "cases_of_the_study"]),
    ("second", "identifier", ["reachability", "ids", "reachable_under_rule3_candidates", 0]),
    ("second", "status", ["expectations", "T3", "holds"]),
    ("targets", "number", ["counts", "name"]),
])
@pytest.mark.parametrize("name", LIBRARIES)
def test_rule3_perturbed_copy_differs(name, which, kind, path, tmp_path):
    second, targets = rule3_deposited(name)
    if which == "second":
        second = str(perturbed(second, tmp_path / "second_rule3.json", path, kind))
    else:
        targets = str(perturbed(targets, tmp_path / "second_targets3.json", path, kind))
    assert_differs(*run(rule3_args(name, second, targets)), name)


@pytest.mark.parametrize("field, change", [
    ("checks_reachable_under_rule3", plus_1),
    ("rule_code", append_x),
    ("reach_json_sha256", append_x),
])
def test_rule3_joserfc_variant_field_differs(field, change, tmp_path):
    second, targets = rule3_deposited("joserfc")
    copy = changed(targets, tmp_path / "second_targets3.json", ["variant", field], change)
    code, out, err = run(rule3_args("joserfc", second, str(copy)))
    assert_differs(code, out, err, "joserfc")
    assert re.search(rf"^DIFF.*variant {field}", out, re.M), out


def test_rule3_joserfc_variant_reachable_not_compared(tmp_path):
    second, targets = rule3_deposited("joserfc")
    copy = changed(targets, tmp_path / "second_targets3.json", ["variant", "reachable"], append_x)
    code, out, err = run(rule3_args("joserfc", second, str(copy)))
    assert_agrees(code, out, err, COMPARED["rule3"]["joserfc"], "joserfc")
    assert re.search(r"^not compared: variant\.reachable ", out, re.M), out


@pytest.mark.parametrize("name", LIBRARIES)
def test_rule3_missing_input_exits_2(name, tmp_path):
    second, targets = rule3_deposited(name)
    code, _, _ = run(rule3_args(name, str(tmp_path / "absent.json"), targets))
    assert code == 2
    code, _, _ = run(rule3_args(name, second, str(tmp_path / "absent.json")))
    assert code == 2


def test_rule3_joserfc_without_class_a_tsv_exits_2():
    code, _, err = run(rule3_args("joserfc", *rule3_deposited("joserfc"), class_a=False))
    assert code == 2, err


# compare_mutants.py

def mutants_args(second: str) -> list[str]:
    return ["recompute/compare_mutants.py", "--second", second, "--first", "generated/mutants/joserfc"]


def test_mutants_deposited_inputs_agree():
    for f in ("described-cases.json", "described-cases.csv", "cases.tsv"):
        need(f"generated/mutants/joserfc/{f}")
    code, out, err = run(mutants_args(need("recompute/out/joserfc/second_mutants.json")))
    assert_agrees(code, out, err, COMPARED["mutants"]["joserfc"])
    assert re.search(r"^internal checks .*: checked [1-9]\d*, failed 0$", out, re.M)


@pytest.mark.parametrize("kind, path", [
    ("number", ["counts", "cases_of_the_study"]),
    ("identifier", ["rows", "comparison"]),
])
def test_mutants_perturbed_copy_differs(kind, path, tmp_path):
    copy = perturbed("recompute/out/joserfc/second_mutants.json", tmp_path / "second_mutants.json", path, kind)
    assert_differs(*run(mutants_args(str(copy))))


@pytest.mark.parametrize("path", [
    ["counts", "tool_mutants"],
    ["counts", "deletions"],
    ["counts", "tool_mutants_by_operator", None],
    ["counts", "tool_mutants_by_file", None],
    ["counts", "deletions_by_file", None],
])
def test_mutants_perturbed_total_differs(path, tmp_path):
    copy = changed("recompute/out/joserfc/second_mutants.json", tmp_path / "second_mutants.json", path, plus_1)
    code, out, err = run(mutants_args(str(copy)))
    assert_differs(code, out, err)
    assert re.search(rf"^DIFF counts\.totals \| counts\.{path[1]}", out, re.M), out


def test_mutants_missing_input_exits_2(tmp_path):
    code, _, _ = run(mutants_args(str(tmp_path / "absent.json")))
    assert code == 2


# compare_totals.py

def second_dir_copy(tmp_path: Path) -> Path:
    """Copy second_labels.json of the 4 libraries into tmp_path/second."""
    folder = tmp_path / "second"
    for name in LIBRARIES:
        src = EXPERIMENT / need(f"recompute/out/{name}/second_labels.json")
        (folder / name).mkdir(parents=True)
        (folder / name / "second_labels.json").write_bytes(src.read_bytes())
    return folder


def test_totals_deposited_inputs_agree():
    need("recompute/out/second_totals.json")
    need("generated/labels/summary.json")
    need("generated/trace/compare.json")
    for name in LIBRARIES:
        need(f"recompute/out/{name}/second_labels.json")
    code, out, err = run(["recompute/compare_totals.py"])
    assert_agrees(code, out, err, COMPARED["totals"])


@pytest.mark.parametrize("kind, path", [
    ("number", ["cases", "pooled", "agreed_label_none"]),
    ("status", ["expectations_labels", "overall", "L3", "status"]),
])
def test_totals_perturbed_totals_differ(kind, path, tmp_path):
    copy = perturbed("recompute/out/second_totals.json", tmp_path / "second_totals.json", path, kind)
    assert_differs(*run(["recompute/compare_totals.py", "--totals", str(copy)]))


def test_totals_perturbed_unit_identifier_differs(tmp_path):
    folder = second_dir_copy(tmp_path)
    perturbed("recompute/out/joserfc/second_labels.json", folder / "joserfc" / "second_labels.json",
              ["expectations", "L3", "units_ids", 0], "identifier")
    assert_differs(*run(["recompute/compare_totals.py", "--second-dir", str(folder)]))


def test_totals_missing_input_exits_2(tmp_path):
    code, _, _ = run(["recompute/compare_totals.py", "--totals", str(tmp_path / "absent.json")])
    assert code == 2
    folder = second_dir_copy(tmp_path)
    (folder / "authlib" / "second_labels.json").unlink()
    code, _, _ = run(["recompute/compare_totals.py", "--second-dir", str(folder)])
    assert code == 2

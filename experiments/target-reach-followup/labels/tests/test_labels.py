"""Tests of the label tooling on small synthetic inputs and on the synthetic
package of the target-reach toolkit (../target-reach/tests/fixture/toy)."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import analyse_labels
import check_first
import check_labels
import convert_reference
import parts
import prepare
from labelslib import (LABEL_COLUMNS, LabelError, Universe, ancestors, is_expected, label_text,
                       param_value_of, parse_basis, parse_label, read_tsv, validate_labels, write_tsv)

LABELS = Path(__file__).resolve().parents[1]
E = LABELS.parent.parent / "target-reach"
TOY = E / "tests" / "fixture"


# -- labels and bases ----------------------------------------------------------------

def test_parse_label():
    assert parse_label("none") == ("none",)
    assert parse_label(" core.f#1 ") == ("check", "core.f#1")
    p = parse_label("by-param claim: nbf=a.b#1; exp=a.c#2; iat=none")
    assert p == ("param", "claim", (("exp", "a.c#2"), ("iat", None), ("nbf", "a.b#1")))
    assert label_text(p) == "by-param claim: exp=a.c#2; iat=none; nbf=a.b#1"
    assert label_text(parse_label(label_text(p))) == label_text(p)
    for bad in ("", "a b", "by-param : x=a#1; y=b#1", "by-param c: x=a#1", "by-param c: x=a#1; x=b#1",
                "by-param c: x; y=b#1"):
        with pytest.raises(LabelError):
            parse_label(bad)


def test_parse_basis():
    assert parse_basis("none") == ("none",)
    assert parse_basis("name+class") == ("class", "name")
    assert parse_basis("assert") == ("assert",)
    for bad in ("", "class+class", "rule", "none+class", "class,name"):
        with pytest.raises(LabelError):
            parse_basis(bad)


def test_param_value():
    p = parse_label("by-param claim: exp=a#1; iat=b#1; nbf=none")
    assert param_value_of(p, "t.py::T::test_x[None-exp]") == ("a#1", ["exp"])
    assert param_value_of(p, "t.py::T::test_x[inf-nbf]") == (None, ["nbf"])
    assert param_value_of(p, "t.py::T::test_x[exp-iat]")[1] == ["exp", "iat"]      # 2 values: unresolved
    assert param_value_of(p, "t.py::T::test_x")[1] == []


def test_ancestors_and_builtins():
    classes = {"Base": ["Exception"], "Sub": ["Base"], "Odd": ["ext.Thing"]}
    assert ancestors("Sub", classes)[:3] == ["Sub", "Base", "Exception"]
    assert is_expected("Sub", ["Base"], classes)
    assert not is_expected("Base", ["Sub"], classes)
    assert is_expected("UnicodeDecodeError", ["ValueError"], {})      # built-in bases of the interpreter
    assert not is_expected("Odd", ["Exception"], classes)              # an outside base ends the walk


UNI = Universe(blocks={"t.py::a#0": ["Base"], "t.py::b#0": ["Base"], "t.py::c#0": ["Sub"]},
               checks={"m.f#1": "Sub", "m.g#1": "Base", "m.h#1": "Other"},
               classes={"Base": ["Exception"], "Sub": ["Base"], "Other": ["Exception"]})


def labels_rows(rows: list[list[str]]) -> tuple[list[str], list[dict]]:
    out = []
    for i, r in enumerate(rows, start=2):
        d = dict(zip(LABEL_COLUMNS, r))
        d["__line__"] = i
        out.append(d)
    return LABEL_COLUMNS, out


def test_validate_valid_and_class_outside():
    h, rows = labels_rows([["t.py::a#0", "m.f#1", "class", "q", ""],
                           ["t.py::b#0", "m.h#1", "name", "", ""],
                           ["t.py::c#0", "none", "none", "", "2 checks remain"]])
    res = validate_labels(h, rows, UNI)
    assert res["errors"] == []
    assert len(res["warnings"]) == 1                                  # basis name without a quote
    assert [c["label"] for c in res["class_outside"]] == ["m.h#1"]    # Other is no subclass of Base


def test_validate_errors():
    h, rows = labels_rows([["t.py::a#0", "m.x#1", "class", "q", ""],     # unknown check
                           ["t.py::a#0", "m.f#1", "class", "q", ""],     # accepted: the first row failed
                           ["t.py::a#0", "m.g#1", "class", "q", ""],     # labeled again
                           ["t.py::b#0", "none", "class", "", ""],       # none with a basis
                           ["t.py::z#0", "none", "none", "", "x"],       # not an included block
                           ["t.py::c#0", "none", "none", "", ""]])       # none without a reason
    res = validate_labels(h, rows, UNI)
    text = "\n".join(res["errors"])
    assert "m.x#1 is not a check id" in text and "labeled again" in text
    assert "label none needs basis none" in text and "not an included block" in text
    assert "basis none needs the reason" in text
    assert "has no label" not in text            # a row with an error is reported once, not as missing too
    h, rows = labels_rows([["t.py::a#0", "m.f#1", "class", "q", ""]])
    assert sum("has no label" in e for e in validate_labels(h, rows, UNI)["errors"]) == 2
    assert validate_labels(["block", "label"], [], UNI)["errors"]


# -- prepare.py ---------------------------------------------------------------------

def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def make_defs(root: Path) -> Path:
    defs = root / "defs"
    defs.mkdir(parents=True)
    (defs / "subject.json").write_text(json.dumps({
        "name": "syn", "commit": "0" * 40, "copy": ["syn", "tests"]}), encoding="utf-8")
    (defs / "checks.json").write_text(json.dumps({
        "checks": [{"id": "core.f#1", "file": "syn/core.py", "function": "f", "class": "Bad",
                    "lines": [[3, 3], [5, 6]], "template": "bad {*}", "guards": ["x < 0", None],
                    "reachable": True, "role": "subject"}],
        "classes": {"Bad": {"bases": ["Exception"], "module": "syn.core", "qualname": "Bad"}}}),
        encoding="utf-8")
    (defs / "blocks.json").write_text(json.dumps({"blocks": [
        {"key": "tests/test_a.py::test_a#0", "file": "tests/test_a.py", "header_span": [4, 4],
         "body_span": [5, 6], "test": "test_a", "test_class": None, "expected": ["Bad"], "included": True,
         "match": "bad", "match_unparsed": None, "post": [["str_eq", "bad x"], ["attr_eq", "code", 3]],
         "post_unparsed": ["assert e.value.args"]},
        {"key": "tests/test_a.py::T.test_b#0", "file": "tests/test_a.py", "header_span": [9, 10],
         "body_span": None, "test": "test_b", "test_class": "T", "expected": ["Bad"], "included": True,
         "match": None, "match_unparsed": None, "post": [], "post_unparsed": []},
        {"key": "tests/test_a.py::test_c#0", "file": "tests/test_a.py", "header_span": [12, 12],
         "body_span": [13, 13], "test": "test_c", "test_class": None, "expected": ["KeyError"],
         "included": False, "match": None, "match_unparsed": None, "post": [], "post_unparsed": []},
    ]}), encoding="utf-8")
    return defs / "subject.json"


def fake_reader(src: Path):
    """Stands in for the reading of the clone's object store: the files of a folder."""
    def tracked(clone, commit, paths):
        return sorted((p.relative_to(src).as_posix(), p.relative_to(src).as_posix())
                      for top in paths for p in (src / top).rglob("*") if p.is_file())

    def blobs(clone, oids):
        return {o: (src / o).read_bytes() for o in oids}
    return tracked, blobs


@pytest.fixture()
def synthetic_pack(tmp_path, monkeypatch):
    src = tmp_path / "src"
    write(src, {"syn/__init__.py": "", "syn/core.py": "class Bad(Exception):\n    pass\n",
                "tests/test_a.py": "def test_a():\n    pass\n", "other/x.py": "x = 1\n"})
    tracked, blobs = fake_reader(src)
    monkeypatch.setattr(prepare, "tracked_files", tracked)
    monkeypatch.setattr(prepare, "read_blobs", blobs)
    instruction = tmp_path / "READING.md"
    instruction.write_text("Label each block.\n", encoding="utf-8")
    subject = make_defs(tmp_path)
    out = tmp_path / "pack"
    rc = prepare.main(["--subject", str(subject), "--clone", str(src), "--instruction", str(instruction),
                       "--out", str(out)])
    assert rc == 0
    return out


def test_prepare_pack(synthetic_pack):
    out = synthetic_pack
    names = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert names == ["MANIFEST.txt", "READING.md", "blocks.tsv", "checks.tsv", "classes.tsv", "labels.tsv",
                     "src/syn/__init__.py", "src/syn/core.py", "src/tests/test_a.py"]
    h, checks = read_tsv(out / "checks.tsv")
    assert h == ["id", "file", "function", "class", "lines", "template", "guards"]
    assert "reachable" not in h and "role" not in h
    assert (checks[0]["lines"], checks[0]["guards"]) == ("3 | 5-6", "x < 0 | (none)")
    _, blocks = read_tsv(out / "blocks.tsv")
    assert [b["block"] for b in blocks] == ["tests/test_a.py::T.test_b#0", "tests/test_a.py::test_a#0"]
    a = blocks[1]
    assert (a["lines"], a["test"], a["expected"]) == ("4-6", "test_a", "Bad")
    assert a["assertions"] == ("match: bad | after the block: str(exception) == 'bad x' | after the block: "
                               "exception.code == 3 | after the block: assert e.value.args")
    assert (blocks[0]["lines"], blocks[0]["test"], blocks[0]["assertions"]) == ("9-10", "T.test_b", "")
    h, labels = read_tsv(out / "labels.tsv")
    assert h == LABEL_COLUMNS and [r["label"] for r in labels] == ["", ""]
    lines = (out / "MANIFEST.txt").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 8 and all(len(x.split("  ")[0]) == 64 for x in lines)
    assert prepare.verify_manifest(out) == []
    (out / "src" / "syn" / "core.py").write_text("changed\n", encoding="utf-8")
    (out / "extra.txt").write_text("x\n", encoding="utf-8")
    problems = prepare.verify_manifest(out)
    assert "src/syn/core.py: changed" in problems and "extra.txt: present and not listed" in problems


def test_assertion_texts_name_the_operation():
    """`excinfo.match(pattern)` searches the pattern in the text of the exception."""
    b = {"match": "bad .*", "post": [["match", "Token expired"], ["str_eq", "x"], ["str_in", "y"],
                                     ["attr_eq", "code", 3]]}
    assert prepare.assertion_texts(b) == [
        "match: bad .*",
        "after the block: re.search 'Token expired' in str(exception)",
        "after the block: str(exception) == 'x'",
        "after the block: 'y' in str(exception)",
        "after the block: exception.code == 3",
    ]


def test_prepare_reads_a_directory_of_a_repository(tmp_path):
    """The object store is read with git itself, for a package that lies in a
    directory of its repository (`repository_directory`): paths are relative to
    that directory, files outside it and files changed after the commit are
    not read, and symbolic links are skipped."""
    repo = tmp_path / "repo"
    write(repo, {"packages/syn/syn/__init__.py": "", "packages/syn/syn/core.py": "x = 1\n",
                 "packages/syn/tests/test_a.py": "def test_a():\n    pass\n",
                 "packages/syn/docs/index.rst": "docs\n", "packages/other/syn/core.py": "y = 2\n",
                 "syn/core.py": "z = 3\n"})
    (repo / "packages" / "syn" / "syn" / "link.py").symlink_to("core.py")

    def run(*args):
        res = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.org",
                              "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
        assert res.returncode == 0, res.stderr
        return res.stdout.strip()
    run("init", "-q")
    run("add", "-A")
    run("commit", "-q", "-m", "first")
    commit = run("rev-parse", "HEAD")
    # changes after the commit, in the working tree and in a later commit, are not read
    (repo / "packages" / "syn" / "syn" / "core.py").write_text("x = 99\n", encoding="utf-8")
    (repo / "packages" / "syn" / "syn" / "late.py").write_text("late = 1\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-q", "-m", "second")
    (repo / "packages" / "syn" / "syn" / "core.py").write_text("x = 100\n", encoding="utf-8")
    clone = repo / "packages" / "syn"
    files = prepare.tracked_files(clone, commit, ["syn", "tests"])
    assert [f for f, _ in files] == ["syn/__init__.py", "syn/core.py", "tests/test_a.py"]
    blobs = prepare.read_blobs(clone, [oid for _, oid in files])
    assert [blobs[oid] for _, oid in files] == [b"", b"x = 1\n", b"def test_a():\n    pass\n"]
    # the whole program on the same clone
    subject = make_defs(tmp_path)
    doc = json.loads(subject.read_text(encoding="utf-8"))
    doc["commit"] = commit
    doc["repository_directory"] = "packages/syn"
    subject.write_text(json.dumps(doc), encoding="utf-8")
    instruction = tmp_path / "READING.md"
    instruction.write_text("Label each block.\n", encoding="utf-8")
    out = tmp_path / "pack"
    assert prepare.main(["--subject", str(subject), "--clone", str(clone), "--instruction", str(instruction),
                         "--out", str(out)]) == 0
    names = sorted(p.relative_to(out / "src").as_posix() for p in (out / "src").rglob("*") if p.is_file())
    assert names == ["syn/__init__.py", "syn/core.py", "tests/test_a.py"]
    assert (out / "src" / "syn" / "core.py").read_text(encoding="utf-8") == "x = 1\n"
    assert run("status", "--porcelain") == "M packages/syn/syn/core.py"   # the clone is as it was


def test_prepare_refuses(tmp_path, monkeypatch):
    src = tmp_path / "src"
    write(src, {"syn/core.py": "x = 1\n", "syn/targets.json": "{}\n", "tests/t.py": ""})
    tracked, blobs = fake_reader(src)
    monkeypatch.setattr(prepare, "tracked_files", tracked)
    monkeypatch.setattr(prepare, "read_blobs", blobs)
    instruction = tmp_path / "READING.md"
    instruction.write_text("Label.\n", encoding="utf-8")
    subject = make_defs(tmp_path)
    args = ["--subject", str(subject), "--clone", str(src), "--instruction", str(instruction)]
    # a forbidden file name in the copied paths
    assert prepare.main(args + ["--out", str(tmp_path / "p1")]) == 1
    # a file with the bytes of a file of the experiment directories
    (src / "syn" / "targets.json").unlink()
    shutil.copy(E / "subjects" / "pyjwt" / "subject.json", src / "syn" / "copied.json")
    assert prepare.main(args + ["--out", str(tmp_path / "p2")]) == 1
    # a folder that is not empty, and a folder inside the deposit
    with pytest.raises(SystemExit):
        prepare.main(args + ["--out", str(tmp_path / "p2")])
    with pytest.raises(SystemExit):
        prepare.main(args + ["--out", str(LABELS / "pack-not-allowed")])
    assert not (LABELS / "pack-not-allowed").exists()


def test_check_labels_on_pack(synthetic_pack, tmp_path, capsys):
    good = tmp_path / "good.tsv"
    write_tsv(good, LABEL_COLUMNS, [["tests/test_a.py::test_a#0", "core.f#1", "class+assert", "match bad", ""],
                                    ["tests/test_a.py::T.test_b#0", "none", "none", "", "no assertion"]])
    assert check_labels.main(["--pack", str(synthetic_pack), "--labels", str(good),
                              "--json", str(tmp_path / "r.json")]) == 0
    doc = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert doc["labels"] == {"tests/test_a.py::T.test_b#0": "none", "tests/test_a.py::test_a#0": "core.f#1"}
    bad = tmp_path / "bad.tsv"
    write_tsv(bad, LABEL_COLUMNS, [["tests/test_a.py::test_a#0", "core.g#1", "class", "q", ""]])
    assert check_labels.main(["--pack", str(synthetic_pack), "--labels", str(bad)]) == 1
    (synthetic_pack / "checks.tsv").write_text("id\n", encoding="utf-8")
    assert check_labels.main(["--pack", str(synthetic_pack), "--labels", str(good)]) == 1
    assert "does not match its MANIFEST.txt" in capsys.readouterr().out


# -- convert_reference.py and check_first.py ----------------------------------------

def test_reference_basis():
    assert convert_reference.basis_of("match 'below'; name: minimum key length") == "assert+name"
    assert convert_reference.basis_of("class ExpiredSignatureError, which only the expiry check raises") == "class"
    assert convert_reference.basis_of("claim 'aud'; name: token without audience") == "assert+name"
    assert convert_reference.basis_of("message equals the check's") == "assert"
    with pytest.raises(SystemExit):
        convert_reference.basis_of("by analogy")


def test_check_first_on_synthetic(tmp_path):
    tk = tmp_path / "tk"
    write(tk, {
        "generated/syn/flags.csv": """
            block,index,test,basis,tier,target,target_template,deciding_check,deciding_template,target_fired,own_test_without_target
            t.py::a#0,0,a,name,name,m.X.f#2,x,m.X.f#1,y,no,passes
            """,
        "generated/syn/cases.csv": """
            block,index,test_node,expected,asserts,baseline_class,baseline_site,target,basis,tier,reaches_target,fired,target_fired,own_test_without_target
            t.py::a#0,0,t.py::a,E,class only,m.E,m.X.f#1,m.X.f#2,name,name,no,m.X.f#1,no,passes
            """,
        "subjects/syn/checks.json": json.dumps({"checks": [{"id": "m.X.f#1"}, {"id": "m.X.f#2"}]}),
        "readings/syn/FLAGS.md": """
            # syn
            The check the test
            describes is `X.f#1`, which decides.

            Counts: A 0, B 0, C 1, D 0.
            """})
    first = tmp_path / "first"
    first.mkdir()
    cols = check_first.COLUMNS
    write_tsv(first / "syn.tsv", cols, [["t.py::a#0", "0", "t.py::a", "C", "m.X.f#2", "m.X.f#1", "m.X.f#1",
                                         "The check the test describes is `X.f#1`, which decides.", ""]])
    assert check_first.check("syn", tk, first) == []
    write_tsv(first / "syn.tsv", cols, [["t.py::a#0", "0", "t.py::a", "A", "m.X.f#2", "m.X.f#1", "m.X.f#2",
                                         "The check the test describes is `X.f#1`, which matters.", ""]])
    problems = "\n".join(check_first.check("syn", tk, first))
    assert "does not occur in FLAGS.md" in problems and "does not name m.X.f#2" in problems
    assert "counts per class" in problems
    assert check_first.names_check("see `ac.validate#4`", "pkg.mod.Grant.validate#4")


# -- analyse_labels.py on the synthetic package of the toolkit -----------------------

@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    """Runs the target-reach toolkit on its synthetic package, in a temporary
    folder, and returns (subject.json, generated folder)."""
    root = tmp_path_factory.mktemp("toy")
    (root / "defs").mkdir()
    shutil.copy(TOY / "subject.json", root / "defs" / "subject.json")
    subject = root / "defs" / "subject.json"
    common = ["--subject", str(subject), "--work", str(root / "work")]
    run = [sys.executable, "-I", "-B", str(E / "reach" / "run.py")]
    subprocess.run(run + ["define", "targets", "baseline", "deletions", "whole-baseline", "whole-deletions"]
                   + common + ["--clone", str(TOY / "toy"), "--python", sys.executable],
                   check=True, capture_output=True)
    subprocess.run(run + ["pack"] + common + ["--out", str(root / "gen")], check=True, capture_output=True)
    proc = subprocess.run([sys.executable, "-I", "-B", str(E / "reach" / "analyse.py")] + common
                          + ["--out", str(root / "gen")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return subject, root / "gen"


def rule_labels(subject: Path) -> dict[str, list[str]]:
    targets = json.loads((subject.parent / "targets.json").read_text(encoding="utf-8"))
    out = {}
    for b in targets["blocks"]:
        out[b["key"]] = ([b["key"], b["target"], "class", "q", ""] if b["target"]
                         else [b["key"], "none", "none", "", "no single check"])
    return out


def key_with(rows: dict, part: str) -> str:
    hits = [k for k in rows if part in k]
    assert len(hits) == 1, (part, hits)
    return hits[0]


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_analyse_single_file_equals_rule(toy, tmp_path):
    subject, gen = toy
    labels = tmp_path / "rule.tsv"
    write_tsv(labels, LABEL_COLUMNS, sorted(rule_labels(subject).values()))
    out = tmp_path / "out"
    rc = analyse_labels.main(["--subject", str(subject), "--labels", str(labels), "--generated", str(gen),
                              "--out", str(out), "--first", str(tmp_path / "absent.tsv")])
    assert rc == 0
    c = json.loads((out / "counts.json").read_text(encoding="utf-8"))
    assert all(s["holds"] in (True, None) for s in c["sentinels"].values())
    # labels equal to the rule: no case or block where they differ
    r2 = c["rule_vs_label"]["rule 2"]["all"]
    assert r2["target differs from label"] == r2["label none"] == r2["no target"] == 0
    cells = c["rule_vs_label_blocks"]["rule 2"]["all"]
    assert cells["both, different"] == cells["rule only"] == cells["label only"] == 0
    # the outcome "decided by its label" equals the toolkit's count of cases decided by the target
    summary = json.loads((gen / "summary.json").read_text(encoding="utf-8"))
    assert c["outcomes"]["decided by its label"] == summary["counts"]["cases_reaching_target"]
    assert sum(c["outcomes"].values()) == summary["counts"]["cases_with_target"]


def test_analyse_two_readings(toy, tmp_path):
    subject, gen = toy
    base = rule_labels(subject)
    one, two = dict(base), dict(base)
    loop = key_with(base, "test_versions_loop#0")
    one[loop] = two[loop] = [loop, "core._check_signature#1", "name", "q", ""]   # decides once the version
    aud = key_with(base, "test_audience_mismatch#0")                              # check is deleted
    two[aud] = [aud, "none", "none", "", "unsure"]                                # 1 check and 1 none
    exp = key_with(base, "test_expired#0")
    two[exp] = [exp, "core._check_claims#2", "assert", "q", ""]                   # 2 different checks
    bj = key_with(base, "test_bad_json_body#0")
    pl = f"by-param body: {{={base[bj][1]}; [1,={base[bj][1]}"
    one[bj] = two[bj] = [bj, pl, "class", "q", ""]                                # by parameter, resolved
    f1, f2 = tmp_path / "r1.tsv", tmp_path / "r2.tsv"
    write_tsv(f1, LABEL_COLUMNS, sorted(one.values()))
    write_tsv(f2, LABEL_COLUMNS, sorted(two.values()))
    t3 = json.loads((subject.parent / "targets.json").read_text(encoding="utf-8"))
    for b in t3["blocks"]:
        if b["key"] == loop:
            b["target"], b["tier"], b["basis"] = "core._check_signature#1", "name", "name"
    (tmp_path / "t3.json").write_text(json.dumps(t3), encoding="utf-8")
    out = tmp_path / "out"
    rc = analyse_labels.main(["--subject", str(subject), "--labels", str(f1), str(f2), "--generated", str(gen),
                              "--targets3", str(tmp_path / "t3.json"), "--out", str(out),
                              "--first", str(tmp_path / "absent.tsv")])
    assert rc == 0
    c = json.loads((out / "counts.json").read_text(encoding="utf-8"))
    n = len(base)
    assert c["agreement"] == {"same check": n - 2 - sum(1 for v in base.values() if v[1] == "none"),
                              "both none": sum(1 for v in base.values() if v[1] == "none"),
                              "1 check and 1 none": 1, "2 different checks": 1}
    rows = read_rows(out / "outcomes.csv")
    loop_rows = [r for r in rows if r["block"] == loop]
    assert len(loop_rows) == 2
    assert {r["outcome"] for r in loop_rows} == {
        "label does not fire and decides once the deciding check is deleted"}
    assert {r["site_without_deciding"] for r in loop_rows} == {"core._check_signature#1"}
    assert c["outcomes"]["label does not fire and decides once the deciding check is deleted"] == 2
    # rule 2 targets the version check, rule 3 the label
    rv = read_rows(out / "rule-vs-label.csv")
    assert {r["category"] for r in rv if r["block"] == loop and r["rule"] == "rule 2"} == {
        "target differs from label"}
    assert {r["category"] for r in rv if r["block"] == loop and r["rule"] == "rule 3"} == {"target equals label"}
    assert {r["category"] for r in rv if r["block"] in (aud, exp)} == {"no agreed label"}
    assert c["rule_vs_label"]["rule 3"]["by_tier"]["name"]["target equals label"] >= 2
    bj_rows = [r for r in rv if r["block"] == bj and r["rule"] == "rule 2"]
    assert len(bj_rows) == 2 and {r["category"] for r in bj_rows} == {"target equals label"}
    # the agreement statistics: n blocks, 2 of them with unequal labels
    st = c["agreement_statistics"]
    assert st["labels"]["items"] == n and st["labels"]["equal"] == n - 2
    assert st["labels"]["observed"] == round((n - 2) / n, 4)
    assert st["check_or_none"]["items"] == n and st["check_or_none"]["equal"] == n - 1
    assert 0 < st["labels"]["kappa"] < 1
    # reading 1 names a check everywhere it is not `none` in both; with n0 blocks `none` in both:
    n0 = sum(1 for v in base.values() if v[1] == "none")
    p_o = (n - 1) / n
    p_e = ((n - n0) * (n - n0 - 1) + n0 * (n0 + 1)) / (n * n)
    assert st["check_or_none"]["kappa"] == round((p_o - p_e) / (1 - p_e), 4)
    assert "Cohen's kappa" in (out / "COUNTS.md").read_text(encoding="utf-8")


def test_kappa():
    k = analyse_labels.kappa
    assert k([]) == {"items": 0, "categories": 0, "equal": 0, "observed": None, "expected": None,
                     "kappa": None}
    # complete agreement on 2 categories used equally: kappa 1
    assert k([("a", "a"), ("b", "b")])["kappa"] == 1.0
    # 1 category only: chance agreement is 1 and kappa is not defined
    assert k([("a", "a"), ("a", "a")]) == {"items": 2, "categories": 1, "equal": 2, "observed": 1.0,
                                           "expected": 1.0, "kappa": None}
    # the textbook table: 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no -> p_o 0.7, p_e 0.5, kappa 0.4
    pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15
    v = k(pairs)
    assert (v["items"], v["categories"], v["equal"]) == (50, 2, 35)
    assert (v["observed"], v["expected"], v["kappa"]) == (0.7, 0.5, 0.4)
    # complete disagreement on 2 categories used equally: kappa -1
    assert k([("a", "b"), ("b", "a")])["kappa"] == -1.0


def test_analyse_sentinels_fail(toy, tmp_path):
    subject, gen = toy
    base = rule_labels(subject)
    bj = key_with(base, "test_bad_json_body#0")
    base[bj] = [bj, f"by-param body: x={base[bj][1]}; y=none", "class", "q", ""]   # resolves in no case
    labels = tmp_path / "l.tsv"
    write_tsv(labels, LABEL_COLUMNS, sorted(base.values()))
    gen2 = tmp_path / "gen"
    shutil.copytree(gen, gen2)
    rows = read_rows(gen2 / "cases.csv")
    rows[0]["baseline_site"] = "core.nothing#9"
    with (gen2 / "cases.csv").open("w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    out = tmp_path / "out"
    rc = analyse_labels.main(["--subject", str(subject), "--labels", str(labels), "--generated", str(gen2),
                              "--out", str(out), "--first", str(tmp_path / "absent.tsv")])
    assert rc == 1
    c = json.loads((out / "counts.json").read_text(encoding="utf-8"))
    held = {k: v["holds"] for k, v in c["sentinels"].items()}
    assert held["1"] is False and held["2"] is False and held["5"] is False
    assert held["3"] and held["4"] and held["6"] and held["7"] and held["8"]
    assert (out / "COUNTS.md").is_file() and (out / "agreement.csv").is_file()   # outputs written first


# -- parts.py -------------------------------------------------------------------------

def test_parts_split():
    files = ["t/a.py"] * 3 + ["t/b.py"] * 4 + ["t/c.py"] * 1 + ["t/d.py"] * 4
    assert parts.split(files, 12) == [("t/a.py", 1, 3), ("t/b.py", 1, 4), ("t/c.py", 1, 1), ("t/d.py", 1, 4)]
    # 2 parts of 12 blocks: the first ends with the file that reaches 6
    assert parts.split(files, 6) == [("t/a.py", 1, 3), ("t/b.py", 1, 4), ("t/c.py", 2, 1), ("t/d.py", 2, 4)]
    # a file larger than the limit is not divided, and the parts are numbered without a gap
    assert parts.split(["x.py"] * 9 + ["y.py"], 3) == [("x.py", 1, 9), ("y.py", 2, 1)]
    assert parts.split([], 5) == []
    # the order of the blocks does not matter
    assert parts.split(list(reversed(files)), 6) == parts.split(files, 6)
    with pytest.raises(ValueError):
        parts.split(files, 0)


def test_parts_join(synthetic_pack, tmp_path):
    pack = synthetic_pack
    a, b = "tests/test_a.py::T.test_b#0", "tests/test_a.py::test_a#0"
    assert parts.main(["split", "--pack", str(pack), "--max-blocks", "50", "--out", str(tmp_path / "p.tsv")]) == 0
    _, rows = read_tsv(tmp_path / "p.tsv")
    assert [(r["file"], r["part"], r["blocks"]) for r in rows] == [("tests/test_a.py", "1", "2")]
    one = tmp_path / "one.tsv"
    write_tsv(one, LABEL_COLUMNS, [[a, "none", "none", "", "generic"], [b, "core.f#1", "class", "q", ""]])
    out = tmp_path / "joined.tsv"
    assert parts.main(["join", "--pack", str(pack), "--parts", str(tmp_path / "p.tsv"), "--labels", str(one),
                       "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == one.read_text(encoding="utf-8")
    # 2 parts written here: each block from its own part; a label outside the part is not read
    order = [a, b]
    file_of = {a: "f1.py", b: "f2.py"}
    part_of = {"f1.py": 1, "f2.py": 2}
    l1 = (LABEL_COLUMNS, [{"block": a, "label": "x#1", "basis": "name", "quote": "", "note": ""},
                          {"block": b, "label": "wrong#9", "basis": "name", "quote": "", "note": ""}])
    l2 = (LABEL_COLUMNS, [{"block": a, "label": "", "basis": "", "quote": "", "note": ""},
                          {"block": b, "label": "y#2", "basis": "class", "quote": "", "note": ""}])
    rows, errors, outside = parts.join(order, file_of, part_of, [l1, l2])
    assert errors == [] and outside == [f"part 1: {b}"]
    assert rows == [[a, "x#1", "name", "", ""], [b, "y#2", "class", "", ""]]
    # a block missing in its part, a block twice, a wrong number of files
    rows, errors, _ = parts.join(order, file_of, part_of, [l1, (LABEL_COLUMNS, [l2[1][0], l2[1][0]])])
    assert any("twice" in e for e in errors) and any("missing" in e for e in errors)
    _, errors, _ = parts.join(order, file_of, part_of, [l1])
    assert errors == ["1 labels files for 2 parts"]

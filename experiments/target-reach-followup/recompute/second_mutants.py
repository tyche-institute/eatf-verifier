"""Second computation of the mutant counts of PROTOCOL.md, section 4.3, for 1 subject.

Command line (paths relative to the folder `target-reach-followup/`):

    python3 -I -B recompute/second_mutants.py \
        --subject ../target-reach/subjects/<name>/subject.json \
        --work work/mutants/<name> --mutants MUTANTS.csv --clone DIR \
        --cases CASES.tsv [--extra-tests DIR] \
        [--without-tests ID ...] [--replace OLD=NEW ...] --out FILE.json \
        [--records RECORDS.tar.xz] [--toolkit-second SECOND.py]

Inputs:

- `--subject`: `subject.json` of the toolkit; `checks.json` and `targets.json`
  beside it are read (the checks, their functions and lines, the targets of
  rule 2).
- `--records`: the deposited records of the toolkit (`records.tar.xz` or a
  folder unpacked from it); by default `<toolkit>/generated/<name>/records.tar.xz`,
  where `<toolkit>` is the folder 2 levels above the folder of `subject.json`.
  The cases of the study, their deciding checks, their classes and the tests
  that pass at baseline are taken from its `base-1.json`.
- `--work`: the raw records of the mutant runs: `manifest.json`, `mutated/<id>.py`,
  `runs/<id>.json`, `records/mutants/<id>.json`, `records/base-1.json`,
  `records/whole/base.json` and, with `--extra-tests`, `extra/<digest>/base.json`.
- `--mutants`: `mutants.csv` (id, file, function, changed lines, operator, check).
- `--clone`: the clone of the library; only the sources of the mutated files
  are read (spans of the checks, functions, changed lines).
- `--cases`: tab-separated, header `case`, `described`, `kind`, `variant`. Rows
  whose kind starts with "shadowed" are the shadowed rows. Rows of kind
  "comparison" are compared with the comparison cases derived here. Rows of
  any other kind are reported apart, with the same tables as shadowed rows.
- `--extra-tests`: the folder of the extra tests (repaired variants); its
  digest names the extra runs in the run records.
- `--without-tests`: whole-suite test keys (`<run>|<module>.<class>::<name>`)
  removed from the kills.
- `--replace OLD=NEW`: the whole-suite test OLD removed and the extra test NEW
  (a key, or the end of a key) added.
- `--toolkit-second`: the toolkit's own second computation, whose helpers
  (`case_key`, `passes`, `status_of`, `records_root`, `compute`) are used; by
  default `../../target-reach/recompute/second.py` relative to this file.

Groups of counts and the sections that define them (PROTOCOL.md of the
follow-up unless the toolkit is named):

- `per_mutant`: for every tool mutant and every deletion, the lines it
  changes, the whole-suite status, whether the suite kills it and which tests
  kill it (4.3 "Kills"); the detection under O_V, O_Vfc, O_C, O_T and O_S, and
  by the recorder suite (4.3 "Kills", last sentence; toolkit section 4,
  "Oracles" and "Status of a case"); the checks it is at and the checks in
  whose function it lies (4.3 "At a check"); the extra tests that kill it
  (4.3 "Killed by a variant").
- `checks`: for every check of the mutated files, its span, the tool mutants
  at it and in its function, and its deletion (4.3 "At a check").
- `tests`: for every whole-suite test with at least 1 kill, its kills and its
  unique kills, of tool mutants and of deletions (4.3 "Unique kill").
- `extra_tests`: the kills of each extra test (4.3 "Killed by a variant").
- `cases_file`: the shadowed rows, and the comparison cases derived from the
  definitions and the baseline records against the rows of kind "comparison"
  (4.3 "Comparison cases").
- `rows`: for each shadowed row, each comparison case and each row of another
  kind, the table of 4.3 "Reported".
- `library`: the mutants that the whole suite kills, without the given tests,
  with the given replacements, with the extra tests added, the same for the
  deletions, and per described check the mutants at it that the suite does
  not kill and the variant kills (4.3 "Reported", last sentence).
- `expectations`: M1, M2 and M3 with the counts behind each (section 2).
- `input_checks`: agreement of the inputs with each other (changed lines,
  digests, baselines, guards), and the deletions compared with the toolkit's
  deposited deletion records.
- `readings`: each choice made where the protocol leaves room.

Output: 1 JSON file, sorted keys, 2-space indentation. Exit status 0, or 2
when an input is missing or malformed.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SECOND = HERE.parent.parent / "target-reach" / "recompute" / "second.py"
ORACLES = ("O_V", "O_Vfc", "O_C", "O_T")
MUTANT_ORACLES = ("O_V", "O_Vfc", "O_C", "O_T", "O_S", "suite")
DELETION = "check_deletion"

READINGS = [
    "The cases of the study, their deciding checks, their classes at baseline and the tests that pass "
    "at baseline are read from the deposited base-1.json of the toolkit (section 3: the same cases and "
    "records); the base-1.json of the mutant runs is compared with it, message texts aside.",
    "A test is identified across suite runs by its key without the leading '<run>|' (4.3: a test that "
    "runs in several suite runs is 1 test); --without-tests and the OLD of --replace remove that test "
    "from every suite run.",
    "The kills of a completed whole-suite run are the tests listed as lost in its run record: the tests "
    "that pass in both unmodified whole-suite runs and do not pass on the mutant copy.",
    "A mutant whose whole-suite run is 'timeout' or 'error' after the repeat is killed by the suite and "
    "gives no kill to any test; it stays killed when tests are removed.",
    "An extra test kills a mutant only in a completed extra run (4.3 'Killed by a variant'); an extra "
    "run that is 'timeout' or 'error' kills nothing.",
    "Counts of mutants are of tool mutants; the deletions are reported apart in every table, and M1, M2 "
    "and M3 are decided on tool mutants, with the deletion of the relevant check reported beside them.",
    "Case detection follows the toolkit: an observed case is detected when the oracle holds at baseline "
    "and not on the mutant copy; a crashed case is detected under every oracle (under O_T only for a "
    "case with a target); withheld and missing cases are not detected in the main columns; a recorder "
    "run that is 'timeout' detects in every case under every oracle; a recorder run that is 'error' "
    "gives no value and is left out of the per-case groups.",
    "O_S for 1 case detects when the case's own test passes at baseline and not in the mutant's "
    "recorder run, or when the case is crashed.",
    "Mutant-level detection: an oracle detects when it detects in an observed case of the study; a "
    "crashed case anywhere is a detection under every oracle, O_T included; O_S detects when a test that "
    "holds a case of the study passes at baseline and not in the recorder run, or a case crashed; "
    "'suite' detects when any test that passes at baseline does not pass in the recorder run.",
    "'The test of the case does not pass in the recorder run' is true for a recorder run that is "
    "'timeout' and has no value for a recorder run that is 'error'.",
    "The lines a mutant changes are found by comparing the modified file with the file of the clone, "
    "line by line ('\\n' ends a line); they are compared with the column changed_lines of mutants.csv.",
    "The span of a check: for each raise statement, its lines and the lines of its innermost guard, "
    "found as reach.checks.guard_of finds it: the nearest enclosing 'if' statement of which the raise "
    "is not in the test (the lines of the test expression), or the nearest enclosing 'except' clause "
    "(from the 'except' line to the last line of the exception type, or the 'except' line alone when "
    "the clause names no type).",
    "The function of a check covers the lines of the definition that checks.json names, from its first "
    "decorator to its last line; a tool mutant lies in it when it changes at least 1 line and every "
    "changed line is in that range.",
    "Comparison cases: cases of the study whose rule-2 target is their deciding check, whose target is "
    "a check of a mutated file, and whose case key is not the case of a shadowed row; rows of other "
    "kinds do not make a case shadowed.",
    "Rows of the cases file whose kind neither starts with 'shadowed' nor is 'comparison' are reported "
    "apart under 'other_kinds', with the same tables and with M1 to M3 computed over them, and take no "
    "part in the shadowed results.",
    "M3, 'fires in no case of the baseline': the check is neither among the fired checks nor the "
    "deciding check of any recorded execution of an included block in the deposited base-1.json; the "
    "same over the cases of the study is reported beside it.",
    "M3, 'the suite with the variant': the whole suite with the variant added; where the whole suite "
    "does not kill the deletion, adding the variant and replacing the test by it give the same result.",
    "For the library, 'the same without the tests that hold a shadowed case' and 'with each such test "
    "replaced by its variant' are computed both from --without-tests and --replace as given, and from "
    "the rows of the cases file.",
]


class InputError(Exception):
    pass


def fail(msg: str):
    raise InputError(msg)


# -- loading -----------------------------------------------------------------------------

def load_json(path: Path, what: str):
    if not path.exists():
        fail(f"{what} is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        fail(f"{what} is malformed ({path}): {e}")


def load_second(path: Path):
    if not path.exists():
        fail(f"the toolkit's second.py is missing: {path}")
    spec = importlib.util.spec_from_file_location("toolkit_second", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["toolkit_second"] = mod
    spec.loader.exec_module(mod)
    return mod


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_lines(text: str) -> list[str]:
    """Lines with their ends; only '\\n' ends a line."""
    return re.findall(r"[^\n]*\n|[^\n]+$", text)


def parse_ranges(text: str) -> list[int]:
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, z = part.split("-", 1)
            out += list(range(int(a), int(z) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def rel_to_source(subject: dict, rel: str) -> str:
    src = subject.get("source_root", ".")
    return rel if src in (".", "") else f"{src.rstrip('/')}/{rel}"


def identity(key: str) -> str:
    """A whole-suite key without its suite run: 1 test across suite runs."""
    return key.split("|", 1)[1] if "|" in key else key


def nodeid_identity(nodeid: str) -> str:
    """The whole-suite identity of a pytest node id, as the junit classname gives it:
    `<module path with dots>[.<class>...]::<name>`, parameters kept with the name."""
    head, bracket, params = nodeid.partition("[")
    parts = head.split("::")
    module = parts[0][:-3] if parts[0].endswith(".py") else parts[0]
    classname = ".".join([module.replace("/", ".")] + parts[1:-1])
    return f"{classname}::{parts[-1]}{bracket}{params}"


def extra_digest(folder: Path) -> str:
    files = sorted(folder.glob("test_*.py"))
    if not files:
        fail(f"{folder}: no file test_*.py")
    h = hashlib.sha256()
    for f in files:
        h.update(f"{f.name}\0{file_sha256(f)}\n".encode())
    return h.hexdigest()[:16]


# -- functions, raise statements and spans ---------------------------------------------------

def functions(tree: ast.Module) -> dict[str, ast.AST]:
    """Qualified name -> definition, named as checks.json names functions: methods as
    `Class.method`, nested functions as `outer.inner`, the k-th definition (k >= 2) of 1
    name in 1 scope as `<name>~k`; definitions under `if`, `try` and `with` are read."""
    found: dict[str, ast.AST] = {}
    count: dict[str, int] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = prefix + child.name
                count[qual] = count.get(qual, 0) + 1
                if count[qual] > 1:
                    qual = f"{qual}~{count[qual]}"
                found[qual] = child
                walk(child, f"{qual}.")
            elif isinstance(child, (ast.If, ast.Try, ast.With)) or type(child).__name__ == "TryStar":
                walk(child, prefix)

    walk(tree, "")
    return found


def own_raises(fn: ast.AST) -> list[ast.Raise]:
    out = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(child, ast.Raise):
                out.append(child)
            visit(child)

    visit(fn)
    return out


def innermost_guard(node: ast.AST, fn: ast.AST):
    parents = {}
    for n in ast.walk(fn):
        for c in ast.iter_child_nodes(n):
            parents[c] = n
    cur = node
    while cur is not fn and cur in parents:
        par = parents[cur]
        if isinstance(par, ast.If) and cur is not par.test:
            return par
        if isinstance(par, ast.ExceptHandler):
            return par
        cur = par
    return None


def guard_text(g) -> str | None:
    if g is None:
        return None
    if isinstance(g, ast.If):
        return ast.unparse(g.test)
    head = "except"
    if g.type is not None:
        head += " " + ast.unparse(g.type)
    if g.name:
        head += " as " + g.name
    return head


def guard_lines(g) -> list[int]:
    if g is None:
        return []
    if isinstance(g, ast.If):
        return list(range(g.test.lineno, g.test.end_lineno + 1))
    end = g.type.end_lineno if g.type is not None else g.lineno
    return list(range(g.lineno, end + 1))


def function_range(fn: ast.AST) -> tuple[int, int]:
    first = min([fn.lineno] + [d.lineno for d in fn.decorator_list])
    return first, fn.end_lineno


def check_spans(checks: list[dict], sources: dict[str, str]) -> tuple[dict, list[str]]:
    """check id -> span record, and the guards that differ from checks.json."""
    out, problems = {}, []
    trees = {rel: ast.parse(text) for rel, text in sources.items()}
    fns = {rel: functions(t) for rel, t in trees.items()}
    for c in checks:
        rel = c["file"]
        if rel not in trees:
            continue
        fn = fns[rel].get(c["function"])
        if fn is None:
            fail(f"check {c['id']}: function {c['function']} not found in {rel}")
        raises = {(n.lineno, n.end_lineno): n for n in own_raises(fn)}
        raise_lines, glines, span, guards = set(), set(), set(), []
        for i, (a, z) in enumerate(c["lines"]):
            node = raises.get((a, z))
            if node is None:
                fail(f"check {c['id']}: no raise statement on lines {a}-{z} of {rel}")
            g = innermost_guard(node, fn)
            rl = set(range(a, z + 1))
            gl = set(guard_lines(g))
            raise_lines |= rl
            glines |= gl
            span |= rl | gl
            kind = None if g is None else ("if" if isinstance(g, ast.If) else "except")
            guards.append({"raise_lines": [a, z], "kind": kind, "lines": sorted(gl), "text": guard_text(g)})
            recorded = (c.get("guards") or [None] * len(c["lines"]))[i]
            if recorded != guard_text(g):
                problems.append(f"{c['id']} raise {a}-{z}: guard {guard_text(g)!r}, checks.json {recorded!r}")
        first, last = function_range(fn)
        out[c["id"]] = {"file": rel, "function": c["function"], "function_lines": [first, last],
                        "raise_lines": sorted(raise_lines), "guard_lines": sorted(glines - raise_lines),
                        "guards": guards, "span": sorted(span)}
    return out, problems


# -- the computation ---------------------------------------------------------------------------

def compute(args, second) -> dict:
    subject_path = Path(args.subject)
    subject = load_json(subject_path, "subject.json")
    name = subject.get("name")
    defs = subject_path.parent
    checks_doc = load_json(defs / "checks.json", "checks.json")
    targets_doc = load_json(defs / "targets.json", "targets.json")
    checks = {c["id"]: c for c in checks_doc["checks"]}
    target_of = {r["key"]: r.get("target") for r in targets_doc["blocks"]}

    records_arg = Path(args.records) if args.records else \
        subject_path.resolve().parent.parent.parent / "generated" / name / "records.tar.xz"
    if not records_arg.exists():
        fail(f"the toolkit's records are missing: {records_arg}")
    keep: list = []
    rec_root = second.records_root(str(records_arg), keep)
    base1 = load_json(rec_root / "base-1.json", "deposited base-1.json")

    work = Path(args.work)
    manifest_doc = load_json(work / "manifest.json", "manifest.json")
    if manifest_doc.get("subject") != name:
        fail(f"manifest.json is of {manifest_doc.get('subject')}, not of {name}")
    manifest = manifest_doc["mutants"]
    mutated_files = sorted(manifest_doc["files"])
    local_base1 = load_json(work / "records" / "base-1.json", "base-1.json of the mutant runs")
    local_base2 = load_json(work / "records" / "base-2.json", "base-2.json of the mutant runs")
    whole_base = load_json(work / "records" / "whole" / "base.json", "whole/base.json of the mutant runs")
    passing_whole = set(whole_base["passing"])

    # -- mutants.csv
    mpath = Path(args.mutants)
    if not mpath.exists():
        fail(f"mutants.csv is missing: {mpath}")
    with mpath.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        need = {"mutant", "file", "function", "changed_lines", "operator", "sha256", "check"}
        if not need <= set(reader.fieldnames or []):
            fail(f"mutants.csv lacks the columns {sorted(need - set(reader.fieldnames or []))}")
        csv_rows = {r["mutant"]: r for r in reader}
    if set(csv_rows) != set(manifest):
        fail(f"mutants.csv and manifest.json list different mutants: "
             f"{sorted(set(csv_rows) ^ set(manifest))[:5]}")
    ids = sorted(manifest)
    tool_ids = [m for m in ids if csv_rows[m]["operator"] != DELETION]
    del_ids = [m for m in ids if csv_rows[m]["operator"] == DELETION]

    # -- sources of the clone
    clone = Path(args.clone)
    sources, digests_ok = {}, {}
    for rel in mutated_files:
        p = clone / rel_to_source(subject, rel)
        if not p.exists():
            fail(f"a mutated file is missing from the clone: {p}")
        sources[rel] = p.read_bytes().decode("utf-8")
        digests_ok[rel] = file_sha256(p) == checks_doc["sha256"].get(rel)
    if not all(digests_ok.values()):
        fail(f"files of the clone differ from those checks.json was made from: "
             f"{sorted(k for k, v in digests_ok.items() if not v)}")
    spans, guard_problems = check_spans(checks_doc["checks"], sources)

    # -- changed lines of every mutant
    changed: dict[str, list[int]] = {}
    changed_mismatch, digest_mismatch, length_mismatch = [], [], []
    for m in ids:
        e = manifest[m]
        row = csv_rows[m]
        csv_lines = parse_ranges(row["changed_lines"])
        if e.get("path") is None:
            changed[m] = csv_lines
            continue
        p = work / e["path"]
        if not p.exists():
            fail(f"the modified file of {m} is missing: {p}")
        data = p.read_bytes()
        d = hashlib.sha256(data).hexdigest()
        if d != e["sha256"] or (row["sha256"] and d != row["sha256"]):
            digest_mismatch.append(m)
        old, new = split_lines(sources[e["file"]]), split_lines(data.decode("utf-8"))
        if len(old) != len(new):
            length_mismatch.append(m)
        lines = [i + 1 for i, (x, y) in enumerate(zip(old, new)) if x != y]
        changed[m] = lines
        if lines != csv_lines:
            changed_mismatch.append(m)

    # -- at a check, in the function of a check
    file_checks = {cid: s for cid, s in spans.items()}
    at: dict[str, dict[str, str]] = {m: {} for m in ids}
    in_fn: dict[str, list[str]] = {m: [] for m in ids}
    for m in ids:
        rel = manifest[m]["file"]
        cl = set(changed[m])
        if csv_rows[m]["operator"] == DELETION:
            cid = csv_rows[m]["check"] or manifest[m].get("check")
            if cid not in file_checks:
                fail(f"deletion {m}: check {cid} is not a check of a mutated file")
            at[m][cid] = "deletion"
            in_fn[m] = [cid]
            continue
        for cid, s in file_checks.items():
            if s["file"] != rel:
                continue
            hit = cl & set(s["span"])
            if hit:
                r = bool(hit & set(s["raise_lines"]))
                g = bool(hit & set(s["guard_lines"]))
                at[m][cid] = "raise and guard" if r and g else ("raise" if r else "guard")
            a, z = s["function_lines"]
            if cl and all(a <= x <= z for x in cl):
                in_fn[m].append(cid)
    deletion_of = {}
    for m in del_ids:
        cid = csv_rows[m]["check"] or manifest[m].get("check")
        if cid in deletion_of:
            fail(f"2 deletions of check {cid}")
        deletion_of[cid] = m
    deletion_not_at_own_raises = [m for m in del_ids
                                  if not set(changed[m]) <= set(spans[csv_rows[m]["check"]]["raise_lines"])
                                  or not changed[m]]

    # -- cases of the study (deposited baseline)
    base_cases = [c for c in base1["cases"] if c.get("included")]
    study = [c for c in base_cases if c.get("raised") and c.get("rejection") and c.get("check_result") == "accepted"]
    study_by_key = {second.case_key(c): c for c in study}
    recorded_by_key = {second.case_key(c): c for c in base_cases}

    def decider(c: dict) -> str | None:
        site = c.get("site")
        if site and site.get("kind") == "check" and site.get("check"):
            return site["check"]
        return None

    def firing(c: dict) -> set:
        s = set(c.get("fired") or [])
        if decider(c):
            s.add(decider(c))
        return s

    base_tests = {t["nodeid"]: t for t in base1["tests"]}
    base_passing = {k for k, t in base_tests.items() if second.passes(t)}
    study_tests = {c["test"] for c in study}

    # -- run records
    digest = None
    extra_base = None
    extra_tests: list[str] = []
    if args.extra_tests:
        folder = Path(args.extra_tests)
        if not folder.is_dir():
            fail(f"--extra-tests is not a folder: {folder}")
        digest = extra_digest(folder)
        extra_base = load_json(work / "extra" / digest / "base.json", f"extra/{digest}/base.json")
        extra_tests = sorted(extra_base["tests"])
    extra_passing = set(extra_base["passing"]) if extra_base else set()

    runs, recs = {}, {}
    for m in ids:
        r = load_json(work / "runs" / f"{m}.json", f"run record of {m}")
        if r.get("mutant") != m or r.get("sha256") != manifest[m]["sha256"]:
            fail(f"run record of {m} is not of the modified file of manifest.json")
        for part in ("recorder", "whole"):
            if part not in r or "status" not in r[part]:
                fail(f"run record of {m} has no {part} status")
        if digest is not None and digest not in (r.get("extra") or {}):
            fail(f"run record of {m} has no run of the extra tests {digest}")
        runs[m] = r
        if r["recorder"]["status"] == "completed":
            recs[m] = load_json(work / "records" / "mutants" / f"{m}.json", f"recorder record of {m}")

    lost_not_passing = sorted({k for m in ids if runs[m]["whole"]["status"] == "completed"
                               for k in runs[m]["whole"]["lost"] if k not in passing_whole})

    # -- per mutant: kills and detection
    whole_status = {m: runs[m]["whole"]["status"] for m in ids}
    kills = {m: (sorted({identity(k) for k in runs[m]["whole"]["lost"]}) if whole_status[m] == "completed" else [])
             for m in ids}
    killed_by_suite = {m: whole_status[m] != "completed" or bool(kills[m]) for m in ids}

    def extra_kills(m: str) -> list[str]:
        if digest is None:
            return []
        e = runs[m]["extra"][digest]
        return sorted(e["lost"]) if e["status"] == "completed" else []

    xkills = {m: extra_kills(m) for m in ids}

    row_cases: set[str] = set()     # filled below; per-case detection kept only for these
    per_case_det: dict[str, dict[str, dict]] = {}

    def detect(m: str, keys_of_interest: set) -> dict:
        st = runs[m]["recorder"]["status"]
        if st == "timeout":
            det = {o: True for o in MUTANT_ORACLES}
            wf = {o: True for o in ORACLES}
            cases = {k: {"status": "timeout", **{o: True for o in ORACLES + ("O_S",)},
                         "test_passes": False} for k in keys_of_interest}
            return {"status": st, "detected": det, "detected_withheld_as_failing": wf, "cases": cases,
                    "case_status": {}}
        if st != "completed":
            return {"status": st, "detected": None, "detected_withheld_as_failing": None,
                    "cases": {k: None for k in keys_of_interest}, "case_status": {}}
        rec = recs[m]
        run_cases = {second.case_key(c): c for c in rec["cases"] if c.get("included")}
        run_tests = {t["nodeid"]: t for t in rec["tests"]}
        det = {o: False for o in MUTANT_ORACLES}
        wf = {o: False for o in ORACLES}
        statuses = Counter()
        crashed = False
        cases = {}
        for ck, c in study_by_key.items():
            stt = second.status_of(ck, c["test"], run_cases, run_tests)
            statuses[stt] += 1
            t = target_of.get(c["block"])
            base_hold = {"O_V": True, "O_Vfc": True, "O_C": True, "O_T": bool(t) and decider(c) == t}
            cd = {o: False for o in ORACLES}
            if stt == "observed":
                r = run_cases[ck]
                raised = bool(r.get("raised"))
                site = r.get("site") or {}
                hold = {"O_V": raised and bool(r.get("rejection")), "O_Vfc": raised,
                        "O_C": raised and r.get("class") == c.get("class"),
                        "O_T": raised and bool(t) and site.get("check") == t}
                for o in ORACLES:
                    if base_hold[o] and not hold[o]:
                        cd[o] = True
                        det[o] = True
            elif stt == "crashed":
                crashed = True
                for o in ORACLES:
                    cd[o] = True if o != "O_T" else bool(t)
            elif stt == "withheld":
                for o in ORACLES:
                    if base_hold[o]:
                        wf[o] = True
            test_passes = second.passes(run_tests.get(c["test"]))
            os_ = (c["test"] in base_passing and not test_passes) or stt == "crashed"
            if ck in keys_of_interest:
                cases[ck] = {"status": stt, **cd, "O_S": os_, "test_passes": test_passes}
        if crashed:
            for o in ORACLES:
                det[o] = True
        for o in ORACLES:
            wf[o] = wf[o] or det[o]
        lost_own = [t for t in study_tests if t in base_passing and not second.passes(run_tests.get(t))]
        lost_any = [t for t in base_passing if not second.passes(run_tests.get(t))]
        det["O_S"] = bool(lost_own) or crashed
        det["suite"] = bool(lost_any)
        for k in keys_of_interest:
            if k not in cases:      # a row case that is not a case of the study
                cases[k] = None
        return {"status": st, "detected": det, "detected_withheld_as_failing": wf, "cases": cases,
                "case_status": dict(sorted(statuses.items()))}

    # -- cases file
    cpath = Path(args.cases)
    if not cpath.exists():
        fail(f"the cases file is missing: {cpath}")
    with cpath.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        need = {"case", "described", "kind", "variant"}
        if not need <= set(reader.fieldnames or []):
            fail(f"the cases file lacks the columns {sorted(need - set(reader.fieldnames or []))}")
        file_rows = [dict(r) for r in reader]

    def resolve_extra(text: str, what: str) -> str:
        if not extra_tests:
            fail(f"{what} names the extra test {text!r}, but no --extra-tests is given")
        found = [k for k in extra_tests if k == text or k.endswith(text)]
        if len(found) != 1:
            fail(f"{what}: {text!r} matches {len(found)} extra tests")
        return found[0]

    shadowed_rows, comparison_file_rows, other_rows = [], [], []
    for i, r in enumerate(file_rows, 2):
        case, described, kind = (r.get("case") or "").strip(), (r.get("described") or "").strip(), \
            (r.get("kind") or "").strip()
        variant = (r.get("variant") or "").strip()
        if case not in recorded_by_key:
            fail(f"cases file, line {i}: {case!r} is no recorded case of an included block")
        if described not in checks:
            fail(f"cases file, line {i}: {described!r} is no check of checks.json")
        row = {"case": case, "described": described, "kind": kind,
               "variant": resolve_extra(variant, f"cases file, line {i}") if variant else None,
               "variant_as_written": variant or None}
        if kind.startswith("shadowed"):
            shadowed_rows.append(row)
        elif kind == "comparison":
            comparison_file_rows.append(row)
        else:
            other_rows.append(row)

    shadowed_cases = {r["case"] for r in shadowed_rows}
    derived = []
    for ck, c in sorted(study_by_key.items()):
        t = target_of.get(c["block"])
        if t and decider(c) == t and checks.get(t, {}).get("file") in mutated_files and ck not in shadowed_cases:
            derived.append(ck)
    comparison_rows = [{"case": ck, "described": target_of[study_by_key[ck]["block"]], "kind": "comparison",
                        "variant": None, "variant_as_written": None} for ck in derived]
    file_comp = sorted({r["case"] for r in comparison_file_rows})
    file_comp_described_ok = sorted(r["case"] for r in comparison_file_rows
                                    if r["case"] in study_by_key
                                    and r["described"] == target_of.get(study_by_key[r["case"]]["block"]))

    row_cases = {r["case"] for r in shadowed_rows + other_rows + comparison_rows}
    for m in ids:
        per_case_det[m] = detect(m, row_cases)

    # -- per mutant output
    per_mutant = {}
    for m in ids:
        d = per_case_det[m]
        per_mutant[m] = {
            "kind": "deletion" if m in del_ids else "tool mutant",
            "file": manifest[m]["file"], "function": csv_rows[m]["function"],
            "operator": csv_rows[m]["operator"], "check": csv_rows[m]["check"] or None,
            "changed_lines": changed[m],
            "at_checks": dict(sorted(at[m].items())),
            "in_functions_of_checks": sorted(in_fn[m]),
            "whole_suite_status": whole_status[m], "whole_suite_runs": runs[m]["whole"].get("runs"),
            "killed_by_suite": killed_by_suite[m],
            "killed_by_suite_as": ("a test" if kills[m] else (whole_status[m] if whole_status[m] != "completed"
                                                              else "not killed")),
            "killing_tests": kills[m],
            "recorder_status": d["status"], "recorder_runs": runs[m]["recorder"].get("runs"),
            "detected": d["detected"], "detected_withheld_as_failing": d["detected_withheld_as_failing"],
            "case_status": d["case_status"],
            "extra_status": runs[m]["extra"][digest]["status"] if digest else None,
            "killing_extra_tests": xkills[m],
        }

    # -- checks
    checks_out = {}
    for cid, s in sorted(spans.items()):
        tool_at = sorted(m for m in tool_ids if cid in at[m])
        tool_fn = sorted(m for m in tool_ids if cid in in_fn[m])
        fires_rec = any(cid in firing(c) for c in base_cases)
        fires_study = any(cid in firing(c) for c in study)
        checks_out[cid] = {**s, "tool_mutants_at": tool_at, "tool_mutants_at_count": len(tool_at),
                           "tool_mutants_in_function": tool_fn, "tool_mutants_in_function_count": len(tool_fn),
                           "deletion": deletion_of.get(cid),
                           "fires_in_a_recorded_case_of_the_baseline": fires_rec,
                           "fires_in_a_case_of_the_study": fires_study,
                           "deciding_check": any(decider(c) == cid for c in study),
                           "reachable": checks[cid].get("reachable")}

    # -- tests and unique kills
    def per_test(group: list[str]) -> dict:
        out: dict[str, dict] = {}
        for m in group:
            for t in kills[m]:
                out.setdefault(t, {"kills": [], "unique_kills": []})["kills"].append(m)
                if len(kills[m]) == 1:
                    out[t]["unique_kills"].append(m)
        return out

    pt_tool, pt_del = per_test(tool_ids), per_test(del_ids)
    keys_of = {}
    for k in passing_whole:
        keys_of.setdefault(identity(k), []).append(k)
    tests_out = {}
    for t in sorted(set(pt_tool) | set(pt_del)):
        a, b = pt_tool.get(t, {"kills": [], "unique_kills": []}), pt_del.get(t, {"kills": [], "unique_kills": []})
        tests_out[t] = {"keys": sorted(keys_of.get(t, [])),
                        "kills": sorted(a["kills"]), "kills_count": len(a["kills"]),
                        "unique_kills": sorted(a["unique_kills"]), "unique_kills_count": len(a["unique_kills"]),
                        "unique_kills_at_checks": sorted({c for m in a["unique_kills"] for c in at[m]}),
                        "deletions_killed": sorted(b["kills"]), "deletions_killed_count": len(b["kills"]),
                        "unique_deletion_kills": sorted(b["unique_kills"]),
                        "unique_deletion_kills_checks": sorted(csv_rows[m]["check"] for m in b["unique_kills"])}

    extra_out = {}
    for x in extra_tests:
        tk = sorted(m for m in tool_ids if x in xkills[m])
        dk = sorted(m for m in del_ids if x in xkills[m])
        extra_out[x] = {"passes_in_both_unmodified_runs": x in extra_passing,
                        "kills": tk, "kills_count": len(tk), "deletions_killed": dk,
                        "deletions_killed_count": len(dk),
                        "deletions_killed_checks": sorted(csv_rows[m]["check"] for m in dk)}

    # -- rows (4.3 "Reported")
    def group_table(members: list[str], case: str, test_id: str, variant: str | None) -> dict:
        members = sorted(members)
        valued = [m for m in members if per_case_det[m]["cases"].get(case) is not None]
        t = {
            "mutants": members,
            "killed_by_suite": [m for m in members if killed_by_suite[m]],
            "detected_by_the_case_under_O_C": [m for m in valued if per_case_det[m]["cases"][case]["O_C"]],
            "test_of_the_case_does_not_pass_in_the_recorder_run":
                [m for m in valued if not per_case_det[m]["cases"][case]["test_passes"]],
            "killed_by_its_test": [m for m in members if test_id in kills[m]],
            "unique_kills_of_its_test": [m for m in members if kills[m] == [test_id]],
            "killed_by_the_variant": ([m for m in members if variant in xkills[m]] if variant else None),
            "recorder_run_without_a_value": [m for m in members if per_case_det[m]["cases"].get(case) is None],
        }
        t["counts"] = {k: (len(v) if v is not None else None) for k, v in t.items() if k != "counts"}
        return t

    def row_report(r: dict) -> dict:
        case = r["case"]
        c = recorded_by_key[case]
        dec = decider(c)
        desc = r["described"]
        test_id = nodeid_identity(c["test"])
        v = r["variant"]
        at_desc = [m for m in tool_ids if desc in at[m]]
        at_dec = [m for m in tool_ids if dec and dec in at[m]]
        groups = {
            "tool_mutants_at_the_described_check": at_desc,
            "tool_mutants_at_the_deciding_check": at_dec,
            "tool_mutants_at_the_described_and_not_at_the_deciding_check": [m for m in at_desc if m not in set(at_dec)],
            "tool_mutants_in_the_function_of_the_described_check": [m for m in tool_ids if desc in in_fn[m]],
            "tool_mutants_in_the_function_of_the_deciding_check": [m for m in tool_ids if dec and dec in in_fn[m]],
            "tool_mutants_in_all_mutated_files": list(tool_ids),
            "deletion_of_the_described_check": [deletion_of[desc]] if desc in deletion_of else [],
            "deletion_of_the_deciding_check": [deletion_of[dec]] if dec in deletion_of else [],
        }
        return {"case": case, "kind": r["kind"], "described_check": desc, "deciding_check": dec,
                "target_rule_2": target_of.get(c["block"]), "case_of_the_study": case in study_by_key,
                "test": test_id, "test_whole_suite_keys": sorted(keys_of.get(test_id, [])),
                "test_passes_at_baseline_recorder": c["test"] in base_passing,
                "variant": v, "variant_as_written": r["variant_as_written"],
                "described_check_in_mutated_files": desc in spans,
                "deciding_check_in_mutated_files": bool(dec) and dec in spans,
                "described_check_fires_in_a_recorded_case_of_the_baseline": any(desc in firing(x) for x in base_cases),
                "described_check_fires_in_a_case_of_the_study": any(desc in firing(x) for x in study),
                "groups": {g: group_table(ms, case, test_id, v) for g, ms in groups.items()}}

    def rows_out(rows: list[dict]) -> dict:
        out: dict[str, dict] = {}
        for r in rows:
            out.setdefault(r["case"], {})[r["described"]] = row_report(r)
        return out

    rep_shadowed, rep_other = rows_out(shadowed_rows), rows_out(other_rows)
    rep_comparison = rows_out(comparison_rows)

    # -- library
    without = [identity(k) for k in (args.without_tests or [])]
    for k in args.without_tests or []:
        if k not in passing_whole:
            fail(f"--without-tests: {k!r} is no test that passes in both unmodified whole-suite runs")
    replacements = []
    for item in args.replace or []:
        if "=" not in item:
            fail(f"--replace: {item!r} is not OLD=NEW")
        old, new = item.rsplit("=", 1)
        if old not in passing_whole:
            fail(f"--replace: {old!r} is no test that passes in both unmodified whole-suite runs")
        replacements.append({"old": old, "new": resolve_extra(new, "--replace")})

    def killed_set(group, removed=(), added=()) -> list[str]:
        rem, add = set(removed), set(added)
        return sorted(m for m in group if whole_status[m] != "completed" or (set(kills[m]) - rem)
                      or (add & set(xkills[m])))

    def scoring(group: list[str], removed: list[str], added: list[str]) -> dict:
        def block(ms):
            return {"ids": ms, "count": len(ms)}
        base = killed_set(group)
        errors = [m for m in group if whole_status[m] == "error"]
        out = {
            "total": len(group),
            "killed_by_the_whole_suite": block(base),
            "killed_by_the_whole_suite_by_kind": {
                "by_a_test": len([m for m in group if kills[m]]),
                "timeout": len([m for m in group if whole_status[m] == "timeout"]),
                "error": len(errors)},
            "score": (len(base) / len(group)) if group else None,
            "score_without_error_mutants": ((len(base) - len(errors)) / (len(group) - len(errors)))
            if len(group) > len(errors) else None,
            "killed_without_the_given_tests": block(killed_set(group, removed=removed)),
            "killed_with_the_given_replacements": block(killed_set(
                group, removed=[identity(r["old"]) for r in replacements], added=[r["new"] for r in replacements])),
            "killed_with_the_extra_tests_added": block(killed_set(group, added=extra_tests)),
        }
        out["not_killed_by_the_whole_suite"] = block(sorted(set(group) - set(base)))
        return out

    removed_unique = sorted({m for t in without for m in pt_tool.get(t, {}).get("unique_kills", [])})
    library = {
        "without_tests": sorted(args.without_tests or []),
        "replacements": replacements,
        "extra_tests": extra_tests,
        "extra_digest": digest,
        "tool_mutants": scoring(tool_ids, without, extra_tests),
        "deletions": scoring(del_ids, without, extra_tests),
        "unique_kills_of_the_removed_tests": {"ids": removed_unique, "count": len(removed_unique)},
    }
    lt = library["tool_mutants"]
    library["removal_check"] = {
        "killed_minus_killed_without_the_given_tests":
            lt["killed_by_the_whole_suite"]["count"] - lt["killed_without_the_given_tests"]["count"],
        "unique_kills_of_the_removed_tests": len(removed_unique),
        "note": "the 2 numbers are equal when no mutant is killed by 2 or more removed tests and by no other test",
    }

    def from_rows(rows: list[dict]) -> dict:
        tests = sorted({nodeid_identity(recorded_by_key[r["case"]]["test"]) for r in rows})
        repl = sorted({(nodeid_identity(recorded_by_key[r["case"]]["test"]), r["variant"]) for r in rows
                       if r["variant"]})
        rem_repl = [t for t, _ in repl]
        add_repl = [v for _, v in repl]
        described = {}
        for r in rows:
            v = r["variant"]
            at_desc = [m for m in tool_ids if r["described"] in at[m]]
            entry = described.setdefault(r["described"], {})
            key = v or "(no variant)"
            not_killed = [m for m in at_desc if not killed_by_suite[m]]
            entry[key] = {
                "tool_mutants_at_the_check": len(at_desc),
                "not_killed_by_the_suite": not_killed,
                "not_killed_by_the_suite_and_killed_by_the_variant":
                    [m for m in not_killed if v and v in xkills[m]] if v else None,
                "deletion": deletion_of.get(r["described"]),
                "deletion_killed_by_the_suite": killed_by_suite[deletion_of[r["described"]]]
                if r["described"] in deletion_of else None,
                "deletion_killed_by_the_variant": (v in xkills[deletion_of[r["described"]]])
                if v and r["described"] in deletion_of else None,
            }
        out = {"tests_that_hold_a_row": [{"test": t, "keys": sorted(keys_of.get(t, []))} for t in tests],
               "replacements": [{"test": t, "variant": v} for t, v in repl],
               "described_checks": described}
        for label, group in (("tool_mutants", tool_ids), ("deletions", del_ids)):
            out[label] = {
                "killed_by_the_whole_suite": len(killed_set(group)),
                "killed_without_the_tests_that_hold_a_row": {
                    "ids": killed_set(group, removed=tests), "count": len(killed_set(group, removed=tests))},
                "killed_with_each_such_test_replaced_by_its_variant": {
                    "ids": killed_set(group, removed=rem_repl, added=add_repl),
                    "count": len(killed_set(group, removed=rem_repl, added=add_repl))},
            }
        return out

    library["from_shadowed_rows"] = from_rows(shadowed_rows)
    if other_rows:
        library["from_rows_of_other_kinds"] = from_rows(other_rows)

    # -- expectations
    def expectations(rows: list[dict], reports: dict) -> dict:
        m1_rows, m2_rows, m3_rows = {}, {}, {}
        for r in rows:
            rep = reports[r["case"]][r["described"]]
            g = rep["groups"]
            key = f"{r['case']} -> {r['described']}"
            m1_rows[key] = {
                "test": rep["test"], "deciding_check": rep["deciding_check"],
                "unique_kills_of_its_test_at_the_deciding_check":
                    g["tool_mutants_at_the_deciding_check"]["unique_kills_of_its_test"],
                "tool_mutants_at_the_deciding_check": len(g["tool_mutants_at_the_deciding_check"]["mutants"]),
                "deletion_of_the_deciding_check_is_a_unique_kill_of_its_test":
                    g["deletion_of_the_deciding_check"]["unique_kills_of_its_test"] != []
                    if g["deletion_of_the_deciding_check"]["mutants"] else None,
            }
            m2_rows[key] = {
                "detected_under_O_C_at_the_described_and_not_at_the_deciding_check":
                    g["tool_mutants_at_the_described_and_not_at_the_deciding_check"]["detected_by_the_case_under_O_C"],
                "tool_mutants_at_the_described_and_not_at_the_deciding_check":
                    len(g["tool_mutants_at_the_described_and_not_at_the_deciding_check"]["mutants"]),
                "deletion_of_the_described_check_detected_under_O_C":
                    (g["deletion_of_the_described_check"]["detected_by_the_case_under_O_C"] != [])
                    if g["deletion_of_the_described_check"]["mutants"] and r["described"] != rep["deciding_check"]
                    else None,
                "recorder_runs_without_a_value":
                    g["tool_mutants_at_the_described_and_not_at_the_deciding_check"]["recorder_run_without_a_value"],
            }
            if r["variant"]:
                d = deletion_of.get(r["described"])
                fires = rep["described_check_fires_in_a_recorded_case_of_the_baseline"]
                vk = g["tool_mutants_at_the_described_check"]["killed_by_the_variant"]
                entry = {
                    "variant": r["variant"],
                    "variant_kills_at_the_described_check": vk,
                    "tool_mutants_at_the_described_check": len(g["tool_mutants_at_the_described_check"]["mutants"]),
                    "variant_kills_the_deletion_of_the_described_check": (r["variant"] in xkills[d]) if d else None,
                    "described_check_fires_in_a_recorded_case_of_the_baseline": fires,
                    "described_check_fires_in_a_case_of_the_study":
                        rep["described_check_fires_in_a_case_of_the_study"],
                }
                first = len(vk) >= 1
                if not fires:
                    if d is None:
                        second_part = False
                        entry["second_part"] = "the deletion of the described check is not among the mutants"
                    else:
                        suite_kills = killed_by_suite[d]
                        with_variant = suite_kills or r["variant"] in xkills[d]
                        entry["whole_suite_kills_the_deletion"] = suite_kills
                        entry["suite_with_the_variant_kills_the_deletion"] = with_variant
                        second_part = (not suite_kills) and with_variant
                else:
                    second_part = True
                    entry["second_part"] = "not applicable: the described check fires in a case of the baseline"
                entry["holds_for_this_row"] = first and second_part
                m3_rows[key] = entry

        def status(units: int, ok: bool) -> str:
            return "not applicable" if units == 0 else ("held" if ok else "not held")

        m1_ok = any(v["unique_kills_of_its_test_at_the_deciding_check"] for v in m1_rows.values())
        m2_ok = all(not v["detected_under_O_C_at_the_described_and_not_at_the_deciding_check"]
                    for v in m2_rows.values())
        m3_ok = all(v["holds_for_this_row"] for v in m3_rows.values())
        return {
            "M1": {"rule": "at least 1 test that holds a shadowed case has a unique kill at the check "
                           "that decides the case", "rows": m1_rows, "units": len(m1_rows),
                   "rows_with_a_unique_kill": sorted(k for k, v in m1_rows.items()
                                                     if v["unique_kills_of_its_test_at_the_deciding_check"]),
                   "status": status(len(m1_rows), m1_ok)},
            "M2": {"rule": "no shadowed case detects, under O_C, a mutant at the check it describes and not "
                           "at the check that decides it", "rows": m2_rows, "units": len(m2_rows),
                   "rows_with_such_a_detection": sorted(
                       k for k, v in m2_rows.items()
                       if v["detected_under_O_C_at_the_described_and_not_at_the_deciding_check"]),
                   "status": status(len(m2_rows), m2_ok)},
            "M3": {"rule": "each variant kills at least 1 mutant at the described check; where that check "
                           "fires in no case of the baseline, the whole suite does not kill its deletion and "
                           "the suite with the variant does", "rows": m3_rows, "units": len(m3_rows),
                   "rows_where_it_does_not_hold": sorted(k for k, v in m3_rows.items()
                                                         if not v["holds_for_this_row"]),
                   "status": status(len(m3_rows), m3_ok)},
        }

    exp = expectations(shadowed_rows, rep_shadowed)
    exp_other = expectations(other_rows, rep_other) if other_rows else None

    # -- input checks: baselines, deletions against the toolkit's deposit
    def strip(x):
        return second.strip_messages(x)

    deposited_whole = load_json(rec_root / "whole" / "base.json", "deposited whole/base.json")
    tk = second.compute(subject_path, rec_root)
    tk_del = tk["Q2"]["per_deletion"]
    del_compare = {}
    for cid, info in sorted(tk_del.items()):
        m = deletion_of.get(cid)
        if m is None:
            continue
        mine = per_mutant[m]
        here = mine["detected"]
        there = info["detected"]
        diffs = {}
        if here is None:
            diffs["recorder"] = "no value here"
        else:
            for o in MUTANT_ORACLES:
                if bool(here[o]) != bool(there[o]):
                    diffs[o] = {"here": here[o], "toolkit": there[o]}
            for o in ORACLES:
                if bool(mine["detected_withheld_as_failing"][o]) != bool(info["detected_withheld_as_failing"][o]):
                    diffs[f"{o}_withheld_as_failing"] = {"here": mine["detected_withheld_as_failing"][o],
                                                         "toolkit": info["detected_withheld_as_failing"][o]}
        if bool(killed_by_suite[m]) != bool(info["whole_suite_detected"]):
            diffs["whole_suite"] = {"here": killed_by_suite[m], "toolkit": info["whole_suite_detected"]}
        del_compare[cid] = {"deletion": m, "differences": diffs}
    input_checks = {
        "files_of_the_clone_equal_checks_json": digests_ok,
        "changed_lines_differ_from_mutants_csv": changed_mismatch,
        "modified_files_with_another_digest": digest_mismatch,
        "modified_files_with_another_number_of_lines": length_mismatch,
        "mutants_without_a_modified_file": sorted(m for m in ids if manifest[m].get("path") is None),
        "deletions_that_change_lines_outside_the_raise_statements_of_their_check": deletion_not_at_own_raises,
        "guards_that_differ_from_checks_json": guard_problems,
        "lost_tests_that_do_not_pass_in_both_unmodified_runs": lost_not_passing,
        "deposited_base_1_equals_base_1_of_the_mutant_runs_messages_aside": strip(base1) == strip(local_base1),
        "base_1_equals_base_2_of_the_mutant_runs_messages_aside": strip(local_base1) == strip(local_base2),
        "deposited_whole_suite_passing_equals_that_of_the_mutant_runs":
            sorted(deposited_whole.get("passing", [])) == sorted(passing_whole),
        "mutants_by_recorder_status": dict(sorted(Counter(runs[m]["recorder"]["status"] for m in ids).items())),
        "mutants_by_whole_suite_status": dict(sorted(Counter(whole_status[m] for m in ids).items())),
        "mutants_by_extra_status": dict(sorted(Counter(runs[m]["extra"][digest]["status"] for m in ids).items()))
        if digest else None,
        "repeated_recorder_runs": sorted(m for m in ids if (runs[m]["recorder"].get("runs") or 1) > 1),
        "repeated_whole_suite_runs": sorted(m for m in ids if (runs[m]["whole"].get("runs") or 1) > 1),
        "deletions_compared_with_the_toolkit_deposit": del_compare,
        "deletions_that_differ_from_the_toolkit_deposit": sorted(k for k, v in del_compare.items() if v["differences"]),
        "extra_tests_unstable_at_baseline": sorted(extra_base.get("unstable", [])) if extra_base else None,
    }

    cases_file = {
        "shadowed_rows": [{k: r[k] for k in ("case", "described", "kind", "variant")} for r in shadowed_rows],
        "rows_of_other_kinds": [{k: r[k] for k in ("case", "described", "kind", "variant")} for r in other_rows],
        "comparison_cases_of_the_file": file_comp,
        "comparison_rows_of_the_file_whose_described_check_is_the_target": file_comp_described_ok,
        "comparison_cases_derived": derived,
        "comparison_cases_derived_count": len(derived),
        "derived_equals_the_file": derived == file_comp,
        "only_derived": sorted(set(derived) - set(file_comp)),
        "only_in_the_file": sorted(set(file_comp) - set(derived)),
        "derived_cases_that_are_cases_of_rows_of_other_kinds": sorted(set(derived) & {r["case"] for r in other_rows}),
    }

    counts = {
        "tool_mutants": len(tool_ids), "deletions": len(del_ids),
        "tool_mutants_by_file": dict(sorted(Counter(manifest[m]["file"] for m in tool_ids).items())),
        "deletions_by_file": dict(sorted(Counter(manifest[m]["file"] for m in del_ids).items())),
        "tool_mutants_by_operator": dict(sorted(Counter(csv_rows[m]["operator"] for m in tool_ids).items())),
        "tool_mutants_at_least_1_check": sum(1 for m in tool_ids if at[m]),
        "cases_of_the_study": len(study), "recorded_executions_of_included_blocks": len(base_cases),
        "mutant_level_detection_tool_mutants": {
            o: sum(1 for m in tool_ids if per_mutant[m]["detected"] and per_mutant[m]["detected"][o])
            for o in MUTANT_ORACLES},
        "mutant_level_detection_deletions": {
            o: sum(1 for m in del_ids if per_mutant[m]["detected"] and per_mutant[m]["detected"][o])
            for o in MUTANT_ORACLES},
        "mutants_without_a_recorder_value": sorted(m for m in ids if per_mutant[m]["detected"] is None),
    }

    return {
        "subject": name, "version": subject.get("version"),
        "protocol": "PROTOCOL.md of target-reach-followup, sections 2 and 4.3",
        "arguments": {"subject": args.subject, "work": args.work, "mutants": args.mutants, "clone": args.clone,
                      "cases": args.cases, "extra_tests": args.extra_tests, "records": str(records_arg),
                      "without_tests": args.without_tests or [], "replace": args.replace or []},
        "input_sha256": {"mutants_csv": file_sha256(mpath), "cases": file_sha256(cpath),
                         "manifest": file_sha256(work / "manifest.json"),
                         "checks_json": file_sha256(defs / "checks.json"),
                         "targets_json": file_sha256(defs / "targets.json"),
                         "records": file_sha256(records_arg) if records_arg.is_file() else None},
        "readings": READINGS,
        "counts": counts,
        "per_mutant": per_mutant,
        "checks": checks_out,
        "tests": tests_out,
        "extra_tests": extra_out,
        "cases_file": cases_file,
        "rows": {"shadowed": rep_shadowed, "comparison": rep_comparison, "other_kinds": rep_other},
        "library": library,
        "expectations": exp,
        "expectations_over_rows_of_other_kinds": exp_other,
        "input_checks": input_checks,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--mutants", required=True)
    ap.add_argument("--clone", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--extra-tests")
    ap.add_argument("--without-tests", nargs="*", default=[])
    ap.add_argument("--replace", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--records")
    ap.add_argument("--toolkit-second", default=str(DEFAULT_SECOND))
    a = ap.parse_args(argv)
    try:
        second = load_second(Path(a.toolkit_second))
        data = compute(a, second)
    except InputError as e:
        print(f"second_mutants: {e}", file=sys.stderr)
        return 2
    except SystemExit as e:         # raised by a helper of the toolkit's second.py
        print(f"second_mutants: {e}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, ValueError, SyntaxError) as e:
        print(f"second_mutants: malformed input: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    lib = data["library"]["tool_mutants"]
    e = data["expectations"]
    print(f"{data['subject']}: {data['counts']['tool_mutants']} tool mutants, {data['counts']['deletions']} "
          f"deletions; whole suite kills {lib['killed_by_the_whole_suite']['count']} tool mutants and "
          f"{data['library']['deletions']['killed_by_the_whole_suite']['count']} deletions; "
          f"{len(data['cases_file']['shadowed_rows'])} shadowed rows, "
          f"{data['cases_file']['comparison_cases_derived_count']} comparison cases; "
          f"M1 {e['M1']['status']}, M2 {e['M2']['status']}, M3 {e['M3']['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

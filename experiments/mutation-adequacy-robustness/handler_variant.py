"""Analysis D of PROTOCOL.md: a second way to delete a check that sits in a handler.

    python3 -I handler_variant.py

Reuses the machinery of the second study (../mutation-adequacy-pyjwt/)
read-only: its clone work/pyjwt, its virtual environment work/venv, its
recorder plugin/s2_recorder.py, its checks.json and cases.json, the copy,
deletion and recorder-run functions of run_s2.py and the case, state and
oracle functions of analyse_s2.py (both imported by file location, with
bytecode writing switched off so that nothing is written into that folder).

Steps:

1. verify: the clone is at the fixed commit and clean, the subject and test
   files match their SHA-256, Python and the installed packages are as
   recorded (run_s2.py's verify, re-implemented without any write: git runs
   with --no-optional-locks and Python with -B).
2. Handler checks: the reached checks with at least one raise statement
   lexically inside an `except` handler, derived from the unmodified source.
3. Runs, each on a fresh copy of jwt/, tests/ and pyproject.toml under
   work/: 1 control copy; per handler check one copy under the original
   variant (every raise statement of the check becomes `pass`) and one under
   variant R (a raise statement in a handler becomes a bare `raise`, any
   other raise statement of the check becomes `pass`).
4. Sentinels: the control gives the study's baseline record apart from
   timing; the original variant reproduces the oracle results of the
   deposited generated/deletions.csv for every handler check.
5. Results: generated/handler-variant.csv, handler-variant-cases.csv,
   handler-variant.json and handler-variant.md.

Raise sites under variant R are mapped by line number against the unmodified
source; every mapped site is checked against the recorder's own numbering by
raise count, and the script stops if the two disagree.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # importing the study's scripts must not write __pycache__ there

import ast
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent / "mutation-adequacy-pyjwt"
WORK = HERE / "work"
GENERATED = HERE / "generated"
VARIANTS = ("original", "R")
WORKERS = 10


def import_file(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = import_file("run_s2", STUDY / "run_s2.py")
A = import_file("analyse_s2", STUDY / "analyse_s2.py")
ORACLES = A.ORACLES  # O_V, O_V_fc, O_C, O_T, O_S
NAMES = A.NAMES


def fail(message: str) -> None:
    raise SystemExit(f"handler_variant: SENTINEL FAILED: {message}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def yn(value: bool) -> str:
    return "yes" if value else "no"


# -- 1. verify ----------------------------------------------------------------

def verify() -> dict:
    """run_s2.verify, with the same checks, made write-free."""
    checks, cases = load(R.CHECKS), load(R.CASES)
    commit = checks["subject"]["commit"]
    git = ["git", "--no-optional-locks", "-C", str(R.SUBJECT)]
    head = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    dirty = subprocess.run(git + ["status", "--porcelain"], capture_output=True, text=True,
                           check=True).stdout.strip()
    problems = []
    if head != commit:
        problems.append(f"clone is at {head}, not {commit}")
    if dirty:
        problems.append(f"clone has changes: {dirty[:200]}")
    for rel, digest in checks["subject"]["sha256"].items():
        if R.sha256(R.SUBJECT / rel) != digest:
            problems.append(f"{rel}: SHA-256 differs")
    for name, digest in cases["test_files_sha256"].items():
        if R.sha256(R.SUBJECT / "tests" / name) != digest:
            problems.append(f"tests/{name}: SHA-256 differs")
    version = subprocess.run([str(R.PY), "-I", "-B", "-c", "import sys; print(sys.version.split()[0])"],
                             capture_output=True, text=True, check=True).stdout.strip()
    if version != R.PYTHON_VERSION:
        problems.append(f"Python {version}, not {R.PYTHON_VERSION}")
    freeze = subprocess.run([str(R.PY), "-I", "-B", "-m", "pip", "freeze"], capture_output=True,
                            text=True, check=True, env=R.clean_env()).stdout.split()
    fixed = (R.WORK / "pip-freeze.txt").read_text(encoding="utf-8").split()
    if sorted(freeze) != sorted(fixed):
        problems.append(f"venv differs from pip-freeze.txt: {sorted(set(freeze) ^ set(fixed))}")
    importable = subprocess.run([str(R.PY), "-I", "-B", "-c",
                                 "import importlib.util as u; print(u.find_spec('jwt') is None)"],
                                capture_output=True, text=True, check=True, cwd="/",
                                env=R.clean_env()).stdout.strip()
    if importable != "True":
        problems.append("a jwt package is importable from the venv itself")
    if problems:
        fail("verify failed:\n  " + "\n  ".join(problems))
    return {"commit": commit, "clean": True, "subject_files_match": len(checks["subject"]["sha256"]),
            "test_files_match": len(cases["test_files_sha256"]), "python": version,
            "pinned_packages_match": len(fixed), "jwt_not_installed": True}


# -- 2. handler checks ----------------------------------------------------------

def unmodified_source(rel: str) -> str:
    return (R.SUBJECT / rel).read_text(encoding="utf-8")


def raises_in_handler(source: str, function: str) -> list[int]:
    """Ordinals (run_s2's numbering) of the raise statements of `function`
    that sit lexically inside an `except` handler of that function."""
    fn = R.functions(ast.parse(source))[function]
    inside: set[int] = set()

    def visit(node: ast.AST, in_handler: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            here = in_handler or isinstance(child, ast.ExceptHandler)
            if isinstance(child, ast.Raise) and here:
                inside.add(id(child))
            visit(child, here)

    visit(fn, False)
    return [k for k, node in enumerate(R.raise_nodes(fn)) if id(node) in inside]


# -- 3. variant R -----------------------------------------------------------------

def reraise_variant(source: str, function: str, ordinals: list[int], in_handler: list[int]) -> tuple[str, list[dict]]:
    """Variant R: each listed raise statement in a handler becomes a bare
    `raise`, each other listed raise statement becomes `pass`; continuation
    lines become empty, so every line keeps its number (as run_s2.delete_raises)."""
    tree = ast.parse(source)
    fn = R.functions(tree)[function]
    raises = R.raise_nodes(fn)
    lines = [line.encode("utf-8") for line in source.splitlines(keepends=True)]
    changed = []
    for k in sorted(ordinals, reverse=True):
        node = raises[k]
        new = b"raise" if k in in_handler else b"pass"
        first, last = node.lineno - 1, node.end_lineno - 1
        prefix = lines[first][:node.col_offset]
        suffix = lines[last][node.end_col_offset:]
        if prefix.strip():
            raise SystemExit(f"{function} raise {k}: does not start its line")
        if suffix.strip() and not suffix.strip().startswith(b"#"):
            raise SystemExit(f"{function} raise {k}: shares its last line with other code")
        removed = b"".join(lines[first:last + 1]).decode("utf-8")
        if first == last:
            lines[first] = prefix + new + suffix
        else:
            lines[first] = prefix + new + b"\n"
            for i in range(first + 1, last):
                lines[i] = b"\n"
            lines[last] = suffix if suffix.strip() else b"\n"
        changed.append({"raise": k, "lines": [node.lineno, node.end_lineno], "removed": removed,
                        "replacement": new.decode()})
    out = b"".join(lines).decode("utf-8")
    new_tree = ast.parse(out)
    compile(out, function, "exec")
    if len(out.splitlines()) != len(source.splitlines()):
        raise SystemExit(f"{function}: variant R changed the line count")
    passed = [k for k in ordinals if k not in in_handler]
    left = R.raise_nodes(R.functions(new_tree)[function])
    kept = [k for k in range(len(raises)) if k not in passed]
    if len(left) != len(kept):
        raise SystemExit(f"{function}: {len(left)} raises left, expected {len(kept)}")
    for node, k in zip(left, kept):
        if node.lineno != raises[k].lineno:
            raise SystemExit(f"{function}: raise {k} moved from line {raises[k].lineno} to {node.lineno}")
        if k in ordinals and (node.exc is not None or node.cause is not None):
            raise SystemExit(f"{function}: raise {k} is not a bare raise")
    for name, node in R.functions(tree).items():
        if name != function and ast.dump(node) != ast.dump(R.functions(new_tree)[name]):
            raise SystemExit(f"{function}: variant R also changed {name}")
    return out, sorted(changed, key=lambda c: c["raise"])


def build_copy(variant: str, check: dict | None, in_handler: list[int]) -> tuple[Path, dict | None]:
    name = "_control" if check is None else check["id"]
    dest = WORK / "copies" / variant / name
    R.make_copy(dest)  # fresh copy, SHA-256 of the subject files checked against the clone
    if check is None:
        return dest, None
    target = dest / check["file"]
    source = target.read_text(encoding="utf-8")
    if variant == "original":
        new, changed = R.delete_raises(source, check["function"], check["raises"])
    else:
        new, changed = reraise_variant(source, check["function"], check["raises"], in_handler)
    target.write_text(new, encoding="utf-8")
    info = {"check": check["id"], "variant": variant, "file": check["file"], "function": check["function"],
            "raises": changed, "sha256_before": hashlib.sha256(source.encode()).hexdigest(),
            "sha256_after": R.sha256(target)}
    R.dump(dest / "deletion.json", info)
    return dest, info


# -- raise sites by line number ------------------------------------------------------

class LineIndex:
    """Raise statements of every function of the unmodified package, by line."""

    def __init__(self) -> None:
        self._fns: dict[str, dict[str, list[ast.Raise]]] = {}

    def raises(self, rel: str, function: str) -> list[ast.Raise] | None:
        if rel not in self._fns:
            path = R.SUBJECT / rel
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                self._fns[rel] = {}
            else:
                self._fns[rel] = {n: R.raise_nodes(f) for n, f in R.functions(tree).items()}
        found = self._fns[rel].get(function)
        return found

    def ordinal(self, rel: str, function: str, line: int) -> tuple[bool, int | None]:
        """(function found, ordinal of the unmodified raise statement whose lines hold `line`)."""
        raises = self.raises(rel, function)
        if raises is None:
            return False, None
        hits = [k for k, node in enumerate(raises) if node.lineno <= line <= node.end_lineno]
        if len(hits) > 1:
            raise SystemExit(f"line {line} of {function} lies in {len(hits)} raise statements")
        return True, (hits[0] if hits else None)


INDEX = LineIndex()
SEGMENT_OF = {v: k for k, v in R.load(R.CHECKS)["segment_calls"].items()}


def segment_for(check: str | None, frames: list[dict]) -> str | None:
    """As the recorder and analyse_s2.renumber_after_deletion do."""
    if check == "jws.segment-encoding" and len(frames) > 1:
        outer = frames[-2]
        if (outer["function"] == "PyJWS._load" and outer["kind"] == "call"
                and outer["callee"] == "_decode_base64url_segment"):
            return SEGMENT_OF.get(outer["ordinal"])
    return None


def map_by_line(record: dict, info: dict | None) -> dict:
    """Map every raise site of an included block to a check by the line number
    of its innermost frame in the unmodified source, and check it against the
    recorder's numbering by raise count: the recorder's ordinal, translated
    through the raise statements that the copy still holds, must name the same
    unmodified raise statement. Sets site.check and site.segment to the
    line-based mapping. Returns counts."""
    where = (info["file"], info["function"]) if info else None
    passed = [c["raise"] for c in info["raises"] if c.get("replacement", "pass") == "pass"] if info else []
    counts = Counter()
    for rec in record["blocks"]:
        site = rec.get("site")
        if not rec["included"] or not site or not site["frames"]:
            continue
        inner = site["frames"][-1]
        found, k_line = INDEX.ordinal(inner["file"], inner["function"], inner["line"])
        if inner["kind"] == "raise":
            k_rec = inner["ordinal"]
            if (inner["file"], inner["function"]) == where:
                n = len(INDEX.raises(*where))
                kept = [k for k in range(n) if k not in passed]
                k_rec = kept[k_rec]
            if found and k_line != k_rec:
                fail(f"raise site {inner} maps by line to raise {k_line} and by raise count to {k_rec}")
            if not found and A.CHECK_AT.get((inner["file"], inner["function"], k_rec)) is not None:
                fail(f"raise site {inner} is a check's raise statement but its function is not in the source")
        elif found and k_line is not None:
            fail(f"site {inner} lies in an unmodified raise statement but the recorder did not see a raise")
        check = A.CHECK_AT.get((inner["file"], inner["function"], k_line)) if k_line is not None else None
        segment = segment_for(check, site["frames"])
        counts["sites"] += 1
        counts["raise_sites"] += inner["kind"] == "raise"
        if (check, segment) != (site["check"], site["segment"]):
            counts["remapped"] += 1
            site["recorded_check"], site["recorded_segment"] = site["check"], site["segment"]
            site["check"], site["segment"] = check, segment
        else:
            counts["recorder_numbering_same_check"] += inner["kind"] == "raise"
    return dict(counts)


# -- runs ------------------------------------------------------------------------------

def run_all(jobs: list[tuple[str, str, Path]], timeout: float) -> dict[tuple[str, str], dict]:
    def one(job):
        variant, name, cwd = job
        out = WORK / "records" / variant / f"{name}.json"
        return (variant, name), R.recorder_run(f"{variant}/{name}", cwd, out, timeout)

    with ThreadPoolExecutor(WORKERS) as pool:
        results = dict(pool.map(one, jobs))
    log = WORK / "records" / "runs.jsonl"
    log.write_text("".join(json.dumps(results[k], ensure_ascii=False) + "\n" for k in sorted(results)),
                   encoding="utf-8")
    for key, entry in sorted(results.items()):
        if entry["timed_out"] or not entry["record"]:
            print("  run", "/".join(key), "timed out" if entry["timed_out"] else "wrote no record", flush=True)
    return results


def changed_cases(state: dict, cases: dict) -> list[tuple[str, str, dict]]:
    """analyse_s2's rule for a case that changed: not observed, or its class,
    raise site, segment, message or pytest's check differs from the baseline."""
    out = []
    for cid, case in cases.items():
        kind, rec = state["cases"].get(cid, (state["state"], None))
        rec = rec or {}
        site = rec.get("site") or {}
        if (kind != "observed" or rec.get("class") != case["B"] or site.get("check") != case["site"]
                or site.get("segment") != case["site_segment"] or rec.get("message") != case["message"]
                or rec.get("real") != "ok"):
            out.append((cid, kind, rec))
    return sorted(out, key=lambda t: t[0])


def class_label(kind: str, rec: dict) -> str:
    if kind != "observed":
        return kind
    return rec.get("class") if rec.get("outcome") == "raised" else "no exception"


def fmt_counter(counter: Counter) -> str:
    return "; ".join(f"{k} {v}" for k, v in sorted(counter.items()))


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    with (GENERATED / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    print("handler_variant: verify", flush=True)
    verified = verify()
    checks = R.load(R.CHECKS)
    timeout = load(R.RECORDS / "baseline" / "timeout.json")["timeout_seconds"]

    # the study's baseline: cases, applicable sets, reached checks
    base = load(R.RECORDS / "baseline" / "base-1.json")
    cases = A.baseline_cases(base)
    base_state = A.run_state(R.RECORDS / "baseline" / "base-1.json", None, cases)
    s = {o: {cid for cid, (kind, rec) in base_state["cases"].items()
             if kind == "observed" and A.holds(o, cases[cid], rec)} for o in ORACLES}
    reached = defaultdict(list)
    for cid, c in cases.items():
        if c["site"]:
            reached[c["site"]].append(cid)
    mutated = [c for c in checks["checks"] if c["mutated"]]
    reached_checks = sorted(c["id"] for c in mutated if c["id"] in reached)

    deposited = {r["check"]: r for r in csv.DictReader(
        (STUDY / "generated" / "deletions.csv").open(encoding="utf-8"))}
    deposited_cases = defaultdict(list)
    for r in csv.DictReader((STUDY / "generated" / "deletion-cases.csv").open(encoding="utf-8")):
        deposited_cases[r["check"]].append(r)
    if sorted(d for d, r in deposited.items() if r["reached"] == "yes") != reached_checks:
        fail("the reached checks derived from the baseline differ from the deposited deletions.csv")

    handler = {}
    for c in mutated:
        if c["id"] not in reached:
            continue
        inside = [k for k in raises_in_handler(unmodified_source(c["file"]), c["function"]) if k in c["raises"]]
        if inside:
            handler[c["id"]] = inside
    handler_ids = sorted(handler, key=lambda d: [x["id"] for x in mutated].index(d))
    by_id = {c["id"]: c for c in mutated}
    print(f"handler_variant: {len(reached_checks)} reached checks, {len(handler_ids)} handler checks:",
          ", ".join(handler_ids), flush=True)

    # build copies and run
    if (WORK / "copies").exists():
        shutil.rmtree(WORK / "copies")
    if (WORK / "records").exists():
        shutil.rmtree(WORK / "records")
    jobs, infos = [], {}
    dest, _ = build_copy("control", None, [])
    jobs.append(("control", "_control", dest))
    for d in handler_ids:
        for variant in VARIANTS:
            dest, info = build_copy(variant, by_id[d], handler[d])
            infos[(variant, d)] = info
            jobs.append((variant, d, dest))
    print(f"handler_variant: {len(jobs)} recorder runs, timeout {timeout} s", flush=True)
    entries = run_all(jobs, timeout)

    # sentinel 1: control equals the study's baseline record apart from timing
    control_path = WORK / "records" / "control" / "_control.json"
    if not control_path.exists():
        fail("the control run wrote no record")
    sentinel_control = A.normalise(load(control_path)) == A.normalise(base)
    if not sentinel_control:
        fail("the control copy does not reproduce the study's baseline record (apart from timing)")

    # evaluate each run
    results = {}
    for d in handler_ids:
        for variant in VARIANTS:
            path = WORK / "records" / variant / f"{d}.json"
            entry = entries[(variant, d)]
            if variant == "original":
                # the study's own mapping (deviation 6 of its protocol) ...
                state = A.run_state(path, entry, cases, deleted=by_id[d])
                # ... cross-checked against the line mapping
                if state["state"] == "ran":
                    check_record = load(path)
                    line_counts = map_by_line(check_record, infos[(variant, d)])
                    for rec in check_record["blocks"]:
                        if rec["included"]:
                            cid = A.case_id(rec)
                            kind, mine = state["cases"][cid]
                            a = (mine.get("site") or {}) if mine else {}
                            b = rec.get("site") or {}
                            if (a.get("check"), a.get("segment")) != (b.get("check"), b.get("segment")):
                                fail(f"{d}, original variant: line mapping and renumbering disagree on {cid}")
                else:
                    line_counts = {}
                remapped = state.get("renumbered", 0)
            else:
                state = A.run_state(path, entry, cases)  # no renumbering by the study's rule
                line_counts = map_by_line(state["record"], infos[(variant, d)]) if state["state"] == "ran" else {}
                remapped = line_counts.get("remapped", 0)
            verdict = A.evaluate(state, s, cases, oracles=ORACLES)
            results[(variant, d)] = {"state": state, "verdict": verdict, "moves": A.moves(state, cases),
                                     "changed": changed_cases(state, cases), "remapped": remapped,
                                     "line_counts": line_counts}

    # sentinel 2: the original variant re-run reproduces the deposited oracle results
    sentinel_rerun = {}
    for d in handler_ids:
        got = {NAMES[o]: yn(results[("original", d)]["verdict"][o]["killed"]) for o in ORACLES}
        want = {NAMES[o]: deposited[d][NAMES[o]] for o in ORACLES}
        sentinel_rerun[d] = got == want
        if got != want:
            fail(f"{d}: the original variant re-run gives {got}, the deposited deletions.csv {want}")
    # additional comparison, reported: cases changed and the classes of the changed cases
    rerun_extra = {}
    for d in handler_ids:
        r = results[("original", d)]
        rerun_classes = Counter(class_label(k, rec) for _, k, rec in r["changed"])
        dep_classes = Counter(row["class"] if row["status"] == "observed" and row["class"] else
                              ("no exception" if row["status"] == "observed" else row["status"])
                              for row in deposited_cases[d])
        rerun_extra[d] = {"cases_changed_same": len(r["changed"]) == int(deposited[d]["cases_changed"]),
                          "changed_case_ids_same": [c for c, _, _ in r["changed"]]
                          == sorted(row["case"] for row in deposited_cases[d]),
                          "changed_classes_same": rerun_classes == dep_classes,
                          "sites_renumbered_same": r["remapped"] == int(deposited[d]["sites_renumbered"])}

    # rows
    rows, case_rows = [], []
    summary_checks = {}
    for d in handler_ids:
        c = by_id[d]
        dep = deposited[d]
        dep_classes = Counter(row["class"] if row["status"] == "observed" and row["class"] else
                              ("no exception" if row["status"] == "observed" else row["status"])
                              for row in deposited_cases[d])
        common = {"check": d, "file": c["file"], "function": c["function"], "class": c["class"],
                  "raise_statements": len(c["raises"]), "raises_in_handler": len(handler[d]),
                  "baseline_cases_reaching": len(reached[d])}
        original = {**common, "variant": "original", "source": "deposited deletions.csv",
                    **{NAMES[o]: dep[NAMES[o]] for o in ORACLES},
                    "cases_changed": int(dep["cases_changed"]), "changed_case_classes": fmt_counter(dep_classes),
                    "moves": dep["moves"], "sites_remapped": int(dep["sites_renumbered"])}
        r = results[("R", d)]
        r_classes = Counter(class_label(k, rec) for _, k, rec in r["changed"])
        variant_r = {**common, "variant": "R", "source": "this run",
                     **{NAMES[o]: yn(r["verdict"][o]["killed"]) for o in ORACLES},
                     "cases_changed": len(r["changed"]), "changed_case_classes": fmt_counter(r_classes),
                     "moves": "; ".join(f"{k} {v}" for k, v in sorted(r["moves"].items()) if k != "same"),
                     "sites_remapped": r["remapped"]}
        rows += [original, variant_r]
        summary_checks[d] = {
            "function": c["function"], "class": c["class"], "raises": c["raises"], "raises_in_handler": handler[d],
            "baseline_cases_reaching": len(reached[d]),
            "original": {k: original[k] for k in ("O_V", "O_V^fc", "O_C", "O_T", "O_S", "cases_changed")}
            | {"changed_case_classes": dict(sorted(dep_classes.items()))},
            "R": {k: variant_r[k] for k in ("O_V", "O_V^fc", "O_C", "O_T", "O_S", "cases_changed")}
            | {"changed_case_classes": dict(sorted(r_classes.items())), "run": r["state"]["state"],
               "line_mapping": r["line_counts"]},
        }
        for cid, kind, rec in r["changed"]:
            case = cases[cid]
            site = rec.get("site") or {}
            case_rows.append({
                "check": d, "case": cid, "status": kind,
                "baseline_class": case["B"], "baseline_site": case["site"],
                "baseline_segment": case["site_segment"],
                "class": rec.get("class") if kind == "observed" and rec.get("outcome") == "raised" else
                ("no exception" if kind == "observed" else None),
                "site": site.get("check"), "segment": site.get("segment"),
                "message": rec.get("message"),
                **{NAMES[o]: (yn(A.holds(o, case, rec)) if kind == "observed" else kind) for o in ORACLES},
            })

    # the 41 reached checks together: handler checks by variant R, the others as deposited
    combined = {}
    for o in ORACLES:
        undetected_dep = sorted(d for d in reached_checks if deposited[d][NAMES[o]] == "no")
        undetected_mix = sorted(
            [d for d in reached_checks if d not in handler and deposited[d][NAMES[o]] == "no"]
            + [d for d in handler_ids if not results[("R", d)]["verdict"][o]["killed"]])
        combined[NAMES[o]] = {"undetected_original": len(undetected_dep),
                              "undetected_with_R": len(undetected_mix),
                              "checks_with_R": undetected_mix}
    fc_only = sorted(d for d in reached_checks
                     if deposited[d]["O_V"] == "yes" and deposited[d]["O_V^fc"] == "no")
    fc_only_handler = [d for d in fc_only if d in handler]

    fields = ["check", "variant", "source", "file", "function", "class", "raise_statements", "raises_in_handler",
              "baseline_cases_reaching", "O_V", "O_V^fc", "O_C", "O_T", "O_S", "cases_changed",
              "changed_case_classes", "moves", "sites_remapped"]
    GENERATED.mkdir(exist_ok=True)
    rows.sort(key=lambda r: (r["check"], VARIANTS.index(r["variant"])))
    write_csv("handler-variant.csv", rows, fields)
    case_rows.sort(key=lambda r: (r["check"], r["case"]))
    write_csv("handler-variant-cases.csv", case_rows,
              ["check", "case", "status", "baseline_class", "baseline_site", "baseline_segment",
               "class", "site", "segment", "message", "O_V", "O_V^fc", "O_C", "O_T", "O_S"])

    summary = {
        "schema": "urn:eatf:experiment:mutation-adequacy-robustness-handler-variant:1",
        "analysis": "D",
        "verify": verified,
        "runs": {"recorder_runs": len(jobs), "timeout_seconds": timeout,
                 "states": dict(sorted(Counter(results[k]["state"]["state"] for k in results).items()))},
        "reached_checks": len(reached_checks),
        "handler_checks": {"count": len(handler_ids), "checks": handler_ids},
        "fail_closed_only_deletions": {"count": len(fc_only), "of_which_handler_checks": len(fc_only_handler),
                                       "checks": fc_only, "handler_checks": fc_only_handler},
        "site_mapping": ("variant R: the innermost frame's line mapped to the raise statement of the unmodified "
                         "source whose lines hold it; every raise site checked against the recorder's ordinal "
                         "translated through the raise statements the copy keeps; original variant: the study's "
                         "renumbering, cross-checked against the line mapping"),
        "sentinels": {
            "control_reproduces_baseline": sentinel_control,
            "original_variant_reproduces_deposited_oracles": dict(sorted(sentinel_rerun.items())),
        },
        "rerun_additional_comparison": dict(sorted(rerun_extra.items())),
        "checks": dict(sorted(summary_checks.items())),
        "reached_checks_together": combined,
    }
    (GENERATED / "handler-variant.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")
    (GENERATED / "handler-variant.md").write_text(render(summary, rows), encoding="utf-8")
    print(render(summary, rows))
    return 0


def render(summary: dict, rows: list[dict]) -> str:
    h = summary["handler_checks"]
    f = summary["fail_closed_only_deletions"]
    comb = summary["reached_checks_together"]
    sen = summary["sentinels"]
    out = [
        "# Analysis D: a second way to delete a check that sits in a handler", "",
        "Generated by `handler_variant.py`; exploratory and post hoc (PROTOCOL.md, D).", "",
        f"Of the {summary['reached_checks']} reached checks of the second study, {h['count']} have at least one "
        f"raise statement lexically inside an `except` handler: {', '.join(h['checks'])}.", "",
        f"Of the {f['count']} deletions of reached checks that O_V detects and O_V^fc does not, "
        f"{f['of_which_handler_checks']} are handler checks.", "",
        "Variant R replaces each raise statement of the check that sits in a handler by a bare `raise` and any "
        "other raise statement of the check by `pass`. The original variant replaces every raise statement of "
        "the check by `pass`; its row is taken from the deposited results.", "",
        "## Sentinels", "",
        f"- The control copy reproduces the study's baseline record apart from timing: "
        f"{yn(sen['control_reproduces_baseline'])}.",
        f"- The original variant, re-run on fresh copies, reproduces the deposited oracle results for every "
        f"handler check: {yn(all(sen['original_variant_reproduces_deposited_oracles'].values()))} "
        f"({sum(sen['original_variant_reproduces_deposited_oracles'].values())} of {h['count']}).",
        "", "## Handler checks", "",
        "| Check | Variant | O_V | O_V^fc | O_C | O_T | O_S | Cases changed | Classes of the changed cases |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(f"| {r['check']} | {r['variant']} | {r['O_V']} | {r['O_V^fc']} | {r['O_C']} | {r['O_T']} | "
                   f"{r['O_S']} | {r['cases_changed']} | {r['changed_case_classes']} |")
    out += ["", f"## The {summary['reached_checks']} reached checks together", "",
            "Deletions not detected, with every check deleted as in the study, and with the handler checks "
            "deleted by variant R and the others as in the study.", "",
            "| Oracle | Original | Handler checks by variant R |", "|---|---|---|"]
    for o, v in comb.items():
        out.append(f"| {o} | {v['undetected_original']} | {v['undetected_with_R']} |")
    out += ["", "## Raise sites", "", summary["site_mapping"] + ".", ""]
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())

"""Score the mutants of 1 subject per case and per test, as the toolkit scores a deletion copy.

    python3 -I -B mutants/analyse_mutants.py --subject NAME_OR_SUBJECT_JSON
        [--targets-file TSV] [--without-tests ID ... | @FILE]
        [--extra-tests DIR [--replace OLD=NEW ...]]
        [--work DIR] [--out DIR] [--clone DIR] [--deposited DIR]

Reads the definitions of the subject (checks.json, blocks.json, targets.json
beside subject.json), mutants.csv and materialize.json (written by
materialize.py), and the records of run_mutants.py under <work>. Writes into
<out> (default generated/mutants/<name>/): runs.jsonl.xz, cases.csv.xz,
per-case.csv, per-test.csv, oracles.csv, score.json and SHA256SUMS (which
also lists mutants.csv and materialize.json). runs.jsonl and cases.csv are
kept compressed (xz); score.json gives the digest of each text before
compression. Every output is sorted and holds no time. The program writes its
outputs and then exits 1 when a sentinel (S1 to S6, see README.md) does not
hold.

mutants.csv holds 2 kinds of mutant: the mutants of mutmut and the deletions
of checks (operator `check_deletion`). Every count of score.json outside its
section `check_deletions`, and every count of per-case.csv, is of the mutants
of mutmut; runs.jsonl, cases.csv and oracles.csv hold both kinds, and
per-test.csv counts the deletions in 2 columns of their own.

A unique kill: the tests of the whole suite that kill the mutant are 1 test.
A test that runs in several suite runs is 1 test (its kill counts for each of
its runs in per-test.csv).

The scoring reuses reach.analyse.Run (the status of a case: observed,
crashed, withheld, missing), reach.analyse.oracles (O_V, O_Vfc, O_C, O_T on
1 case), reach.study (the cases of the study) and reach.run.junit_outcomes.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import sys
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (DELETION, PACKED, REFERENCE, TOOLKIT, default_out, default_work, functions,  # noqa: E402
                    junit_key, load_json, local_settings, need_python_312, rel_to_source, span,
                    split_lines, subject_paths, write_packed)
from reach.analyse import Run, asserts_message, oracles, site_label  # noqa: E402
from reach.study import case_key, left_out_reason  # noqa: E402

CASE_ORACLES = ["O_V", "O_Vfc", "O_C", "O_T"]
ORACLES = CASE_ORACLES + ["O_S"]
STATUSES = ("completed", "timeout", "error")


def norm(record: dict) -> str:
    """A record without message texts (reach/analyse.py, sentinel 1)."""
    cases = [{k: v for k, v in c.items() if k != "message"} for c in record["cases"]]
    return json.dumps(dict(record, cases=cases), sort_keys=True)


def csv_text(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue()


def yn(v) -> str:
    return "" if v is None else ("yes" if v else "no")


def parse_lines(text: str) -> list[int]:
    out = []
    for part in filter(None, text.split(";")):
        a, _, z = part.partition("-")
        out += list(range(int(a), int(z or a) + 1))
    return out


# -- per case, per mutant ------------------------------------------------------------------------

def case_detection(rstatus: str, run: Run | None, base: Run, key: str, base_or: dict,
                   target: str | None) -> dict:
    """What 1 mutant does to 1 case of the study, by the rules the toolkit
    applies to a deletion copy (PROTOCOL.md of target-reach, section 4):

    observed  a case oracle detects when it holds at baseline and does not hold now
    crashed   detected under every oracle (O_T only for a case with a target)
    withheld  not detected; counted in the withheld-as-failing columns
    missing   not detected
    time limit  (the recorder run exceeded the limit 2 times) detected under every oracle
    no record   (the recorder run gave no record 2 times) no value
    O_S: the case's own test passes at baseline and does not pass in the run.
    """
    b = base.cases[key]
    test = b["test"]
    out = {"status": None, "withheld": {o: False for o in CASE_ORACLES}}
    if rstatus == "timeout":
        out["status"] = "time limit"
        out.update({o: True for o in ORACLES})
        if not target:
            out["O_T"] = None
        return out
    if rstatus != "completed":
        out["status"] = "no record"
        out.update({o: None for o in ORACLES})
        return out
    st = run.status(key, test)
    out["status"] = st
    if st == "observed":
        now = oracles(run.cases[key], b, target)
        for o in CASE_ORACLES:
            out[o] = None if base_or[o] is None else bool(base_or[o] and now[o] is False)
    elif st == "crashed":
        out.update({o: True for o in CASE_ORACLES})
        if not target:
            out["O_T"] = None
    else:
        for o in CASE_ORACLES:
            out[o] = None if base_or[o] is None else False
            if st == "withheld" and base_or[o]:
                out["withheld"][o] = True
    out["O_S"] = True if st == "crashed" else bool(base.passed(test) and not run.passed(test))
    return out


def mutant_detection(rstatus: str, run: Run | None, base: Run, keys: list[str], per_case: dict) -> dict:
    """The detection of 1 mutant over all cases, exactly as reach/analyse.py
    decides it for 1 deletion: a case oracle detects when it detects on an
    observed case; a crash of any case is a detection under every oracle;
    O_S when the test of any case passes at baseline and not in the run; the
    suite when any test of the recorder run does; a run that exceeded the
    limit 2 times is detected under every oracle and the suite."""
    if rstatus == "timeout":
        return {**{o: True for o in ORACLES}, "suite": True, "withheld": {o: True for o in CASE_ORACLES}}
    if rstatus != "completed":
        return {**{o: None for o in ORACLES}, "suite": None, "withheld": {o: None for o in CASE_ORACLES}}
    det = {o: False for o in ORACLES}
    withheld = {o: False for o in CASE_ORACLES}
    crashed = False
    for k in keys:
        d = per_case[k]
        if d["status"] == "observed":
            for o in CASE_ORACLES:
                det[o] = det[o] or bool(d[o])
        crashed = crashed or d["status"] == "crashed"
        for o in CASE_ORACLES:
            withheld[o] = withheld[o] or d["withheld"][o]
    case_tests = sorted({base.cases[k]["test"] for k in keys})
    det["O_S"] = any(base.passed(n) and not run.passed(n) for n in case_tests)
    if crashed:
        det = {o: True for o in ORACLES}
    suite = any(base.passed(n) and not run.passed(n) for n in base.tests)
    return {**det, "suite": suite, "withheld": {o: det[o] or withheld[o] for o in CASE_ORACLES}}


# -- the whole suite --------------------------------------------------------------------------------

def whole_killed(entry: dict) -> bool | None:
    """Killed by the whole suite: a test that passes in both unmodified runs does
    not pass on the mutant copy, or the run (repeated 1 time) exceeded the time
    limit or left no result file."""
    if entry["status"] in ("timeout", "error"):
        return True
    return bool(entry["lost"])


def score_counts(kill_sets: dict[str, set], status: dict[str, str]) -> dict:
    """kill_sets: mutant -> the tests that kill it (completed runs);
    status: mutant -> completed, timeout or error."""
    n = len(status)
    by_tests = sorted(m for m in status if status[m] == "completed" and kill_sets.get(m))
    timeouts = sorted(m for m in status if status[m] == "timeout")
    errors = sorted(m for m in status if status[m] == "error")
    killed = len(by_tests) + len(timeouts) + len(errors)
    return {"mutants": n, "killed": killed, "killed_by_a_test": len(by_tests), "timeouts": len(timeouts),
            "errors": len(errors), "survived": n - killed,
            "score": round(killed / n, 6) if n else None,
            "score_without_errors": round((killed - len(errors)) / (n - len(errors)), 6) if n - len(errors) else None,
            "timeout_mutants": timeouts, "error_mutants": errors}


# -- sentinels S1 and S3 ------------------------------------------------------------------------------

def recheck_files(rows: list[dict], work: Path, clone: Path, subject: dict, runs: dict) -> list[str]:
    """S1 again, from the files: each modified file has the digest of mutants.csv,
    the number of lines of the unmodified file, differs from it only inside the
    function's lines, and compiles; and its runs used that digest."""
    problems = []
    originals: dict[str, list[str]] = {}
    for r in rows:
        mid = r["mutant"]
        path = work / "mutated" / f"{mid}.py"
        if not path.exists():
            problems.append(f"{mid}: no modified file")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != r["sha256"]:
            problems.append(f"{mid}: the modified file is not the one of mutants.csv")
        if r["file"] not in originals:
            originals[r["file"]] = split_lines((clone / rel_to_source(subject, r["file"])).read_bytes().decode("utf-8"))
        old, new = originals[r["file"]], split_lines(data.decode("utf-8"))
        first, last = map(int, r["function_lines"].split("-"))
        if len(old) != len(new):
            problems.append(f"{mid}: the number of lines changed")
        else:
            changed = [i + 1 for i, (x, y) in enumerate(zip(old, new)) if x != y]
            if not changed:
                problems.append(f"{mid}: the modified file is the unmodified file")
            if any(not first <= x <= last for x in changed):
                problems.append(f"{mid}: a line outside the function changed")
        try:
            compile(data, r["file"], "exec", dont_inherit=True)
        except SyntaxError as e:
            problems.append(f"{mid}: does not compile ({e.msg})")
        run = runs.get(mid)
        if run is not None and run.get("sha256") != r["sha256"]:
            problems.append(f"{mid}: the runs used another modified file")
    return problems


def deletions_comparison(gen: Path, mine: dict[str, dict], with_target: bool) -> dict | None:
    """S6: each deletion mutant whose check the toolkit's deposited deletions.csv
    lists, against that row: the detection under each oracle and by the suite
    of the recorder run, the withheld-as-failing columns, the whole-suite
    status and the number of tests not passing. `mine`: check -> row of
    oracles.csv as a dict. None when the toolkit deposited no deletions.csv."""
    path = gen / "deletions.csv"
    if not path.exists() or not mine:
        return None
    with path.open(encoding="utf-8") as handle:
        theirs = {r["check"]: r for r in csv.DictReader(handle)}
    if not theirs:
        return None
    columns = [o for o in ORACLES if with_target or o != "O_T"] + ["suite"] + [
        f"{o} withheld-as-failing" for o in CASE_ORACLES if with_target or o != "O_T"]
    pairs = [(c, c) for c in columns] + [("whole_suite", "whole_suite_killed"),
                                         ("whole_suite_tests_not_passing", "whole_suite_tests_killing")]
    differ, compared, not_run = [], 0, []
    for cid in sorted(set(theirs) & set(mine)):
        if theirs[cid]["run"] != "ran":
            not_run.append(cid)
            continue
        compared += 1
        for a, b in pairs:
            if str(theirs[cid][a]) != str(mine[cid][b]):
                differ.append(f"{cid}: {a} is {theirs[cid][a]} in the toolkit's deletions.csv and {mine[cid][b]} here")
    return {"deposited": len(theirs), "deletions_here": len(mine), "compared": compared,
            "columns": [a for a, _ in pairs], "not_run_in_the_deposit": not_run,
            "deleted_here_only": sorted(set(mine) - set(theirs)), "differences": differ}


def deposited(gen: Path) -> tuple[list[dict] | None, dict | None]:
    """The toolkit's deposited cases.csv and whole-suite baseline of a subject:
    cases.csv, and records/whole/base.json inside records.tar.xz (or, for a
    folder that holds no archive, whole-base.json)."""
    cases = None
    if (gen / "cases.csv").exists():
        with (gen / "cases.csv").open(encoding="utf-8") as handle:
            cases = list(csv.DictReader(handle))
    whole = None
    if (gen / "records.tar.xz").exists():
        with tarfile.open(gen / "records.tar.xz") as tar:
            try:
                whole = json.load(tar.extractfile("records/whole/base.json"))
            except KeyError:
                whole = None
    elif (gen / "whole-base.json").exists():
        whole = load_json(gen / "whole-base.json")
    return cases, whole


# -- S5: the reference study's mutmut outcomes ---------------------------------------------------------

def reference_comparison(rows: list[dict], killed: dict[str, bool | None], runs: dict[str, dict],
                         run_names: list[str]) -> dict:
    """S5: the whole-suite status of each mutant against the mutmut status of the
    reference study. For each difference, the evidence of its cause: the status
    of both runs here, the tests that mutmut selected for the mutated function
    in its own stats run (mutmut runs only those, and a mutant without any is
    `no tests`, counted as survived), mutmut's exit code, and whether a test
    that kills the mutant here is among the selected tests."""
    path = REFERENCE / "generated" / "mutants.csv"
    with path.open(encoding="utf-8") as handle:
        ref = {r["key"]: r for r in csv.DictReader(handle)}
    stats_path = REFERENCE / "work" / "mutmut" / "mutants" / "mutmut-stats.json"
    selected = load_json(stats_path)["tests_by_mangled_function_name"] if stats_path.exists() else None
    exit_codes = {}
    for meta in sorted((REFERENCE / "work" / "mutmut" / "mutants").glob("**/*.meta")):
        exit_codes.update(load_json(meta).get("exit_code_by_key", {}))
    mine = {r["mutmut_name"]: r for r in rows}
    files = sorted({r["file"] for r in rows})
    ref_here = {k: v for k, v in ref.items() if v["file"] in files}
    only_mine, only_ref = sorted(set(mine) - set(ref_here)), sorted(set(ref_here) - set(mine))
    agree, differ = 0, []
    causes = Counter()
    for key in sorted(set(mine) & set(ref_here)):
        r = mine[key]
        m_killed = killed.get(r["mutant"])
        r_killed = ref_here[key]["tool_class"] == "killed"
        if m_killed is None:
            differ.append({"mutmut_name": key, "mutant": r["mutant"], "cause": "no whole-suite run here"})
            causes["no whole-suite run here"] += 1
            continue
        if m_killed == r_killed:
            agree += 1
            continue
        w, rr = runs[r["mutant"]]["whole"], runs[r["mutant"]]["recorder"]
        function = key.rsplit("__mutmut_", 1)[0]
        tests = None if selected is None else sorted(
            junit_key(t, n) for t in selected.get(function, []) for n in run_names)
        inside = None if tests is None else sorted(set(w["lost"]) & set(tests))
        if m_killed and w["status"] == "error":
            cause = ("the package does not import in the mutant copy (the mutated function runs while the "
                     "package is imported; mutmut activates a mutant only after the import)")
        elif m_killed and w["status"] == "timeout":
            cause = "the whole-suite run exceeded its time limit here"
        elif m_killed and tests is not None and not tests:
            cause = "mutmut selected no test for the mutated function (no tests, counted as survived)"
        elif m_killed and inside == []:
            cause = "every test that kills the mutant here is outside mutmut's test selection for the function"
        else:
            cause = "not explained by the run statuses or the test selection"
        causes[cause] += 1
        differ.append({"mutmut_name": key, "mutant": r["mutant"], "function": r["function"],
                       "operator": r["operator"], "original": r["original"], "mutated": r["mutated"],
                       "whole_suite": ("killed" if m_killed else "survived") + f" ({w['status']})",
                       "recorder_run": rr["status"], "reference": ref_here[key]["tool_status"],
                       "mutmut_exit_code": exit_codes.get(key),
                       "mutmut_selected_tests": None if tests is None else len(tests),
                       "killing_tests": len(w["lost"]),
                       "killing_tests_selected_by_mutmut": None if inside is None else len(inside),
                       "killing_tests_first_20": w["lost"][:20], "cause": cause})
    return {"reference": "../mutation-adequacy-pyjwt/generated/mutants.csv (tool_class: killed or survived, "
                         "from mutmut's own run); test selection from its work/mutmut/mutants/mutmut-stats.json",
            "files": files, "mutants_here": len(mine), "mutants_reference": len(ref_here),
            "only_here": only_mine, "only_reference": only_ref,
            "compared": len(set(mine) & set(ref_here)), "agree": agree, "differ": len(differ),
            "differences_by_cause": dict(sorted(causes.items())),
            "differences_by_direction": dict(sorted(Counter(
                f"here {d.get('whole_suite', 'none').split(' ')[0]}, mutmut {d.get('reference', '')}"
                for d in differ).items())),
            "differences": differ}


# -- main ------------------------------------------------------------------------------------------------

def read_targets_file(path: Path, checks: dict) -> dict[str, str]:
    out = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise SystemExit(f"{path}:{n}: 2 fields separated by a tab are needed")
        key, cid = parts[0].strip(), parts[1].strip()
        if cid and cid not in checks:
            raise SystemExit(f"{path}:{n}: {cid} is no check of the subject")
        if key in out:
            raise SystemExit(f"{path}:{n}: case {key} twice")
        out[key] = cid or None
    return out


def test_list(values: list[str] | None) -> list[str]:
    out = []
    for v in values or []:
        if v.startswith("@"):
            out += [x.strip() for x in Path(v[1:]).read_text(encoding="utf-8").splitlines() if x.strip()]
        else:
            out.append(v)
    return sorted(set(out))


def main(argv: list[str]) -> int:
    need_python_312()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--subject", required=True)
    parser.add_argument("--targets-file")
    parser.add_argument("--without-tests", nargs="+")
    parser.add_argument("--extra-tests")
    parser.add_argument("--replace", nargs="+", default=[])
    parser.add_argument("--work")
    parser.add_argument("--out")
    parser.add_argument("--clone")
    parser.add_argument("--deposited", help="the toolkit's outputs of the subject (default: "
                        "../target-reach/generated/<name>/)")
    args = parser.parse_args(argv)
    subject_path, subject = subject_paths(args.subject)
    name = subject["name"]
    defs = subject_path.parent
    work = Path(args.work).resolve() if args.work else default_work(name)
    out = Path(args.out).resolve() if args.out else default_out(name)
    clone, _ = local_settings(name, args.clone, "unused")
    rec = work / "records"
    for need in (defs / "checks.json", defs / "blocks.json", defs / "targets.json", out / "mutants.csv",
                 out / "materialize.json", rec / "suite.json", rec / "base-1.json", rec / "base-2.json",
                 rec / "whole" / "base.json"):
        if not need.exists():
            raise SystemExit(f"absent: {need}")
    checks_doc = load_json(defs / "checks.json")
    checks = {c["id"]: c for c in checks_doc["checks"]}
    blocks = {b["key"]: b for b in load_json(defs / "blocks.json")["blocks"]}
    block_targets = {t["key"]: t.get("target") for t in load_json(defs / "targets.json")["blocks"]}
    with (out / "mutants.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    tool_rows = [r for r in rows if r["operator"] != DELETION]
    tool = {r["mutant"] for r in tool_rows}
    deleted_check = {r["mutant"]: r["check"] for r in rows if r["operator"] == DELETION}
    materialized = load_json(out / "materialize.json")
    base_raw, base2_raw = load_json(rec / "base-1.json"), load_json(rec / "base-2.json")
    base = Run(base_raw)
    whole_base = load_json(rec / "whole" / "base.json")
    passing = set(whole_base["passing"])
    keys = sorted(k for k, c in base.cases.items() if left_out_reason(c) is None)

    targets_file = read_targets_file(Path(args.targets_file), checks) if args.targets_file else None
    if targets_file is not None:
        unknown = sorted(set(targets_file) - set(keys))
        if unknown:
            raise SystemExit(f"--targets-file names cases that are no cases of the study: {unknown[:5]}")

    def target_of(k: str) -> str | None:
        if targets_file is not None:
            return targets_file.get(k)
        return block_targets.get(base.cases[k]["block"])

    def deciding(k: str) -> str | None:
        return (base.cases[k].get("site") or {}).get("check")

    # the functions of the mutated files, with their lines
    mutated_files = sorted({r["file"] for r in rows})
    spans: dict[tuple[str, str], tuple[int, int]] = {}
    for f in mutated_files:
        tree = ast.parse((clone / rel_to_source(subject, f)).read_bytes())
        for q, node in functions(tree).items():
            spans[(f, q)] = span(node)
    changed = {r["mutant"]: parse_lines(r["changed_lines"]) for r in rows}

    def lies_in(mid: str, check: str | None) -> bool | None:
        """The changed lines of the mutant lie inside the function of the check
        (its file and its lines, nested definitions included). None when the
        check's file was not mutated."""
        if not check:
            return None
        c = checks[check]
        if c["file"] not in mutated_files:
            return None
        if c["file"] != rows_by_id[mid]["file"]:
            return False
        a, z = spans[(c["file"], c["function"])]
        return all(a <= x <= z for x in changed[mid])

    rows_by_id = {r["mutant"]: r for r in rows}
    runs = {}
    for r in rows:
        p = work / "runs" / f"{r['mutant']}.json"
        if p.exists():
            runs[r["mutant"]] = load_json(p)

    # -- per mutant and case --------------------------------------------------------------------
    base_or = {k: oracles(base.cases[k], base.cases[k], target_of(k)) for k in keys}
    case_rows, oracle_rows, runs_lines = [], [], []
    oracle_header = (["mutant", "file", "function", "operator", "check", "recorder_run"] + ORACLES + ["suite"]
                     + [f"{o} withheld-as-failing" for o in CASE_ORACLES]
                     + ["whole_suite_run", "whole_suite_killed", "whole_suite_tests_killing"])
    det_by_case: dict[str, dict[str, set]] = {k: {o: set() for o in ORACLES} for k in keys}
    status_counts = Counter()
    rec_status, whole_status, killers = {}, {}, {}
    mutant_det = {}
    for r in rows:
        mid = r["mutant"]
        entry = runs.get(mid)
        if entry is None:
            continue
        rstatus = entry["recorder"]["status"]
        rec_status[mid] = rstatus
        run = None
        if rstatus == "completed":
            p = rec / "mutants" / f"{mid}.json"
            run = Run(load_json(p)) if p.exists() else None
            if run is None:
                rstatus = rec_status[mid] = "record absent"
        per_case = {k: case_detection(rstatus, run, base, k, base_or[k], target_of(k)) for k in keys}
        for k in keys:
            d = per_case[k]
            if mid in tool:
                status_counts[d["status"]] += 1
                for o in ORACLES:
                    if d[o]:
                        det_by_case[k][o].add(mid)
            case_rows.append([mid, k, d["status"]] + [yn(d[o]) for o in ORACLES]
                             + [yn(d["withheld"][o]) if d[o] is not None else "" for o in CASE_ORACLES])
        md = mutant_detection(rstatus, run, base, keys, per_case)
        mutant_det[mid] = md
        w = entry["whole"]
        whole_status[mid] = w["status"]
        killers[mid] = set(w["lost"]) if w["status"] == "completed" else set()
        wk = whole_killed(w)
        oracle_rows.append([mid, r["file"], r["function"], r["operator"], r.get("check", ""), rstatus]
                           + [yn(md[o]) for o in ORACLES] + [yn(md["suite"])]
                           + [yn(md["withheld"][o]) for o in CASE_ORACLES]
                           + [w["status"], yn(wk), len(w["lost"])])
        line = {"mutant": mid, "recorder": rstatus, "recorder_runs": entry["recorder"]["runs"],
                "whole": w["status"], "whole_runs": w["runs"], "whole_not_passing": w["lost"]}
        if entry.get("extra"):
            line["extra"] = {d: {"status": e["status"], "runs": e["runs"], "not_passing": e["lost"]}
                             for d, e in sorted(entry["extra"].items())}
        runs_lines.append(line)

    # -- per test of the whole suite ----------------------------------------------------------------
    killed_by: dict[str, set] = defaultdict(set)
    deletions_killed_by: dict[str, set] = defaultdict(set)
    for mid, ts in killers.items():
        for t in ts:
            (killed_by if mid in tool else deletions_killed_by)[t].add(mid)
    # a unique kill: the killing tests are 1 test, the name of the suite run left aside
    unique = {mid: set(ts) for mid, ts in killers.items()
              if len({t.split("|", 1)[1] for t in ts}) == 1}
    tool_killers = {m: ts for m, ts in killers.items() if m in tool}
    tool_status = {m: s for m, s in whole_status.items() if m in tool}
    deletion_killers = {m: ts for m, ts in killers.items() if m in deleted_check}
    deletion_status = {m: s for m, s in whole_status.items() if m in deleted_check}

    def fn_of(mid: str) -> str:
        return f"{rows_by_id[mid]['file']}:{rows_by_id[mid]['function']}"

    def fn_counts(mids) -> str:
        c = Counter(fn_of(m) for m in mids)
        return "; ".join(f"{f} x{n}" for f, n in sorted(c.items()))

    own_keys = {}
    run_names = [x["name"] for x in subject["suite_runs"]]
    for k in keys:
        test = base.cases[k]["test"]
        own_keys[test] = sorted(junit_key(test, n) for n in run_names if junit_key(test, n) in passing)
    test_rows = []
    for t in sorted(set(killed_by) | set(deletions_killed_by)):
        mids, dels = killed_by.get(t, set()), deletions_killed_by.get(t, set())
        uniq = sorted(m for m in mids if m in unique)
        n_cases = sum(1 for k in keys if t in own_keys[base.cases[k]["test"]])
        test_rows.append([t, len(mids), len(uniq), fn_counts(uniq), n_cases, len(dels),
                          " ".join(sorted(deleted_check[m] for m in dels if m in unique))])

    # -- per case ---------------------------------------------------------------------------------------
    per_case_rows = []
    for k in keys:
        b = base.cases[k]
        tgt, dec = target_of(k), deciding(k)
        own = own_keys[b["test"]]
        cells = []
        for o in ORACLES:
            mids = det_by_case[k][o]
            in_t = None if lies_in(next(iter(rows_by_id)), tgt) is None else sum(1 for m in mids if lies_in(m, tgt))
            in_d = None if lies_in(next(iter(rows_by_id)), dec) is None else sum(1 for m in mids if lies_in(m, dec))
            cells += [in_t, in_d, len(mids)]
        uniq = sorted(m for m, ts in unique.items() if m in tool and ts & set(own))
        per_case_rows.append([k, b["block"], b["index"], b["test"],
                              "message" if asserts_message(blocks[b["block"]]) else "class only",
                              tgt, f"{checks[tgt]['file']}:{checks[tgt]['function']}" if tgt else "",
                              site_label(b), f"{checks[dec]['file']}:{checks[dec]['function']}" if dec else "",
                              " ".join(own)] + cells + [len(uniq), fn_counts(uniq)])

    # -- sentinels ----------------------------------------------------------------------------------------
    sentinels = []
    m_s1 = next(s for s in materialized["sentinels"] if s["name"] == "S1")
    m_s2 = next(s for s in materialized["sentinels"] if s["name"] == "S2")
    s1 = recheck_files(rows, work, clone, subject, runs)
    sentinels.append({"name": "S1", "pass": m_s1["pass"] and not s1,
                      "text": m_s1["text"] + "; rechecked from the modified files, and the runs used them",
                      "detail": (m_s1["detail"] + s1)[:50]})
    mutmut_counts = {f: v["mutmut_names"] for f, v in materialized["files"].items()}
    here_counts = dict(sorted(Counter(r["file"] for r in tool_rows).items()))
    s2_ok = m_s2["pass"] and mutmut_counts == here_counts
    sentinels.append({"name": "S2", "pass": s2_ok, "text": m_s2["text"],
                      "detail": m_s2["detail"][:50] + ([] if mutmut_counts == here_counts
                                                       else [f"mutants.csv {here_counts}, mutmut {mutmut_counts}"])})
    dep_cases, dep_whole = deposited(Path(args.deposited).resolve() if args.deposited
                                            else TOOLKIT / "generated" / name)
    s3 = []
    if dep_cases is None or dep_whole is None:
        s3.append("the deposited cases.csv or whole-suite baseline of the toolkit is absent")
    else:
        mine_sites = {(base.cases[k]["block"], str(base.cases[k]["index"]), base.cases[k]["test"]): site_label(base.cases[k])
                      for k in keys}
        theirs = {(c["block"], c["index"], c["test_node"]): c["baseline_site"] for c in dep_cases}
        if set(mine_sites) != set(theirs):
            s3.append(f"cases: {len(set(mine_sites) - set(theirs))} here only, {len(set(theirs) - set(mine_sites))} "
                      "deposited only")
        diff = sorted(f"{x}: {mine_sites[x]} / {theirs[x]}" for x in set(mine_sites) & set(theirs)
                      if mine_sites[x] != theirs[x])
        s3 += [f"deciding check differs: {d}" for d in diff]
        if set(dep_whole["passing"]) != passing:
            s3.append(f"whole-suite passing tests: {len(passing - set(dep_whole['passing']))} here only, "
                      f"{len(set(dep_whole['passing']) - passing)} deposited only")
    if norm(base_raw) != norm(base2_raw):
        s3.append("the 2 unmodified recorder runs give different records, message texts aside")
    sentinels.append({"name": "S3", "pass": not s3,
                      "text": "the unmodified copies give the deposited baseline: the same cases and the same "
                              "deciding check for every case as the toolkit's cases.csv, the same tests passing "
                              "in both whole-suite runs as its whole-suite baseline, and 2 identical recorder "
                              "records, message texts aside",
                      "detail": s3[:50]})
    s4 = []
    extra_digest = None
    if args.extra_tests:
        from run_mutants import extra_digest as digest_of
        extra_digest = digest_of(Path(args.extra_tests).resolve())
    for r in rows:
        e = runs.get(r["mutant"])
        if e is None:
            s4.append(f"{r['mutant']}: no runs")
            continue
        if rec_status.get(r["mutant"]) not in STATUSES:
            s4.append(f"{r['mutant']}: recorder run {rec_status.get(r['mutant'])}")
        if e["whole"]["status"] not in STATUSES or (e["whole"]["status"] != "completed" and e["whole"]["runs"] != 2):
            s4.append(f"{r['mutant']}: whole-suite run {e['whole']['status']}, {e['whole']['runs']} runs")
        if extra_digest and extra_digest not in (e.get("extra") or {}):
            s4.append(f"{r['mutant']}: no run of the extra tests {extra_digest}")
    sentinels.append({"name": "S4", "pass": not s4,
                      "text": "every mutant has its recorder run and its whole-suite run (and the extra tests "
                              "when given), each completed or stated as a timeout or an error after 1 repeat",
                      "detail": s4[:50]})
    whole_kill = {mid: whole_killed(runs[mid]["whole"]) for mid in runs}
    reference = None
    if name.startswith("pyjwt"):
        reference = reference_comparison(tool_rows, whole_kill, runs, run_names)
    gen = Path(args.deposited).resolve() if args.deposited else TOOLKIT / "generated" / name
    deletions = deletions_comparison(
        gen, {row[4]: dict(zip(oracle_header, row)) for row in oracle_rows if row[3] == DELETION},
        targets_file is None)
    if reference is not None:
        sentinels.append({"name": "S5", "pass": not reference["only_here"] and not reference["only_reference"],
                          "text": "the mutants of the 2 PyJWT modules are those of the reference study, by "
                                  "mutmut name; the agreement of the whole-suite status with its mutmut status "
                                  "is reported, with every difference",
                          "detail": [f"agree {reference['agree']} of {reference['compared']}"]
                          + [f"{n} x {c}" for c, n in reference["differences_by_cause"].items()]})
    if deletions is not None:
        sentinels.append({"name": "S6", "pass": not deletions["differences"],
                          "text": "the deletion of each check that the toolkit's deletions.csv lists gives here "
                                  "what the toolkit recorded for its own deletion copy: the same detection under "
                                  "each oracle and by the suite of the recorder run, the same "
                                  "withheld-as-failing columns, the same whole-suite status and the same number "
                                  "of tests not passing"
                                  + ("" if targets_file is None else " (O_T aside: the targets come from a file)"),
                          "detail": [f"compared {deletions['compared']} of {deletions['deletions_here']} deletions"]
                          + deletions["differences"][:50]})

    # -- score ----------------------------------------------------------------------------------------------
    score = {"subject": {k: subject.get(k) for k in ("name", "version", "commit")},
             "files": mutated_files, "mutmut_version": materialized.get("mutmut_version"),
             "targets": "--targets-file" if targets_file is not None else "targets.json",
             "whole_suite": score_counts(tool_killers, tool_status),
             "recorder_runs": dict(sorted(Counter(s for m, s in rec_status.items() if m in tool).items())),
             "whole_suite_runs": dict(sorted(Counter(tool_status.values()).items())),
             "case_statuses": dict(sorted(status_counts.items())),
             "cases": len(keys),
             "tests_passing_in_both_unmodified_runs": len(passing),
             "tests_killing_at_least_1_mutant": len(killed_by),
             "mutants_killed_by_exactly_1_test": sum(1 for m in unique if m in tool),
             "by_file": {}, "by_operator": {},
             "mutant_level_oracles": {o: sum(1 for m, d in mutant_det.items() if m in tool and d[o])
                                      for o in ORACLES + ["suite"]},
             "sentinels": sentinels}
    for key, group in (("by_file", "file"), ("by_operator", "operator")):
        for g in sorted({r[group] for r in tool_rows}):
            mids = [r["mutant"] for r in tool_rows if r[group] == g and r["mutant"] in whole_status]
            c = score_counts({m: killers[m] for m in mids}, {m: whole_status[m] for m in mids})
            score[key][g] = {k: v for k, v in c.items() if not k.endswith("_mutants")}
    score["check_deletions"] = {
        **score_counts(deletion_killers, deletion_status),
        "recorder_runs": dict(sorted(Counter(s for m, s in rec_status.items() if m in deleted_check).items())),
        "killed_by_exactly_1_test": sum(1 for m in unique if m in deleted_check),
        "mutant_level_oracles": {o: sum(1 for m, d in mutant_det.items() if m in deleted_check and d[o])
                                 for o in ORACLES + ["suite"]},
        "not_killed": sorted(deleted_check[m] for m in deletion_status
                             if deletion_status[m] == "completed" and not deletion_killers[m])}
    without = test_list(args.without_tests)
    if without:
        unknown = sorted(set(without) - set(whole_base["passing"]) - set(whole_base.get("unstable", [])))
        reduced = {m: ts - set(without) for m, ts in tool_killers.items()}
        c = score_counts(reduced, tool_status)
        score["without_tests"] = {"tests_left_out": without, "unknown_tests": unknown, **c,
                                  "no_longer_killed": sorted(m for m in tool_killers
                                                             if tool_killers[m] and not reduced[m])}
    if args.extra_tests:
        extra_base = load_json(work / "extra" / extra_digest / "base.json")
        extra_kill, extra_status = {}, {}
        for mid, e in runs.items():
            x = (e.get("extra") or {}).get(extra_digest)
            if x is None:
                continue
            extra_status[mid] = x["status"]
            extra_kill[mid] = set(x["lost"]) if x["status"] == "completed" else set()
        combined_status = {m: (whole_status[m] if whole_status[m] != "completed" else
                               (extra_status.get(m, "completed") if extra_status.get(m) != "completed" else "completed"))
                           for m in whole_status}
        combined = {m: killers[m] | extra_kill.get(m, set()) for m in killers}

        def of(kind: set, d: dict) -> dict:
            return {m: v for m, v in d.items() if m in kind}

        section = {"digest": extra_digest, "files": extra_base["files"], "extra_tests": extra_base["tests"],
                   "extra_tests_passing_in_both_unmodified_runs": extra_base["passing"],
                   "extra_tests_alone": score_counts(of(tool, extra_kill), of(tool, extra_status)),
                   "with_extra_tests": score_counts(of(tool, combined), of(tool, combined_status)),
                   "newly_killed": sorted(m for m in combined if m in tool and combined[m] and not killers[m]
                                          and whole_status[m] == "completed"),
                   "check_deletions": {
                       "extra_tests_alone": score_counts(of(set(deleted_check), extra_kill),
                                                         of(set(deleted_check), extra_status)),
                       "with_extra_tests": score_counts(of(set(deleted_check), combined),
                                                        of(set(deleted_check), combined_status)),
                       "newly_killed": sorted(deleted_check[m] for m in combined
                                              if m in deleted_check and combined[m] and not killers[m]
                                              and whole_status[m] == "completed")}}
        replacements = []
        for pair in args.replace:
            old, sep, new = pair.partition("=")
            if not sep:
                raise SystemExit(f"--replace {pair}: OLD=NEW is needed")
            new_ids = [t for t in extra_base["tests"] if t == new or t.endswith(new)]
            if len(new_ids) != 1:
                raise SystemExit(f"--replace: {new} names {len(new_ids)} extra tests")
            if old not in passing:
                raise SystemExit(f"--replace: {old} is no test that passes in both unmodified runs")
            replaced = {m: (killers[m] - {old}) | ({new_ids[0]} & extra_kill.get(m, set())) for m in tool_killers}
            c = score_counts(replaced, of(tool, combined_status) if extra_status else tool_status)
            replacements.append({"old": old, "new": new_ids[0], **c,
                                 "no_longer_killed": sorted(m for m in tool_killers
                                                            if killers[m] and not replaced[m]),
                                 "newly_killed": sorted(m for m in replaced if replaced[m] and not killers[m])})
        section["replacements"] = replacements
        score["extra_tests"] = section
    if reference is not None:
        score["reference_study"] = reference
    if deletions is not None:
        score["check_deletions"]["toolkit_deletions"] = deletions

    # -- write ---------------------------------------------------------------------------------------------
    out.mkdir(parents=True, exist_ok=True)
    packed = {
        "runs.jsonl": "".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n"
                              for x in sorted(runs_lines, key=lambda x: x["mutant"])),
        "cases.csv": csv_text(["mutant", "case", "status"] + ORACLES
                              + [f"{o} withheld-as-failing" for o in CASE_ORACLES], case_rows),
    }
    assert set(packed) == set(PACKED)
    score["sha256_before_compression"] = {n: write_packed(out / n, text) for n, text in sorted(packed.items())}
    files = {
        "oracles.csv": csv_text(oracle_header, oracle_rows),
        "per-case.csv": csv_text(["case", "block", "index", "test", "asserts", "target", "target_function",
                                  "deciding_check", "deciding_function", "own_test_in_whole_suite"]
                                 + [f"{o}_{w}" for o in ORACLES for w in
                                    ("kills_in_target_function", "kills_in_deciding_function", "kills")]
                                 + ["unique_kills", "unique_kill_functions"], per_case_rows),
        "per-test.csv": csv_text(["test", "kills", "unique_kills", "unique_kill_functions", "cases_of_the_test",
                                  "check_deletions_killed", "check_deletions_killed_by_this_test_only"],
                                 test_rows),
        "score.json": json.dumps(score, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
    }
    for fname, text in files.items():
        (out / fname).write_text(text, encoding="utf-8")
    sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
            for p in sorted(out.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    s = score["whole_suite"]
    failed = [x["name"] for x in sentinels if not x["pass"]]
    d = score["check_deletions"]
    print(f"analyse_mutants: {name}: {s['mutants']} mutants of mutmut, killed {s['killed']} (by a test "
          f"{s['killed_by_a_test']}, timeouts {s['timeouts']}, errors {s['errors']}), survived {s['survived']}; "
          f"{d['mutants']} deletions of checks, killed {d['killed']}, survived {d['survived']}; "
          f"{len(keys)} cases; sentinels that do not hold: {failed or 'none'}")
    for x in sentinels:
        for d in x["detail"][:10]:
            print(f"  {x['name']}: {d}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

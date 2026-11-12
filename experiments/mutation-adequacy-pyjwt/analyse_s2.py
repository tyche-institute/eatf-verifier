"""Analysis for the PyJWT mutation-adequacy study (see PROTOCOL.md).

    work/venv/bin/python -I analyse_s2.py

Reads the records that run_s2.py wrote to work/records/ and writes
generated/: the measures, sentinels and predictions of the protocol, the
exploratory analyses it lists, CSV tables, summary.json, SUMMARY.md,
environment.json, pip-freeze.txt and SHA256SUMS. No definition from the
protocol is changed here; where the protocol left a detail open, the choice
is named in the code and in PROTOCOL.md, "Deviations".
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
RECORDS = WORK / "records"
GENERATED = HERE / "generated"
MUTMUT_PROJECT = WORK / "mutmut"
CHECKS = json.loads((HERE / "checks.json").read_text(encoding="utf-8"))
CASES = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
MUTATED = sorted(CHECKS["subject_functions"])
ORACLES = ("O_V", "O_V_fc", "O_C", "O_T", "O_S")
EXPLORATORY = ("O_CM",)
NAMES = {"O_V": "O_V", "O_V_fc": "O_V^fc", "O_C": "O_C", "O_T": "O_T", "O_S": "O_S", "O_CM": "O_CM"}
SOURCES = ["PROTOCOL.md", "define_s2.py", "checks.json", "cases.json", "plugin/s2_recorder.py",
           "run_s2.py", "analyse_s2.py", ".gitignore"]

# mutmut 3.8.1 exit codes and the first study's mapping of statuses to classes
MUTMUT_STATUS = {1: "killed", 3: "killed", 0: "survived", 5: "no tests", 33: "no tests",
                 36: "timeout", 24: "timeout", -24: "timeout", 152: "timeout", 255: "timeout",
                 -11: "segfault", -9: "segfault"}
TOOL_CLASS = {"killed": "killed", "timeout": "killed", "segfault": "killed",
              "survived": "survived", "no tests": "survived"}

CHECK_BY_ID = {c["id"]: c for c in CHECKS["checks"]}
ORDER = {key: i for i, key in enumerate(CHECKS["order"])}
INCLUDED = {b["key"]: b for b in CASES["blocks"] if b["included"]}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}%" if b else "n/a"


def share(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


# -- cases ------------------------------------------------------------------

def case_id(rec: dict) -> str:
    return f"{rec['test']}|{rec['key']}|{rec['occurrence']}"


def target_of(block: dict, params: dict) -> tuple[str | None, str | None]:
    label = block["label"]
    if "by_param" in label:
        value = label["values"][params[label["by_param"]]]
        return value["target"], value.get("segment")
    return label.get("target"), label.get("segment")


def position(check: str | None, segment: str | None) -> int | None:
    if check is None:
        return None
    key = f"{check}:{segment}" if check == "jws.segment-encoding" else check
    return ORDER.get(key)


def baseline_cases(base: dict) -> dict[str, dict]:
    cases = {}
    for rec in base["blocks"]:
        if not rec["included"]:
            continue
        cid = case_id(rec)
        if cid in cases:
            raise SystemExit(f"case {cid} recorded twice")
        block = INCLUDED[rec["key"]]
        params = base["tests"][rec["test"]].get("params", {})
        target, segment = target_of(block, params)
        site = rec.get("site") or {}
        cases[cid] = {
            "cid": cid, "test": rec["test"], "key": rec["key"], "occurrence": rec["occurrence"],
            "file": block["file"], "expected": block["expected"], "B": rec.get("class"),
            "message": rec.get("message"), "target": target, "segment": segment,
            "labelled": target is not None, "site": site.get("check"), "site_segment": site.get("segment"),
            "post": block["post"], "params": params, "match": block["match"],
        }
    return cases


def post_holds(spec: list, rec: dict, params: dict) -> bool:
    message = rec.get("message")
    kind = spec[0]
    if kind == "str_eq":
        return message == spec[1]
    if kind == "str_in":
        return message is not None and spec[1] in message
    if kind == "str_in_param":
        return message is not None and str(params[spec[1]]) in message
    if kind == "attr_eq":
        if spec[1] != "claim":
            raise SystemExit(f"the recorder does not record attribute {spec[1]}")
        return rec.get("claim") == spec[2]
    if kind == "cause_isinstance":
        mro = rec.get("cause_mro") or []
        return any(q == spec[1] or q.rsplit(".", 1)[-1] == spec[1] for q in mro)
    raise SystemExit(f"unknown post assertion {spec}")


def holds(oracle: str, case: dict, rec: dict) -> bool:
    raised = rec.get("outcome") == "raised"
    if oracle == "O_V":
        return raised and bool(rec.get("pyjwt_error"))
    if oracle == "O_V_fc":
        return raised
    if oracle == "O_C":
        return raised and rec.get("class") == case["B"]
    if oracle == "O_T":
        if not case["labelled"] or not raised:
            return False
        site = rec.get("site") or {}
        return site.get("check") == case["target"] and (
            case["segment"] is None or site.get("segment") == case["segment"])
    if oracle == "O_S":
        return rec.get("real") == "ok" and all(post_holds(s, rec, case["params"]) for s in case["post"])
    if oracle == "O_CM":
        return raised and rec.get("class") == case["B"] and rec.get("message") == case["message"]
    raise SystemExit(oracle)


# -- runs -------------------------------------------------------------------

def run_log(path: Path) -> dict[str, dict]:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            out[entry["name"]] = entry  # the last line for a name wins
    return out


RAISES_IN = Counter()
for _c in CHECKS["checks"]:
    RAISES_IN[(_c["file"], _c["function"])] += len(_c["raises"])
for _r in CHECKS["non_check_raises"]:
    RAISES_IN[(_r["file"], _r["function"])] += 1
CHECK_AT = {(c["file"], c["function"], k): c["id"] for c in CHECKS["checks"] for k in c["raises"]}


def renumber_after_deletion(record: dict, deleted: dict) -> int:
    """Map raise sites in a deletion run back to the unmodified source.

    The recorder numbers the raise statements of the function it runs. In a
    deletion copy the deleted raises are gone from their function, so every
    later raise of that function has a lower number than in the unmodified
    source, and the recorder's check for it is the wrong one. Here the
    number is mapped back (the k-th remaining raise is the k-th raise that
    was not deleted) and the check, and for jws.segment-encoding the
    segment, are looked up again. Returns the number of sites changed."""
    where = (deleted["file"], deleted["function"])
    kept = [k for k in range(RAISES_IN[where]) if k not in deleted["raises"]]
    changed = 0
    for rec in record["blocks"]:
        site = rec.get("site")
        if not site or not site["frames"]:
            continue
        inner = site["frames"][-1]
        if inner["kind"] != "raise" or (inner["file"], inner["function"]) != where:
            continue
        if inner["ordinal"] >= len(kept):
            raise SystemExit(f"raise {inner['ordinal']} of {where} in a copy without {deleted['id']}")
        check = CHECK_AT.get((*where, kept[inner["ordinal"]]))
        segment = None
        if check == "jws.segment-encoding" and len(site["frames"]) > 1:
            outer = site["frames"][-2]
            if (outer["function"] == "PyJWS._load" and outer["kind"] == "call"
                    and outer["callee"] == "_decode_base64url_segment"):
                segment = {v: k for k, v in CHECKS["segment_calls"].items()}.get(outer["ordinal"])
        if (check, segment) != (site["check"], site["segment"]):
            site["recorded_check"], site["recorded_segment"] = site["check"], site["segment"]
            site["check"], site["segment"] = check, segment
            changed += 1
    return changed


def run_state(record_path: Path, entry: dict | None, cases: dict, deleted: dict | None = None) -> dict:
    """What happened to each baseline case in one run.

    A case that did not run is crashed (its test was not collected, its setup
    failed or the test stopped on an exception that is not an assertion
    failure) or withheld (the test stopped on AssertionError or pytest's own
    failure). A case missing from a test that did not stop is "missing"; it
    is excluded like a withheld case and counted separately. For a deletion
    run, `deleted` is the deleted check and raise sites are renumbered."""
    if entry is not None and entry.get("timed_out"):
        return {"state": "timeout", "cases": {}}
    if not record_path.exists():
        return {"state": "load-failure", "cases": {}}
    record = load(record_path)
    renumbered = renumber_after_deletion(record, deleted) if deleted is not None else 0
    observed = {}
    for rec in record["blocks"]:
        if rec["included"]:
            cid = case_id(rec)
            if cid in observed:
                raise SystemExit(f"{record_path.name}: case {cid} recorded twice")
            observed[cid] = rec
    if not observed:
        return {"state": "load-failure", "cases": {}, "record": record, "renumbered": renumbered}
    status = {}
    for cid, case in cases.items():
        if cid in observed:
            status[cid] = ("observed", observed[cid])
            continue
        test = record["tests"].get(case["test"])
        if test is None or (test.get("setup") or {}).get("outcome") != "passed":
            status[cid] = ("crashed", None)
            continue
        stop = (test.get("call") or {}).get("stop")
        if stop is None:
            status[cid] = ("missing", None)
        else:
            status[cid] = ("withheld" if stop["assertion"] else "crashed", None)
    return {"state": "ran", "cases": status, "record": record, "renumbered": renumbered}


def evaluate(state: dict, s: dict[str, set[str]], cases: dict, oracles=ORACLES + EXPLORATORY) -> dict:
    """Kill decision per oracle, with the cases that kill, and the sensitivity
    variant that counts withheld cases as failing."""
    out = {}
    # PROTOCOL.md, "Kill": a crash of any case kills under every oracle; the
    # crashed case is credited with the kill only if it is in S_O.
    crashed_any = any(kind == "crashed" for kind, _ in state["cases"].values())
    for oracle in oracles:
        if state["state"] != "ran":
            out[oracle] = {"killed": True, "by": state["state"], "cases": [], "withheld_killed": True}
            continue
        killing, withheld = [], []
        for cid, (kind, rec) in state["cases"].items():
            if cid not in s[oracle]:
                continue
            if kind == "crashed" or (kind == "observed" and not holds(oracle, cases[cid], rec)):
                killing.append(cid)
            elif kind == "withheld":
                withheld.append(cid)
        killed = bool(killing) or crashed_any
        out[oracle] = {"killed": killed, "by": "cases" if killing else ("crash" if killed else None),
                       "cases": sorted(killing), "withheld_killed": bool(killed or withheld)}
    return out


def moves(state: dict, cases: dict) -> Counter:
    """How the raise site of each observed baseline case moved, by the order in
    checks.json."""
    out: Counter = Counter()
    if state["state"] != "ran":
        return out
    for cid, (kind, rec) in state["cases"].items():
        if kind != "observed":
            out[kind] += 1
            continue
        case = cases[cid]
        if rec.get("outcome") != "raised":
            out["no exception"] += 1
            continue
        site = rec.get("site") or {}
        check, segment = site.get("check"), site.get("segment")
        if check == case["site"] and segment == case["site_segment"]:
            out["same"] += 1
            continue
        if check is None:
            out["no check"] += 1
            continue
        p0, p1 = position(case["site"], case["site_segment"]), position(check, segment)
        if p0 is None or p1 is None:
            out["unordered"] += 1
        else:
            out["later" if p1 > p0 else "earlier"] += 1
    return out


def normalise(record: dict) -> dict:
    """A record without timing, paths, line numbers and mutmut's variant names,
    for sentinel 1."""
    blocks = []
    for rec in record["blocks"]:
        rec = dict(rec)
        if rec.get("site"):
            rec["site"] = dict(rec["site"])
            rec["site"]["frames"] = [{k: v for k, v in f.items() if k not in ("line", "variant")}
                                     for f in rec["site"]["frames"]]
        blocks.append(rec)
    return {"blocks": blocks, "tests": record["tests"], "collect_errors": record["collect_errors"]}


OBSERVED_FIELDS = ("outcome", "class", "pyjwt_error", "message", "claim", "cause_mro", "real")


def observation(kind: str, rec: dict | None) -> list:
    """One case in one run, for outcomes.jsonl: the status, and for an observed
    case what the oracles read."""
    if kind != "observed":
        return [kind]
    site = rec.get("site") or {}
    return ["observed", *[rec.get(f) for f in OBSERVED_FIELDS], site.get("check"), site.get("segment")]


class Outcomes:
    """generated/outcomes.jsonl: a header with every baseline case, then one
    line per run with each case's observation, or null where it equals the
    first baseline run's."""

    def __init__(self, cases: dict, base_state: dict) -> None:
        self.order = list(cases)
        self.base = {cid: observation(*base_state["cases"][cid]) for cid in self.order}
        self.lines = [{
            "schema": "urn:eatf:experiment:mutation-adequacy-pyjwt-outcomes:1",
            "fields": ["status", *OBSERVED_FIELDS, "site_check", "site_segment"],
            "note": "site_check in a deletion run is the check after the renumbering of PROTOCOL.md, deviation 6",
            "cases": [{"case": cid, **{k: cases[cid][k] for k in ("test", "key", "occurrence", "expected", "B", "target",
                                                                     "segment", "labelled", "site", "site_segment",
                                                                     "post", "params")},
                       "baseline": self.base[cid]} for cid in self.order],
        }]

    def add(self, run: str, kind: str, state: dict) -> None:
        cases = None
        if state["state"] == "ran":
            cases = []
            for cid in self.order:
                obs = observation(*state["cases"][cid])
                cases.append(None if obs == self.base[cid] else obs)
        self.lines.append({"run": run, "set": kind, "state": state["state"], "cases": cases})

    def write(self) -> None:
        with (GENERATED / "outcomes.jsonl").open("w", encoding="utf-8") as handle:
            for line in self.lines:
                handle.write(json.dumps(line, ensure_ascii=False, separators=(",", ":"), default=list) + "\n")


# -- mutmut's mutants -------------------------------------------------------

def mutmut_operators() -> dict[str, dict]:
    """The mutmut operator behind each mutant, and whether the mutant changes
    only the arguments of an exception in a raise statement.

    mutmut 3.8.1 does not store operator names. As in the first study, its
    mutations are enumerated again with its own visitor and operator table,
    each operator wrapped so that it tags what it yields; every re-created
    mutant function is compared with the one mutmut wrote."""
    import libcst as cst
    import mutmut.mutation.file_mutation as fm
    from mutmut.mutation.diff_apply import read_functions_from_index, read_mutant_function
    from mutmut.mutation.trampoline_templates import mangle_function_name
    from mutmut.utils.format_utils import get_mutant_name

    tags: dict[int, str] = {}

    def tagged(name, fn):
        def wrapper(node):
            for out in fn(node):
                tags[id(out)] = name
                yield out
        return wrapper

    saved = fm.mutation_operators
    fm.mutation_operators = [(t, tagged(fn.__name__.removeprefix("operator_"), fn)) for t, fn in saved]
    previous = Path.cwd()
    os.chdir(MUTMUT_PROJECT)
    labels: dict[str, dict] = {}
    render = cst.Module(body=[]).code_for_node
    try:
        for rel in MUTATED:
            code = (MUTMUT_PROJECT / rel).read_text(encoding="utf-8")
            module, mutations, _, _ = fm.create_mutations(rel, code, None, None)
            grouped = fm.group_by_top_level_node(mutations)
            owners = []
            for statement in module.body:
                if isinstance(statement, cst.FunctionDef):
                    owners.append((statement, None))
                elif isinstance(statement, cst.ClassDef) and isinstance(statement.body, cst.IndentedBlock):
                    owners += [(m, statement.name.value) for m in statement.body.body
                               if isinstance(m, cst.FunctionDef)]
            mutants_module = None
            for fn, class_name in owners:
                mangled = mangle_function_name(name=fn.name.value, class_name=class_name) + "__mutmut"
                for i, mutation in enumerate(grouped.get(fn, ()), start=1):
                    key = get_mutant_name(Path(rel), f"{mangled}_{i}")
                    mine = fm.deep_replace(fn, mutation.original_node, mutation.mutated_node)
                    found = read_functions_from_index(key, rel)
                    if found is not None:
                        theirs = found[1]
                    else:
                        if mutants_module is None:
                            mutants_module = cst.parse_module((MUTMUT_PROJECT / "mutants" / rel).read_text())
                        theirs = read_mutant_function(mutants_module, key)
                    same = dict(name=fn.name, leading_lines=[])
                    if render(mine.with_changes(**same)) != render(theirs.with_changes(**same)):
                        raise SystemExit(f"re-created mutant {key} differs from mutmut's")
                    if raise_count(render(fn)) != raise_count(render(mine)):
                        # the recorder's raise numbers would then point at other checks
                        raise SystemExit(f"mutant {key} adds or removes a raise statement")
                    labels[key] = {
                        "operator": tags[id(mutation.mutated_node)],
                        "exception_argument": exception_argument_only(render(fn), render(mine)),
                        "original": render(mutation.original_node).strip(),
                        "mutated": render(mutation.mutated_node).strip(),
                    }
    finally:
        fm.mutation_operators = saved
        os.chdir(previous)
    return labels


def stripped(tree: ast.AST) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            node.exc.args, node.exc.keywords = [], []
    return ast.dump(tree)


def raise_count(source: str) -> int:
    return sum(isinstance(node, ast.Raise) for node in ast.walk(ast.parse(textwrap.dedent(source))))


def exception_argument_only(original: str, mutated: str) -> bool:
    """True when the two functions differ, and are the same once the arguments
    of the exception call in every raise statement are removed."""
    a = ast.parse(textwrap.dedent(original))
    b = ast.parse(textwrap.dedent(mutated))
    return ast.dump(a) != ast.dump(b) and stripped(a) == stripped(b)


# -- output -----------------------------------------------------------------

def write_csv(name: str, rows: list[dict]) -> None:
    GENERATED.mkdir(exist_ok=True)
    with (GENERATED / name).open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def yn(value: bool) -> str:
    return "yes" if value else "no"


def main() -> int:
    if Path(sys.prefix).resolve() != (WORK / "venv").resolve():
        raise SystemExit("run with work/venv/bin/python")
    base = load(RECORDS / "baseline" / "base-1.json")
    base2 = load(RECORDS / "baseline" / "base-2.json")
    suite = load(RECORDS / "suite.json")
    timeout = load(RECORDS / "baseline" / "timeout.json")
    cases = baseline_cases(base)
    base_state = run_state(RECORDS / "baseline" / "base-1.json", None, cases)
    s = {o: {cid for cid, (kind, rec) in base_state["cases"].items() if kind == "observed"
             and holds(o, cases[cid], rec)} for o in ORACLES + EXPLORATORY}
    labelled = [cid for cid, c in cases.items() if c["labelled"]]

    # ---- sentinel 2 and P1 (baseline)
    tests_ok = all(all((t.get(w) or {}).get("outcome") == "passed" for w in ("setup", "call", "teardown"))
                   for t in base["tests"].values())
    blocks_ok = all(rec["real"] == "ok" for rec in base["blocks"])
    keys_seen = {rec["key"] for rec in base["blocks"] if rec["included"]}
    every_block = keys_seen == set(INCLUDED)
    sentinel2 = {"case_tests_pass": tests_ok, "pytest_check_passes_on_every_block": blocks_ok,
                 "every_included_block_runs": every_block,
                 "suite_without_recorder_passes": suite["returncode"] == 0,
                 "suite_summary": suite["summary"],
                 "case_tests": len(base["tests"]), "block_runs": len(base["blocks"]), "cases": len(cases)}
    p1_parts = {
        "every_case_raises_a_PyJWTError": len(s["O_V"]) == len(cases),
        "O_S_holds_on_every_case": len(s["O_S"]) == len(cases),
        "O_T_holds_on_every_labelled_case": len(s["O_T"]) == len(labelled),
    }
    o_t_misses = [{"case": cid, "target": cases[cid]["target"], "segment": cases[cid]["segment"],
                   "site": cases[cid]["site"], "site_segment": cases[cid]["site_segment"],
                   "message": cases[cid]["message"]}
                  for cid in labelled if cid not in s["O_T"]]

    outcomes = Outcomes(cases, base_state)
    outcomes.add("base-1", "baseline", base_state)
    outcomes.add("base-2", "baseline", run_state(RECORDS / "baseline" / "base-2.json", None, cases))

    # ---- sentinel 1
    reference = normalise(base)
    sentinel1 = {"base-2": normalise(base2) == reference}
    control_path = RECORDS / "deletions" / "_control.json"
    none_path = RECORDS / "mutants" / "_none.json"
    sentinel1["control"] = control_path.exists() and normalise(load(control_path)) == reference
    sentinel1["mutated package, no mutant active"] = none_path.exists() and normalise(load(none_path)) == reference
    outcomes.add("_control", "control", run_state(control_path, None, cases))
    outcomes.add("_none", "no mutant active", run_state(none_path, None, cases))

    # ---- deletions
    deletion_log = run_log(RECORDS / "deletions" / "runs.jsonl")
    reached = defaultdict(list)
    for cid, c in cases.items():
        if c["site"]:
            reached[c["site"]].append(cid)
    deletion_rows, deletion_case_rows, deletions = [], [], {}
    for check in CHECKS["checks"]:
        if not check["mutated"]:
            continue
        cid_ = check["id"]
        state = run_state(RECORDS / "deletions" / f"{cid_}.json", deletion_log.get(cid_), cases, deleted=check)
        verdict = evaluate(state, s, cases)
        mv = moves(state, cases)
        deletions[cid_] = {"state": state, "verdict": verdict, "moves": mv, "reached": cid_ in reached}
        outcomes.add(cid_, "deletion", state)
        changed = 0
        for cid, case in cases.items():
            kind, rec = state["cases"].get(cid, (state["state"], None))
            rec = rec or {}
            site = rec.get("site") or {}
            row = {"check": cid_, "case": cid, "status": kind,
                   "baseline_class": case["B"], "class": rec.get("class"),
                   "baseline_site": case["site"], "site": site.get("check"),
                   "baseline_segment": case["site_segment"], "segment": site.get("segment"),
                   "message": rec.get("message")}
            row.update({NAMES[o]: (yn(holds(o, case, rec)) if kind == "observed" else kind)
                        for o in ORACLES})
            differs = (kind != "observed" or rec.get("class") != case["B"]
                       or site.get("check") != case["site"] or site.get("segment") != case["site_segment"]
                       or rec.get("message") != case["message"] or rec.get("real") != "ok")
            if differs:
                changed += 1
                deletion_case_rows.append(row)
        deletion_rows.append({
            "check": cid_, "file": check["file"], "function": check["function"], "class": check["class"],
            "raise_statements": len(check["raises"]), "reached": yn(cid_ in reached),
            "baseline_cases_reaching": len(reached.get(cid_, [])), "run": state["state"],
            **{NAMES[o]: yn(verdict[o]["killed"]) for o in ORACLES},
            "O_CM": yn(verdict["O_CM"]["killed"]),
            "cases_changed": changed, "sites_renumbered": state.get("renumbered", 0),
            "moves": "; ".join(f"{k} {v}" for k, v in sorted(mv.items()) if k != "same"),
        })

    # ---- mutants
    listed = load(RECORDS / "mutants" / "list.json")
    labels = mutmut_operators()
    if set(labels) != {m["key"] for m in listed}:
        raise SystemExit(f"{len(labels)} operator labels for {len(listed)} mutmut mutants")
    mutant_log = run_log(RECORDS / "mutants" / "runs.jsonl")
    rows, results = [], {}
    for m in listed:
        status = MUTMUT_STATUS.get(m["exit_code"], f"exit {m['exit_code']}")
        tool = TOOL_CLASS.get(status, "excluded")
        label = labels[m["key"]]
        row = {"key": m["key"], "file": m["file"], "function": m["function"],
               "subject": yn(m["subject"]), "operator": label["operator"],
               "exception_argument": yn(label["exception_argument"]),
               "tool_status": status, "tool_class": tool,
               "original": label["original"][:200], "mutated": label["mutated"][:200]}
        if m["subject"]:
            entry = mutant_log.get(m["key"])
            if entry is None:
                raise SystemExit(f"no recorder run for {m['key']}")
            state = run_state(RECORDS / "mutants" / f"{m['key']}.json", entry, cases)
            verdict = evaluate(state, s, cases)
            mv = moves(state, cases)
            kinds = Counter(kind for kind, _ in state["cases"].values())
            outcomes.add(m["key"], "mutant", state)
            results[m["key"]] = {"verdict": verdict, "moves": mv, "state": state["state"], "tool": tool,
                                 "function": m["function"], "operator": label["operator"],
                                 "exception_argument": label["exception_argument"]}
            row.update({"run": state["state"], "crashed": kinds["crashed"], "withheld": kinds["withheld"],
                        "missing": kinds["missing"]})
            row.update({NAMES[o]: yn(verdict[o]["killed"]) for o in ORACLES + EXPLORATORY})
            row.update({f"{NAMES[o]} cases": len(verdict[o]["cases"]) for o in ORACLES})
            row.update({f"{NAMES[o]} withheld-as-failing": yn(verdict[o]["withheld_killed"]) for o in ORACLES})
            row["moves"] = "; ".join(f"{k} {v}" for k, v in sorted(mv.items()) if k not in ("same", "observed"))
        rows.append(row)
    subject_keys = [m["key"] for m in listed if m["subject"]]
    kills = {o: {k for k in subject_keys if results[k]["verdict"][o]["killed"]} for o in ORACLES + EXPLORATORY}
    kills_withheld = {o: {k for k in subject_keys if results[k]["verdict"][o]["withheld_killed"]}
                      for o in ORACLES}
    tool_killed = {k for k in subject_keys if results[k]["tool"] == "killed"}
    excluded = [k for k in subject_keys if results[k]["tool"] == "excluded"]
    exc_arg = {k for k in subject_keys if results[k]["exception_argument"]}
    n = len(subject_keys)

    # ---- sentinels 3-5
    del_kills = {o: {d for d, v in deletions.items() if v["verdict"][o]["killed"]} for o in ORACLES}
    sentinel3 = {
        "mutants": {"O_V_fc in O_V": kills["O_V_fc"] <= kills["O_V"], "O_V in O_C": kills["O_V"] <= kills["O_C"],
                    "O_V in O_S": kills["O_V"] <= kills["O_S"]},
        "deletions": {"O_V_fc in O_V": del_kills["O_V_fc"] <= del_kills["O_V"],
                      "O_V in O_C": del_kills["O_V"] <= del_kills["O_C"],
                      "O_V in O_S": del_kills["O_V"] <= del_kills["O_S"]},
    }
    s4_bad = sorted(kills["O_S"] - tool_killed)
    sentinel4 = {"holds": not s4_bad, "killed_under_O_S_not_by_mutmut": s4_bad}
    s5_targets = sorted({cases[cid]["target"] for cid in s["O_T"] if CHECK_BY_ID[cases[cid]["target"]]["mutated"]})
    s5_bad = [t for t in s5_targets if not deletions[t]["verdict"]["O_T"]["killed"]]
    sentinel5 = {"holds": not s5_bad, "targets": s5_targets, "undetected": s5_bad}

    # ---- predictions
    reached_deletions = [d for d in deletions if deletions[d]["reached"]]
    p2a = [d for d in reached_deletions if not deletions[d]["verdict"]["O_V"]["killed"]]
    p2b = []
    for d in reached_deletions:
        if deletions[d]["verdict"]["O_C"]["killed"]:
            continue
        cls = CHECK_BY_ID[d]["class"]
        ok = True
        for cid in reached[d]:
            kind, rec = deletions[d]["state"]["cases"][cid]
            site = (rec or {}).get("site") or {}
            other = site.get("check")
            if not (kind == "observed" and rec.get("class") == cases[cid]["B"] and other not in (None, d)
                    and CHECK_BY_ID.get(other, {}).get("class") == cls):
                ok = False
        if ok:
            p2b.append(d)
    p2c = [d for d in reached_deletions
           if deletions[d]["verdict"]["O_V"]["killed"] and not deletions[d]["verdict"]["O_V_fc"]["killed"]]
    p3 = sorted(kills["O_T"] - kills["O_C"])
    gap_cv = kills["O_C"] - kills["O_V"]
    p4 = {"strict_subset": kills["O_V"] < kills["O_C"], "gap": len(gap_cv), "killed_O_C": len(kills["O_C"]),
          "share": share(len(gap_cv), len(kills["O_C"]))}
    p5_rows, p5_fail = [], []
    for cid in sorted(s["O_T"]):
        target = cases[cid]["target"]
        check = CHECK_BY_ID[target]
        if not check["mutated"]:
            continue
        own = [k for k in subject_keys if results[k]["function"] == check["function"]
               and cid in results[k]["verdict"]["O_T"]["cases"]]
        p5_rows.append({"case": cid, "target": target, "function": check["function"], "kills_O_T": len(own)})
        if not own:
            p5_fail.append(cid)
    predictions = {
        "P1": {"held": all(p1_parts.values()), "parts": p1_parts, "O_T_misses": o_t_misses},
        "P2": {"held": bool(p2a) and bool(p2b) and bool(p2c),
               "a_undetected_O_V": p2a, "b_undetected_O_C_same_class": p2b, "c_O_V_only_non_PyJWTError": p2c,
               "reached": len(reached_deletions), "deletions": len(deletions)},
        "P3": {"held": bool(p3), "killed_O_T_not_O_C": p3},
        "P4": {"held": p4["strict_subset"] and (p4["share"] or 0) >= 0.10, **p4},
        "P5": {"held": not p5_fail, "cases": len(p5_rows), "failing": p5_fail},
    }

    # ---- measures
    totals = {}
    for o in ORACLES + EXPLORATORY:
        totals[NAMES[o]] = {"killed": len(kills[o]), "survived": n - len(kills[o]), "score": share(len(kills[o]), n)}
    crosstab = {NAMES[o]: dict(Counter(f"{results[k]['tool']}/{'killed' if k in kills[o] else 'survived'}"
                                       for k in subject_keys)) for o in ORACLES}
    gaps = {
        "O_C - O_V": len(gap_cv), "share of O_C": share(len(gap_cv), len(kills["O_C"])),
        "O_T - O_C": len(kills["O_T"] - kills["O_C"]), "O_C - O_T": len(kills["O_C"] - kills["O_T"]),
        "O_S - O_C": len(kills["O_S"] - kills["O_C"]), "O_C - O_S": len(kills["O_C"] - kills["O_S"]),
        "O_S - O_V": len(kills["O_S"] - kills["O_V"]), "O_V - O_S": len(kills["O_V"] - kills["O_S"]),
    }
    rest = set(subject_keys) - exc_arg
    gaps_without_exc_arg = {
        "mutants": len(rest), "exception_argument_mutants": len(exc_arg),
        "O_C - O_V": len((kills["O_C"] - kills["O_V"]) & rest),
        "share of O_C": share(len((kills["O_C"] - kills["O_V"]) & rest), len(kills["O_C"] & rest)),
        "O_S - O_C": len((kills["O_S"] - kills["O_C"]) & rest), "O_C - O_S": len((kills["O_C"] - kills["O_S"]) & rest),
        "O_S - O_V": len((kills["O_S"] - kills["O_V"]) & rest), "O_V - O_S": len((kills["O_V"] - kills["O_S"]) & rest),
        **{f"killed {NAMES[o]}": len(kills[o] & rest) for o in ORACLES},
    }
    move_totals = Counter()
    move_mutants = Counter()
    for k in subject_keys:
        mv = results[k]["moves"]
        move_totals.update(mv)
        for kind in ("later", "earlier", "no check", "no exception", "unordered"):
            if mv.get(kind):
                move_mutants[kind] += 1
    # PROTOCOL.md, "Moves": the sets it names
    moves_by_set = {}
    for name, keys in (("O_C - O_V", gap_cv), ("O_T - O_C", kills["O_T"] - kills["O_C"])):
        case_runs, with_kind = Counter(), Counter()
        for k in keys:
            mv = results[k]["moves"]
            case_runs.update({kind: v for kind, v in mv.items() if kind != "same"})
            with_kind.update(kind for kind, v in mv.items() if kind != "same" and v)
        moves_by_set[name] = {"mutants": len(keys), "case_runs": dict(case_runs), "mutants_with": dict(with_kind)}
    del_moves = Counter()
    for d in reached_deletions:
        del_moves.update({kind: v for kind, v in deletions[d]["moves"].items() if kind != "same"})
    moves_by_set["deletions of reached checks"] = {"deletions": len(reached_deletions), "case_runs": dict(del_moves)}

    # per function / operator
    function_rows = []
    for rel in MUTATED:
        for fn in CHECKS["subject_functions"][rel]:
            keys = [k for k in subject_keys if results[k]["function"] == fn]
            function_rows.append({"file": rel, "function": fn, "mutants": len(keys),
                                  **{NAMES[o]: len([k for k in keys if k in kills[o]]) for o in ORACLES},
                                  "mutmut": len([k for k in keys if k in tool_killed])})
    operator_rows = []
    for op in sorted({results[k]["operator"] for k in subject_keys}):
        keys = [k for k in subject_keys if results[k]["operator"] == op]
        operator_rows.append({"operator": op, "mutants": len(keys),
                              "exception_argument": len([k for k in keys if k in exc_arg]),
                              **{NAMES[o]: len([k for k in keys if k in kills[o]]) for o in ORACLES}})

    # per case
    case_rows = []
    for cid, c in cases.items():
        row = {"case": cid, "file": c["file"], "expected": c["expected"], "baseline_class": c["B"],
               "baseline_site": c["site"], "baseline_segment": c["site_segment"],
               "target": c["target"], "target_segment": c["segment"], "labelled": yn(c["labelled"]),
               "O_T_at_baseline": yn(cid in s["O_T"]), "message": c["message"]}
        for o in ORACLES:
            killed_by = [k for k in subject_keys if cid in results[k]["verdict"][o]["cases"]]
            unique = [k for k in killed_by if results[k]["verdict"][o]["cases"] == [cid]]
            row[f"{NAMES[o]} kills"] = len(killed_by)
            row[f"{NAMES[o]} unique"] = len(unique)
        case_rows.append(row)
    unlabelled = [{"case": cid, "site": c["site"], "segment": c["site_segment"], "class": c["B"],
                   "reason": INCLUDED[c["key"]]["label"].get("reason")}
                  for cid, c in cases.items() if not c["labelled"]]

    # exploratory: mutmut's whole-suite score, withheld sensitivity
    all_status = Counter(MUTMUT_STATUS.get(m["exit_code"], f"exit {m['exit_code']}") for m in listed)
    tool_all = Counter(TOOL_CLASS.get(st, "excluded") for st in
                       (MUTMUT_STATUS.get(m["exit_code"], "?") for m in listed))
    exploratory = {
        "O_CM": {"killed": len(kills["O_CM"]), "O_CM - O_C": len(kills["O_CM"] - kills["O_C"]),
                 "O_S - O_CM": len(kills["O_S"] - kills["O_CM"]), "O_CM - O_S": len(kills["O_CM"] - kills["O_S"])},
        "mutmut": {"generated": len(listed), "statuses": dict(all_status), "classes": dict(tool_all),
                   "score_all": share(tool_all["killed"], tool_all["killed"] + tool_all["survived"]),
                   "subject_generated": n, "subject_killed": len(tool_killed),
                   "subject_score": share(len(tool_killed), n - len(excluded)), "subject_excluded": len(excluded)},
        "withheld_as_failing": {NAMES[o]: {"killed": len(kills_withheld[o]),
                                           "added": len(kills_withheld[o] - kills[o])} for o in ORACLES},
        "unlabelled_cases": unlabelled,
        "runs": Counter(results[k]["state"] for k in subject_keys),
    }

    outcomes.write()
    write_csv("mutants.csv", rows)
    write_csv("deletions.csv", deletion_rows)
    write_csv("deletion-cases.csv", deletion_case_rows)
    write_csv("cases.csv", case_rows)
    write_csv("functions.csv", function_rows)
    write_csv("operators.csv", operator_rows)
    write_csv("p5.csv", p5_rows)

    def run(cmd: list[str]) -> str:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()

    environment = {
        "python": platform.python_version(), "platform": platform.platform(), "cpu_count": os.cpu_count(),
        "mutmut": run([sys.executable, "-I", "-c", "import importlib.metadata as m; print(m.version('mutmut'))"]),
        "pytest": run([sys.executable, "-I", "-c", "import importlib.metadata as m; print(m.version('pytest'))"]),
        "subject": CHECKS["subject"], "timeout": timeout,
        "mutmut_run": load(RECORDS / "mutmut.json"),
        "experiment_sources_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in SOURCES},
    }
    (GENERATED / "environment.json").write_text(json.dumps(environment, indent=1) + "\n", encoding="utf-8")
    (GENERATED / "pip-freeze.txt").write_text((WORK / "pip-freeze.txt").read_text(encoding="utf-8"),
                                             encoding="utf-8")
    summary = {
        "schema": "urn:eatf:experiment:mutation-adequacy-pyjwt-results:1",
        "subject": CHECKS["subject"],
        "cases": {"blocks": len(INCLUDED), "cases": len(cases), "labelled": len(labelled),
                  "S": {NAMES[o]: len(s[o]) for o in ORACLES + EXPLORATORY}},
        "checks": {"in_mutated_files": len(deletions), "reached": len(reached_deletions),
                   "external": len([c for c in CHECKS["checks"] if not c["mutated"]])},
        "totals": totals, "tool_context": crosstab, "gaps": gaps, "gaps_without_exception_argument": gaps_without_exc_arg,
        "moves": {"case_runs": dict(move_totals), "mutants_with": dict(move_mutants), "by_set": moves_by_set},
        "deletions": {d: {"reached": v["reached"], **{NAMES[o]: v["verdict"][o]["killed"] for o in ORACLES}}
                      for d, v in deletions.items()},
        "predictions": predictions,
        "sentinels": {"1": sentinel1, "2": sentinel2, "3": sentinel3, "4": sentinel4, "5": sentinel5},
        "exploratory": exploratory,
    }
    (GENERATED / "summary.json").write_text(json.dumps(summary, indent=1, default=list) + "\n", encoding="utf-8")
    report = render(summary, deletion_rows, function_rows, operator_rows)
    (GENERATED / "SUMMARY.md").write_text(report, encoding="utf-8")
    files = sorted(f for f in GENERATED.iterdir() if f.is_file() and f.name != "SHA256SUMS")
    (GENERATED / "SHA256SUMS").write_text(
        "".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in files), encoding="ascii")
    print(report)
    ok = (all(sentinel1.values()) and all(v for k, v in sentinel2.items() if isinstance(v, bool))
          and all(all(x.values()) for x in sentinel3.values()) and sentinel4["holds"] and sentinel5["holds"])
    print("sentinels:", "pass" if ok else "FAIL")
    return 0 if ok else 1


def render(summary: dict, deletion_rows: list[dict], function_rows: list[dict], operator_rows: list[dict]) -> str:
    sub = summary["subject"]
    c = summary["cases"]
    p = summary["predictions"]
    t = summary["totals"]
    n = t["O_V"]["killed"] + t["O_V"]["survived"]
    out = [
        "# Mutation adequacy of PyJWT's negative tests: results", "",
        f"Subject {sub['name']} {sub['version']} (`{sub['commit'][:10]}`, {sub['licence']}). "
        f"Cases: {c['cases']} runs of {c['blocks']} included `pytest.raises` blocks; "
        f"{c['labelled']} cases have a target.", "",
        "Generated by `analyse_s2.py`; every number below is in `summary.json` or a CSV here.", "",
        "## Predictions", "",
    ]
    for name in ("P1", "P2", "P3", "P4", "P5"):
        out.append(f"- {name}: {'held' if p[name]['held'] else 'refuted'}")
    p1 = p["P1"]
    out += ["", "P1 parts: " + "; ".join(f"{k.replace('_', ' ')}: {'yes' if v else 'no'}"
                                          for k, v in p1["parts"].items())]
    for miss in p1["O_T_misses"]:
        out.append(f"- O_T fails at baseline on `{miss['case']}`: target {miss['target']}, "
                   f"raised by {miss['site']} (\"{miss['message']}\")")
    p2 = p["P2"]
    out += ["", f"P2 (among {p2['reached']} reached of {p2['deletions']} deletions): "
                f"(a) undetected under O_V: {', '.join(p2['a_undetected_O_V']) or 'none'}; "
                f"(b) undetected under O_C, cases rejected by another check of the same class: "
                f"{', '.join(p2['b_undetected_O_C_same_class']) or 'none'}; "
                f"(c) detected under O_V only through other exceptions: "
                f"{', '.join(p2['c_O_V_only_non_PyJWTError']) or 'none'}.",
            "", f"P3: {len(p['P3']['killed_O_T_not_O_C'])} subject mutants killed under O_T and not under O_C.",
            f"P4: O_C − O_V = {p['P4']['gap']} of {p['P4']['killed_O_C']} "
            f"({100 * (p['P4']['share'] or 0):.1f}%); strict subset: {'yes' if p['P4']['strict_subset'] else 'no'}.",
            f"P5: {p['P5']['cases']} cases; failing: {', '.join(p['P5']['failing']) or 'none'}.", "",
            "## Subject mutants", "",
            "| Oracle | Killed | Survived | Score |", "|---|---|---|---|"]
    for o, v in t.items():
        out.append(f"| {o} | {v['killed']} | {v['survived']} | {pct(v['killed'], n)} |")
    g, gw = summary["gaps"], summary["gaps_without_exception_argument"]
    out += ["", "## Gaps", "",
            "| Measure | All subject mutants | Without exception-argument mutants |", "|---|---|---|",
            f"| Mutants | {n} | {gw['mutants']} |",
            f"| O_C − O_V | {g['O_C - O_V']} ({100 * (g['share of O_C'] or 0):.1f}% of O_C) | "
            f"{gw['O_C - O_V']} ({100 * (gw['share of O_C'] or 0):.1f}% of O_C) |",
            f"| O_T − O_C | {g['O_T - O_C']} | |", f"| O_C − O_T | {g['O_C - O_T']} | |",
            f"| O_S − O_C | {g['O_S - O_C']} | {gw['O_S - O_C']} |", f"| O_C − O_S | {g['O_C - O_S']} | {gw['O_C - O_S']} |",
            f"| O_S − O_V | {g['O_S - O_V']} | {gw['O_S - O_V']} |", f"| O_V − O_S | {g['O_V - O_S']} | {gw['O_V - O_S']} |",
            "", "## Check deletions", "",
            "| Check | Function | Class | Reached | O_V | O_V^fc | O_C | O_T | O_S | Cases changed | Moves |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in deletion_rows:
        out.append(f"| {r['check']} | {r['function']} | {r['class']} | {r['reached']} | {r['O_V']} | {r['O_V^fc']} | "
                   f"{r['O_C']} | {r['O_T']} | {r['O_S']} | {r['cases_changed']} | {r['moves']} |")
    out += ["", "## Functions", "", "| Function | Mutants | O_V | O_V^fc | O_C | O_T | O_S | mutmut |",
            "|---|---|---|---|---|---|---|---|"]
    for r in function_rows:
        out.append(f"| {r['function']} | {r['mutants']} | {r['O_V']} | {r['O_V^fc']} | {r['O_C']} | {r['O_T']} | "
                   f"{r['O_S']} | {r['mutmut']} |")
    out += ["", "## Operators", "", "| Operator | Mutants | Exception-argument | O_V | O_V^fc | O_C | O_T | O_S |",
            "|---|---|---|---|---|---|---|---|"]
    for r in operator_rows:
        out.append(f"| {r['operator']} | {r['mutants']} | {r['exception_argument']} | {r['O_V']} | {r['O_V^fc']} | "
                   f"{r['O_C']} | {r['O_T']} | {r['O_S']} |")
    sen = summary["sentinels"]
    ex = summary["exploratory"]
    out += ["", "## Sentinels", "",
            f"1. Same records apart from timing: " + "; ".join(f"{k}: {'yes' if v else 'no'}" for k, v in sen["1"].items()),
            f"2. Case tests pass: {yn(sen['2']['case_tests_pass'])}; pytest's check passes on every block: "
            f"{yn(sen['2']['pytest_check_passes_on_every_block'])}; every included block runs: "
            f"{yn(sen['2']['every_included_block_runs'])}; suite without the recorder: {sen['2']['suite_summary']}",
            "3. Subsets: " + "; ".join(f"{scope} {k}: {'yes' if v else 'no'}" for scope, d in sen["3"].items()
                                       for k, v in d.items()),
            f"4. Every mutant killed under O_S is killed by mutmut: {yn(sen['4']['holds'])}"
            + (f" (not: {', '.join(sen['4']['killed_under_O_S_not_by_mutmut'])})" if not sen['4']['holds'] else ""),
            f"5. Every deletion of a target is detected under O_T: {yn(sen['5']['holds'])}"
            + (f" (not: {', '.join(sen['5']['undetected'])})" if not sen['5']['holds'] else ""),
            "", "## Exploratory", "",
            f"- mutmut, whole suite: {ex['mutmut']['generated']} mutants, statuses {ex['mutmut']['statuses']}, "
            f"score {100 * (ex['mutmut']['score_all'] or 0):.1f}%; subject functions: {ex['mutmut']['subject_killed']} "
            f"of {ex['mutmut']['subject_generated']} killed.",
            f"- O_CM (class and message equal to the baseline): {ex['O_CM']['killed']} killed; "
            f"O_S − O_CM {ex['O_CM']['O_S - O_CM']}, O_CM − O_S {ex['O_CM']['O_CM - O_S']}.",
            "- Withheld cases counted as failing: " + "; ".join(
                f"{o} +{v['added']}" for o, v in ex["withheld_as_failing"].items()),
            f"- Moves of the raise site, all subject mutants (case runs): {summary['moves']['case_runs']}; "
            f"mutants with at least one: {summary['moves']['mutants_with']}.",
            *[f"- Moves, {name}: {v}" for name, v in summary["moves"]["by_set"].items()],
            "- Unlabelled cases, rejected at baseline by: " + "; ".join(
                f"`{u['case'].split('|')[1]}` {u['site']}" + (f":{u['segment']}" if u["segment"] else "")
                for u in ex["unlabelled_cases"]),
            ""]
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())

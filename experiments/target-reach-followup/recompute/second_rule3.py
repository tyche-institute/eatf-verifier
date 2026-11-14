"""Second computation of rule 3 and its analysis, for 1 subject.

    python3 -I -B recompute/second_rule3.py \
        --subject ../target-reach/subjects/<name>/subject.json \
        --records ../target-reach/generated/<name>/records.tar.xz \
        --reach FILE.json --out FILE.json [--targets-out FILE.json] \
        [--class-a ID [ID ...]] [--toolkit DIR]

Inputs:

- `--subject`: the toolkit subject; `checks.json`, `blocks.json` and
  `targets.json` (the deposited targets of rule 2) are read beside it.
- `--records`: the deposited records of the toolkit (`records.tar.xz`, or a
  directory unpacked from it): `base-1.json`, `base-2.json` and the deletion
  records under `deletions/`.
- `--reach`: the trace output `reach.json` (per function of `checks.json`
  that started in the traced whole-suite run, the entry-point names under
  which it started).
- `--class-a` (optional): identifiers of the class-A cases for expectation T2,
  each a case key (`test|block|index`) or a block key (all cases of the block).
- `--toolkit` (optional): the toolkit directory; the default is
  `../../target-reach` relative to this file. Its `reach/targets.py` scores
  the candidates (the rule code is used as it is), and its
  `recompute/second.py` gives the case and oracle counts of the toolkit
  under the rule-3 targets.

Output (`--out`): 1 JSON file, sorted keys, 2-space indentation. Groups, with
the section of PROTOCOL.md of the follow-up that defines each:

- `reachability` (section 4.2, 'Rule 3' and 'Analysis'): the checks reachable
  by name (the candidates of rule 2), by execution, by both, by execution
  only, by name only, and under rule 3 (by name or by execution), over all
  checks and over the checks of the subject files; per check, its entry
  points.
- `rule2_recomputed` (section 4.2, 'Rule 3': "The code of the rule ... is
  unchanged"): whether the rule code on the unchanged `checks.json` gives the
  deposited `targets.json` byte for byte.
- `blocks` (section 4.2): the target, basis and tier of every included block
  under rule 2 and rule 3, the counts per tier and per basis, and the block
  transitions.
- `cases` (section 4.2, 'Analysis'): per case of the study, the deciding check
  (from the deposited records), and under each rule the target, basis, tier,
  whether the target decides the case, the outcome of a case with a target
  (toolkit protocol, section 4) and the outcome of section 4.1 with the
  target in place of the label; the transition between the rules.
- `counts` (section 4.2, 'Analysis'; section 2, the note on the rule): per
  rule, the cases with a target, decided by it and not decided by it (flags),
  overall, per tier and per basis, with the outcomes.
- `transitions` (section 4.2, 'Analysis'; section 2, the note on the rule):
  the cases that gain, keep, change and lose a target, and those with no
  target under either rule; of each kind, those that the target decides
  under rule 2 and under rule 3; the tier transitions; and what becomes of
  the flags of rule 2.
- `expectations` (section 2, T1, T2, T3): the quantities in the form the
  protocol states them for joserfc, computed for the subject.
- `fired_functions` (trace README, sentinel T2): per check that fires in a
  case of an included block in either baseline record, where its function
  started in the trace.
- `toolkit_second_under_rule3`: from `recompute/second.py` of the toolkit
  run on the rule-3 targets, the outcomes of the cases with a target, the
  O_T detections and the own test on the copy without the target.
- `inputs`: the digests of the inputs and the sentinels that `reach.json`
  states.

`--targets-out` writes the output of the rule code under rule 3, with
`rule_version` `reach-target-rule/3` and a field `variant`.

Exit status: 0 after writing the output; 2 with a message when an input is
missing or malformed, or when `reach.json` does not belong to the subject.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import importlib.util
import json
import shutil
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TOOLKIT = HERE.parent.parent / "target-reach"

NO_TARGET = "no target"
TIERS = ("assertion", "name")

OUTCOME4 = ("the target decides the case",
            "the target fires and another check decides",
            "the target fires and no check decides",
            "the target does not fire",
            "not decided by the target")

OUTCOME8 = ("1 decided by the target",
            "2 target fires and another check decides",
            "3 target fires and no check decides",
            "4 target does not fire and no check decides",
            "5 deciding check not deleted or record missing",
            "6 target does not fire; case not observed on the copy without the deciding check",
            "7 target does not fire and decides once the deciding check is deleted",
            "8 target does not fire and does not decide then either",
            "fired checks not recorded")

TRANSITIONS = ("gains a target", "keeps its target", "changes its target", "loses its target",
               "no target under either rule")

# Values that PROTOCOL.md, section 2, states for joserfc.
STATED_JOSERFC = {"T1_rule2_flags": 60, "T1_rule3_flags_at_most": 10,
                  "T3_share_at_least": 0.85, "T3_rule2": [71, 131]}


class InputError(Exception):
    """An input is missing or malformed."""


# -- loading -------------------------------------------------------------------------

def load_json(path: Path, what: str):
    path = Path(path)
    if not path.is_file():
        raise InputError(f"{what} is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"{what} is not readable JSON: {path}: {exc}") from exc


def need(doc, keys, what: str) -> None:
    if not isinstance(doc, dict):
        raise InputError(f"{what} is not a JSON object")
    absent = [k for k in keys if k not in doc]
    if absent:
        raise InputError(f"{what} lacks the field(s) {absent}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def records_root(arg: str, keep: list) -> Path:
    """The directory that holds `base-1.json`: the given directory (or its
    `records/` folder), or a temporary directory into which the archive is
    unpacked. Members are checked so that nothing lands outside it."""
    p = Path(arg)
    if p.is_dir():
        root = p
    elif p.is_file():
        tmp = tempfile.TemporaryDirectory()
        keep.append(tmp)
        try:
            with tarfile.open(p, "r:*") as tar:
                for m in tar.getmembers():
                    parts = Path(m.name).parts
                    if m.name.startswith("/") or ".." in parts or not (m.isfile() or m.isdir()):
                        raise InputError(f"unexpected member in the records archive: {m.name}")
                tar.extractall(tmp.name, filter="data")
        except (tarfile.TarError, OSError, EOFError) as exc:
            raise InputError(f"the records archive cannot be read: {p}: {exc}") from exc
        root = Path(tmp.name)
    else:
        raise InputError(f"the records are missing: {p}")
    if (root / "records").is_dir():
        root = root / "records"
    for rel in ("base-1.json", "base-2.json"):
        if not (root / rel).is_file():
            raise InputError(f"the records lack {rel}")
    return root


def import_toolkit(toolkit: Path):
    """The rule module `reach.targets` and the module `recompute/second.py`."""
    if not (toolkit / "reach" / "targets.py").is_file():
        raise InputError(f"the toolkit is missing: {toolkit / 'reach' / 'targets.py'}")
    if str(toolkit) not in sys.path:
        sys.path.insert(0, str(toolkit))
    targets = importlib.import_module("reach.targets")
    spec = importlib.util.spec_from_file_location("toolkit_second", toolkit / "recompute" / "second.py")
    if spec is None or spec.loader is None:
        raise InputError("the toolkit's recompute/second.py cannot be loaded")
    second = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(second)
    return targets, second


def dump_like_runner(doc) -> str:
    """The serialization that the toolkit's runner gives targets.json."""
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


# -- cases -----------------------------------------------------------------------------

def case_key(c: dict) -> str:
    return f"{c['test']}|{c['block']}|{c['index']}"


def decider(c: dict) -> str | None:
    """The deciding check: the check whose raise statement holds the raise site."""
    site = c.get("site")
    if site and site.get("kind") == "check" and site.get("check"):
        return site["check"]
    return None


def is_case_of_the_study(c: dict) -> bool:
    """An execution of an included block that raises an exception of a rejection
    class that the block's own check accepts (toolkit protocol, section 4, 'Case')."""
    return bool(c.get("included") and c.get("raised") and c.get("rejection")
                and c.get("check_result") == "accepted")


def outcome4(target: str, c: dict) -> str:
    """Toolkit protocol, section 4, 'Outcome of a case with a target'."""
    d = decider(c)
    if d == target:
        return OUTCOME4[0]
    fired = c.get("fired")
    if fired is None:
        return OUTCOME4[4]
    if target in fired:
        return OUTCOME4[1] if d is not None else OUTCOME4[2]
    return OUTCOME4[3]


class DeletionRuns:
    """The deposited recorder runs of the deletion copies, read on demand."""

    def __init__(self, root: Path) -> None:
        self.root = root
        mpath = root / "deletions" / "manifest.json"
        self.manifest = load_json(mpath, "deletions/manifest.json") if mpath.is_file() else {}
        npath = root / "deletions" / "no-record.json"
        self.no_record = load_json(npath, "deletions/no-record.json") if npath.is_file() else {}
        self.cache: dict[str, dict | None] = {}

    def cases(self, check: str) -> dict | None:
        """case key -> case of the run without `check`, or None when the check
        was not deleted or its run gave no record."""
        if check in self.cache:
            return self.cache[check]
        out = None
        if check in self.manifest and check not in self.no_record:
            path = self.root / "deletions" / f"{self.manifest[check]['dir']}.json"
            if path.is_file():
                rec = load_json(path, f"deletion record {path.name}")
                out = {case_key(x): x for x in rec.get("cases", []) if x.get("included")}
        self.cache[check] = out
        return out


def outcome8(target: str, c: dict, runs: DeletionRuns) -> tuple[str, dict]:
    """Follow-up protocol, section 4.1, 'Outcome of a case with an agreed label
    that names a check', with the target in place of the label. Returns the
    outcome and the detail of the copy without the deciding check."""
    d = decider(c)
    detail: dict = {}
    if d == target:
        return OUTCOME8[0], detail
    fired = c.get("fired")
    if fired is None:
        return OUTCOME8[8], detail
    if target in fired:
        return (OUTCOME8[1] if d is not None else OUTCOME8[2]), detail
    if d is None:
        return OUTCOME8[3], detail
    run = runs.cases(d)
    if run is None:
        return OUTCOME8[4], detail
    r = run.get(case_key(c))
    if r is None:
        return OUTCOME8[5], detail
    detail = {"deciding_check_on_the_copy_without_the_deciding_check": decider(r),
              "raises_a_rejection_class_there": bool(r.get("raised") and r.get("rejection")),
              "own_check_of_the_block_there": r.get("check_result")}
    if decider(r) == target:
        return OUTCOME8[6], detail
    return OUTCOME8[7], detail


# -- the computation ------------------------------------------------------------------

def tier_label(row: dict | None) -> str:
    if not row or not row.get("target"):
        return NO_TARGET
    return row.get("tier") or NO_TARGET


def transition_of(t2: str | None, t3: str | None) -> str:
    if t2 is None and t3 is None:
        return TRANSITIONS[4]
    if t2 is None:
        return TRANSITIONS[0]
    if t3 is None:
        return TRANSITIONS[3]
    return TRANSITIONS[1] if t2 == t3 else TRANSITIONS[2]


def check_reach_json(reach: dict, subject: dict, checks_doc: dict) -> None:
    """reach.json belongs to the subject: same name, same files, same entry
    points, and every function it lists is a function of checks.json."""
    need(reach, ("subject", "files", "entry_points", "functions"), "reach.json")
    if reach["subject"] != subject["name"]:
        raise InputError(f"reach.json is of subject {reach['subject']!r}, not {subject['name']!r}")
    if sorted(reach["files"]) != sorted(checks_doc["sha256"]):
        raise InputError("reach.json names other files than checks.json (field sha256)")
    if sorted(reach["entry_points"]) != sorted(subject["entry_points"]):
        raise InputError("reach.json names other entry points than subject.json")
    known = {(f["file"], f["function"]) for f in checks_doc["functions"]}
    if not isinstance(reach["functions"], list):
        raise InputError("reach.json: the field functions is not a list")
    unknown = []
    for i, row in enumerate(reach["functions"]):
        need(row, ("file", "function", "entry_points"), f"reach.json functions[{i}]")
        if (row["file"], row["function"]) not in known:
            unknown.append(f"{row['file']}::{row['function']}")
    if unknown:
        raise InputError(f"reach.json lists functions that checks.json does not: {unknown[:10]}")


def reachability(checks_doc: dict, reach: dict) -> tuple[dict, set]:
    started = {}
    for row in reach["functions"]:
        started[(row["file"], row["function"])] = sorted(row["entry_points"])
    under_ep = {k for k, eps in started.items() if eps}
    checks = checks_doc["checks"]
    subject_ids = {c["id"] for c in checks if c["role"] == "subject"}
    by_name = {c["id"] for c in checks if c["reachable"]}
    by_exec = {c["id"] for c in checks if (c["file"], c["function"]) in under_ep}
    rule3 = by_name | by_exec
    sets = {
        "reachable_by_name_rule2_candidates": by_name,
        "reachable_by_execution": by_exec,
        "reachable_by_both": by_name & by_exec,
        "reachable_by_execution_only": by_exec - by_name,
        "reachable_by_name_only": by_name - by_exec,
        "reachable_under_rule3_candidates": rule3,
        "reachable_under_neither": {c["id"] for c in checks} - rule3,
    }
    fn_name = {(f["file"], f["function"]) for f in checks_doc["functions"] if f["reachable"]}
    out = {
        "checks": len(checks),
        "checks_in_subject_files": len(subject_ids),
        "counts_all_checks": {k: len(v) for k, v in sets.items()},
        "counts_checks_in_subject_files": {k: len(v & subject_ids) for k, v in sets.items()},
        "ids": {k: sorted(v) for k, v in sets.items()},
        "functions": {
            "functions_in_checks_json": len(checks_doc["functions"]),
            "reachable_by_name": len(fn_name),
            "started_in_the_traced_run": len(started),
            "started_under_an_entry_point": len(under_ep),
            "started_under_an_entry_point_and_not_reachable_by_name": sorted(
                f"{f}::{fn}" for f, fn in under_ep - fn_name),
            "started_only_under_no_entry_point": sorted(
                f"{f}::{fn}" for f, fn in set(started) - under_ep),
        },
        "per_check": {c["id"]: {"file": c["file"], "function": c["function"], "role": c["role"],
                                "by_name": c["id"] in by_name, "by_execution": c["id"] in by_exec,
                                "rule3": c["id"] in rule3,
                                "started": (c["file"], c["function"]) in started,
                                "entry_points": started.get((c["file"], c["function"]), [])}
                      for c in checks},
    }
    return out, by_exec


def block_part(blocks_doc: dict, rows2: dict, rows3: dict) -> dict:
    included = [b["key"] for b in blocks_doc["blocks"] if b["included"]]
    per_block, trans = {}, {t: [] for t in TRANSITIONS}
    by_rule = {}
    for rule, rows in (("rule2", rows2), ("rule3", rows3)):
        with_t = [k for k in included if rows.get(k, {}).get("target")]
        by_rule[rule] = {
            "included_blocks": len(included),
            "blocks_with_a_target": len(with_t),
            "blocks_with_a_target_by_tier": {t: sum(1 for k in with_t if rows[k]["tier"] == t) for t in TIERS},
            "blocks_by_basis_or_reason": dict(sorted(Counter(
                (rows.get(k) or {}).get("basis") or f"none: {(rows.get(k) or {}).get('reason')}"
                for k in included).items())),
        }
    for k in included:
        r2, r3 = rows2.get(k) or {}, rows3.get(k) or {}
        tr = transition_of(r2.get("target"), r3.get("target"))
        trans[tr].append(k)
        per_block[k] = {"rule2": {"target": r2.get("target"), "basis": r2.get("basis"),
                                  "tier": tier_label(r2), "reason": r2.get("reason")},
                        "rule3": {"target": r3.get("target"), "basis": r3.get("basis"),
                                  "tier": tier_label(r3), "reason": r3.get("reason")},
                        "transition": tr}
    return {"by_rule": by_rule, "per_block": per_block,
            "transitions": {t: {"count": len(v), "ids": sorted(v)} for t, v in trans.items()}}


def count_rule(cases: dict, rule: str) -> dict:
    """Cases with a target, decided by it and not decided by it, overall, per
    tier and per basis, with the outcomes."""
    def summary(keys: list[str]) -> dict:
        dec = sorted(k for k in keys if cases[k][rule]["decides"])
        nd = sorted(k for k in keys if not cases[k][rule]["decides"])
        return {"cases_with_a_target": len(keys), "decided_by_the_target": len(dec),
                "not_decided_by_the_target": len(nd), "decided_ids": dec, "not_decided_ids": nd}

    with_t = sorted(k for k, c in cases.items() if c[rule]["target"])
    out = summary(with_t)
    out["cases_without_a_target"] = len(cases) - len(with_t)
    out["cases_without_a_target_ids"] = sorted(k for k, c in cases.items() if not c[rule]["target"])
    out["by_tier"] = {t: summary([k for k in with_t if cases[k][rule]["tier"] == t]) for t in TIERS}
    bases = sorted({cases[k][rule]["basis"] for k in with_t})
    out["by_basis"] = {b: summary([k for k in with_t if cases[k][rule]["basis"] == b]) for b in bases}
    for field, names in (("outcome", OUTCOME4), ("outcome_section_4_1", OUTCOME8)):
        ids = {n: sorted(k for k in with_t if cases[k][rule][field] == n) for n in names}
        out[f"{field}s"] = {n: {"count": len(v), "ids": v} for n, v in ids.items()}
        out[f"{field}s_by_tier"] = {t: {n: sum(1 for k in v if cases[k][rule]["tier"] == t)
                                        for n, v in ids.items()} for t in TIERS}
    return out


def transitions_part(cases: dict) -> dict:
    out = {}
    for tr in TRANSITIONS:
        keys = sorted(k for k, c in cases.items() if c["transition"] == tr)
        d2 = sorted(k for k in keys if cases[k]["rule2"]["decides"])
        d3 = sorted(k for k in keys if cases[k]["rule3"]["decides"])
        out[tr] = {"count": len(keys), "ids": keys,
                   "decided_by_the_rule2_target": len(d2), "decided_by_the_rule2_target_ids": d2,
                   "decided_by_the_rule3_target": len(d3), "decided_by_the_rule3_target_ids": d3}
    tiers = Counter((c["rule2"]["tier"], c["rule3"]["tier"]) for c in cases.values())
    matrix = {}
    for (a, b), n in sorted(tiers.items()):
        matrix.setdefault(f"rule2 {a}", {})[f"rule3 {b}"] = n
    flags2 = sorted(k for k, c in cases.items() if c["rule2"]["target"] and not c["rule2"]["decides"])
    flags_after = {}
    for k in flags2:
        c = cases[k]
        if not c["rule3"]["target"]:
            what = "no target under rule 3"
        elif c["rule3"]["decides"]:
            what = "target under rule 3 decides the case"
        else:
            what = "target under rule 3 does not decide the case"
        flags_after.setdefault(what, []).append(k)
    by_basis = {}
    for k, c in cases.items():
        b = c["rule2"]["basis"] or NO_TARGET
        by_basis.setdefault(b, Counter())[c["transition"]] += 1
    return {"cases": out,
            "tier_transitions": matrix,
            "transitions_by_rule2_basis": {b: dict(sorted(v.items())) for b, v in sorted(by_basis.items())},
            "rule2_flags_under_rule3": {w: {"count": len(v), "ids": sorted(v)}
                                        for w, v in sorted(flags_after.items())}}


def expectations(subject_name: str, cases: dict, counts: dict, class_a: list[str], blocks_of: dict) -> dict:
    """Section 2: T1, T2 and T3, as stated for joserfc, computed for the subject."""
    n2 = counts["rule2"]["not_decided_by_the_target"]
    n3 = counts["rule3"]["not_decided_by_the_target"]
    t1 = {"statement": "the number of cases whose target does not decide them falls from 60 under "
                       "rule 2 to 10 or fewer under rule 3 (stated for joserfc)",
          "rule2_cases_not_decided_by_their_target": n2,
          "rule3_cases_not_decided_by_their_target": n3,
          "falls": n3 < n2,
          "rule3_at_most_10": n3 <= 10,
          "holds": n3 <= 10 and n3 < n2}
    w3, d3 = counts["rule3"]["cases_with_a_target"], counts["rule3"]["decided_by_the_target"]
    w2, d2 = counts["rule2"]["cases_with_a_target"], counts["rule2"]["decided_by_the_target"]
    t3 = {"statement": "among the cases with a target under rule 3, at least 85% are decided by it "
                       "(stated for joserfc; under rule 2: 71 of 131, 54%)",
          "rule3_decided": d3, "rule3_with_a_target": w3,
          "rule3_share": round(d3 / w3, 6) if w3 else None,
          "rule2_decided": d2, "rule2_with_a_target": w2,
          "rule2_share": round(d2 / w2, 6) if w2 else None,
          "holds": (d3 * 100 >= 85 * w3) if w3 else None}

    def keep_table(keys: list[str]) -> dict:
        rows = {k: {"rule2_target": cases[k]["rule2"]["target"], "rule3_target": cases[k]["rule3"]["target"],
                    "keeps": bool(cases[k]["rule2"]["target"])
                    and cases[k]["rule2"]["target"] == cases[k]["rule3"]["target"]}
                for k in keys}
        return {"cases": rows, "count": len(rows), "keep": sum(1 for r in rows.values() if r["keeps"]),
                "holds": bool(rows) and all(r["keeps"] for r in rows.values())}

    # Cases that meet the condition of section 4.1, outcome 7, with the rule-2 target in
    # place of the label; section 4.1 says that the 3 class-A cases of joserfc meet it.
    shadow2 = sorted(k for k, c in cases.items() if c["rule2"]["outcome_section_4_1"] == OUTCOME8[6])
    given, unmatched = [], []
    for ident in class_a:
        if ident in cases:
            given.append(ident)
        elif ident in blocks_of:
            given += blocks_of[ident]
        else:
            unmatched.append(ident)
    t2 = {"statement": "the 3 class-A cases of joserfc keep their target under rule 3",
          "class_a_cases_given": keep_table(sorted(set(given))) if class_a else None,
          "class_a_identifiers_not_found": unmatched,
          "cases_meeting_outcome_7_with_the_rule2_target": keep_table(shadow2),
          "note": ("the class-A cases come from a reading (labels/first/<name>.tsv); without "
                   "--class-a, T2 is given on the cases that meet the condition of section 4.1, "
                   "outcome 7, with the rule-2 target, a set that holds every class-A case")}
    if not class_a:
        t2["holds"] = None
    else:
        t2["holds"] = t2["class_a_cases_given"]["holds"] and not unmatched
    out = {"T1": t1, "T2": t2, "T3": t3}
    if subject_name == "joserfc":
        out["stated_values_for_joserfc"] = {
            "T1_rule2_flags_equal_60": n2 == STATED_JOSERFC["T1_rule2_flags"],
            "T3_rule2_equal_71_of_131": [d2, w2] == STATED_JOSERFC["T3_rule2"]}
    return out


def fired_functions(base_docs: list[dict], checks_doc: dict, reach: dict) -> dict:
    by_id = {c["id"]: c for c in checks_doc["checks"]}
    started = {(r["file"], r["function"]): r for r in reach["functions"]}
    fired: dict[str, set] = {}
    for name, doc in base_docs:
        for c in doc.get("cases", []):
            if not c.get("included"):
                continue
            for chk in set(c.get("fired") or []) | ({decider(c)} - {None}):
                fired.setdefault(chk, set()).add(name)
    rows, status_ids = {}, {}
    for chk in sorted(fired):
        info = by_id.get(chk)
        if info is None:
            rows[chk] = {"status": "not a check of checks.json", "records": sorted(fired[chk])}
            status_ids.setdefault("not a check of checks.json", []).append(chk)
            continue
        r = started.get((info["file"], info["function"]))
        if r is None:
            st = "function did not start in the traced run"
        elif r["entry_points"]:
            st = "function started under an entry point"
        else:
            st = "function started only under no entry point"
        rows[chk] = {"file": info["file"], "function": info["function"], "status": st,
                     "entry_points": sorted(r["entry_points"]) if r else [],
                     "reachable_by_name": info["reachable"],
                     "tests_under_no_entry_point": (r or {}).get("tests_under_none", []),
                     "records": sorted(fired[chk])}
        status_ids.setdefault(st, []).append(chk)
    return {"checks": rows,
            "counts_by_status": {k: len(v) for k, v in sorted(status_ids.items())},
            "ids_by_status": {k: sorted(v) for k, v in sorted(status_ids.items())},
            "every_firing_function_started": "function did not start in the traced run" not in status_ids
            and "not a check of checks.json" not in status_ids}


def toolkit_second(second_mod, subject_path: Path, targets3: dict, root: Path) -> dict:
    """recompute/second.py of the toolkit on a definition folder whose targets.json
    holds the rule-3 targets; checks.json and blocks.json are copied unchanged."""
    with tempfile.TemporaryDirectory() as tmp:
        defs = Path(tmp)
        src = subject_path.parent
        for name in ("subject.json", "checks.json", "blocks.json"):
            shutil.copyfile(src / name, defs / name)
        (defs / "targets.json").write_text(dump_like_runner(targets3), encoding="utf-8")
        try:
            data = second_mod.compute(defs / "subject.json", root)
        except SystemExit as exc:
            raise InputError(f"the toolkit's second.py stopped: {exc}") from exc
    q2 = data["Q2"]
    return {
        "Q1": data["Q1"],
        "O_T_not_detected_deciding_checks": q2["not_detected_deciding_checks"]["O_T"],
        "O_T_not_detected_deciding_checks_ids": q2["not_detected_deciding_checks_ids"]["O_T"],
        "O_T_not_detected_checks_that_fire_and_never_decide":
            q2["not_detected_checks_that_fire_and_never_decide"]["O_T"],
        "O_T_not_detected_checks_that_fire_and_never_decide_ids":
            q2["not_detected_checks_that_fire_and_never_decide_ids"]["O_T"],
        "O_T_not_detected_deciding_checks_withheld_as_failing":
            q2["not_detected_deciding_checks_withheld_as_failing"]["O_T"],
        "own_test_without_the_target": data["Q3"]["own_test_without_the_target"],
        "E4": {k: v for k, v in data["expectations"]["E4"].items()
               if k in ("units", "count", "verdict_ignoring_sentinels")},
        "sentinels": data["sentinels"],
    }


def compute(args) -> tuple[dict, dict]:
    subject_path = Path(args.subject).resolve()
    subject = load_json(subject_path, "subject.json")
    need(subject, ("name", "entry_points"), "subject.json")
    defs = subject_path.parent
    checks_doc = load_json(defs / "checks.json", "checks.json")
    need(checks_doc, ("checks", "classes", "functions", "sha256"), "checks.json")
    blocks_doc = load_json(defs / "blocks.json", "blocks.json")
    need(blocks_doc, ("blocks",), "blocks.json")
    targets_path = defs / "targets.json"
    targets2 = load_json(targets_path, "targets.json")
    need(targets2, ("blocks", "rule_version"), "targets.json")
    reach_path = Path(args.reach)
    reach = load_json(reach_path, "reach.json")
    check_reach_json(reach, subject, checks_doc)

    keep: list = []
    root = records_root(args.records, keep)
    base1 = load_json(root / "base-1.json", "base-1.json")
    base2 = load_json(root / "base-2.json", "base-2.json")
    need(base1, ("cases",), "base-1.json")
    runs = DeletionRuns(root)

    targets_mod, second_mod = import_toolkit(Path(args.toolkit).resolve())

    # Rule 2 again from the unchanged definitions, against the deposited targets.json.
    recomputed2 = targets_mod.compute_targets(blocks_doc, checks_doc)
    rule2_equal = dump_like_runner(recomputed2).encode("utf-8") == targets_path.read_bytes()

    # Rule 3: the field `reachable` widened; nothing else of checks.json changes.
    reach_part, by_exec = reachability(checks_doc, reach)
    checks3 = copy.deepcopy(checks_doc)
    for c in checks3["checks"]:
        c["reachable"] = bool(c["reachable"]) or c["id"] in by_exec
    targets3 = targets_mod.compute_targets(blocks_doc, checks3)
    empty_exec = copy.deepcopy(checks_doc)
    same_without_execution = (dump_like_runner(targets_mod.compute_targets(blocks_doc, empty_exec))
                              == dump_like_runner(recomputed2))

    rows2 = {r["key"]: r for r in targets2["blocks"]}
    rows3 = {r["key"]: r for r in targets3["blocks"]}

    # Cases of the study and their targets under both rules.
    cases: dict[str, dict] = {}
    blocks_of: dict[str, list] = {}
    for c in base1["cases"]:
        if not is_case_of_the_study(c):
            continue
        k = case_key(c)
        entry = {"test": c["test"], "block": c["block"], "index": c["index"],
                 "deciding_check": decider(c),
                 "raise_site": c.get("site"),
                 "fired": sorted(c["fired"]) if c.get("fired") is not None else None}
        for rule, rows in (("rule2", rows2), ("rule3", rows3)):
            r = rows.get(c["block"]) or {}
            t = r.get("target")
            info = {"target": t, "basis": r.get("basis") if t else None, "tier": tier_label(r),
                    "decides": bool(t) and decider(c) == t}
            if t:
                info["outcome"] = outcome4(t, c)
                o8, detail = outcome8(t, c, runs)
                info["outcome_section_4_1"] = o8
                if detail:
                    info["copy_without_the_deciding_check"] = detail
            else:
                info["outcome"] = None
                info["outcome_section_4_1"] = None
            entry[rule] = info
        entry["transition"] = transition_of(entry["rule2"]["target"], entry["rule3"]["target"])
        cases[k] = entry
        blocks_of.setdefault(c["block"], []).append(k)

    counts = {"cases_of_the_study": len(cases),
              "rule2": count_rule(cases, "rule2"),
              "rule3": count_rule(cases, "rule3")}

    out = {
        "subject": subject["name"],
        "version": subject.get("version"),
        "protocol": "PROTOCOL.md of the follow-up, sections 2 (T1, T2, T3) and 4.2",
        "inputs": {
            "reach_json_sha256": sha256_file(reach_path),
            "targets_json_sha256": sha256_file(targets_path),
            "checks_json_sha256": sha256_file(defs / "checks.json"),
            "blocks_json_sha256": sha256_file(defs / "blocks.json"),
            "records_sha256": sha256_file(Path(args.records)) if Path(args.records).is_file() else None,
            "reach_json_sentinels": {s.get("name", "").split(":")[0]: bool(s.get("pass"))
                                     for s in reach.get("sentinels", [])},
            "reach_json_counts": reach.get("counts"),
            "rule_version_of_the_deposited_targets": targets2["rule_version"],
        },
        "rule2_recomputed": {
            "equals_deposited_targets_json_byte_for_byte": rule2_equal,
            "rule_code_with_an_empty_execution_set_equals_rule2": same_without_execution,
        },
        "reachability": reach_part,
        "blocks": block_part(blocks_doc, rows2, rows3),
        "cases": cases,
        "counts": counts,
        "transitions": transitions_part(cases),
        "expectations": expectations(subject["name"], cases, counts, args.class_a or [], blocks_of),
        "fired_functions": fired_functions([("base-1", base1), ("base-2", base2)], checks_doc, reach),
        "toolkit_second_under_rule3": toolkit_second(second_mod, subject_path, targets3, root),
    }
    # Internal agreement: the toolkit's second.py on the rule-3 targets and the counts above.
    q1 = out["toolkit_second_under_rule3"]["Q1"]
    out["toolkit_second_under_rule3"]["agrees_with_the_counts_above"] = (
        q1["cases_with_a_target"] == counts["rule3"]["cases_with_a_target"]
        and q1["flags"] == counts["rule3"]["not_decided_by_the_target"]
        and sorted(q1["flag_ids"]) == counts["rule3"]["not_decided_ids"])

    targets3_doc = dict(targets3)
    targets3_doc["rule_version"] = "reach-target-rule/3"
    targets3_doc["variant"] = {
        "rule_code": targets_mod.RULE_VERSION,
        "reachable": "reachable by name, or the function started under an entry point (reach.json)",
        "reach_json_sha256": out["inputs"]["reach_json_sha256"],
        "checks_reachable_by_name": reach_part["counts_all_checks"]["reachable_by_name_rule2_candidates"],
        "checks_reachable_by_execution": reach_part["counts_all_checks"]["reachable_by_execution"],
        "checks_reachable_under_rule3": reach_part["counts_all_checks"]["reachable_under_rule3_candidates"],
    }
    for tmp in keep:
        tmp.cleanup()
    return out, targets3_doc


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Second computation of rule 3 and its analysis, for 1 subject.")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--records", required=True)
    ap.add_argument("--reach", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--targets-out")
    ap.add_argument("--class-a", nargs="*", default=[])
    ap.add_argument("--toolkit", default=str(DEFAULT_TOOLKIT))
    args = ap.parse_args(argv)
    try:
        data, targets3 = compute(args)
    except InputError as exc:
        print(f"second_rule3: {exc}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, AttributeError) as exc:
        print(f"second_rule3: an input is malformed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.targets_out:
        tp = Path(args.targets_out)
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text(json.dumps(targets3, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    c2, c3 = data["counts"]["rule2"], data["counts"]["rule3"]
    tr = data["transitions"]["cases"]
    r = data["reachability"]["counts_all_checks"]
    print(f"{data['subject']}: checks by name {r['reachable_by_name_rule2_candidates']}, "
          f"by execution only {r['reachable_by_execution_only']}, rule 3 {r['reachable_under_rule3_candidates']}; "
          f"{data['counts']['cases_of_the_study']} cases; "
          f"rule 2: {c2['cases_with_a_target']} with a target, {c2['decided_by_the_target']} decided; "
          f"rule 3: {c3['cases_with_a_target']} with a target, {c3['decided_by_the_target']} decided; "
          f"gain {tr['gains a target']['count']}, keep {tr['keeps its target']['count']}, "
          f"change {tr['changes its target']['count']}, lose {tr['loses its target']['count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

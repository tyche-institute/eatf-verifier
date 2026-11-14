"""Compare the output of `second_rule3.py` with the outputs of `trace/rule3.py` and `trace/analyse3.py`.

    python3 -I -B recompute/compare_rule3.py --second OUT.json --first generated/trace/<name>
        [--second-targets TARGETS3.json] [--first-compare generated/trace/compare.json]
        [--class-a-tsv labels/first/<name>.tsv]

`--second` is the output of `second_rule3.py` for 1 subject and
`--second-targets` its optional `--targets-out` file. `--first` is the folder
that `trace/rule3.py` and `trace/analyse3.py` wrote for the same subject
(`targets.json`, `checks-reachability.csv`, `compare.csv`,
`fired-functions.csv`, `analysis/`); `--first-compare` is the `compare.json`
written beside the subject folders (default: `compare.json` in the parent of
`--first`). `--class-a-tsv` is the first reading of the flags; its rows of
class A give the cases of expectation T2. When it is given, the second output
must have been made with the same cases in `--class-a`. It is required when
the second output carries class-A cases (`expectations.T2.class_a_cases_given`
is not null).

Without `--second-targets`, the values that only the rule output holds are
not compared, and the printed "not compared" lines name them. With
`--second-targets`, the field `variant` of the rule output is compared with
the field `variant` of `targets.json`: its 3 counts of reachable checks with
`variant.reachability`, its fields `reach_json_sha256` and `rule_code` with
the fields of the same name, and the field `rule_version` of the rule output
with `variant.name`. The text `variant.reachable` is worded differently by the
2 programs and is not compared; 1 printed line says so.

The table `MAPPINGS` below names each compared value of the second output
and its place in the first outputs. A value is a number, a set (compared as a
set: the members only in 1 of the 2 are listed) or a table (compared per
item: the items only in 1 of the 2, and per common item the fields that
differ). Each number, each set and each item of a table counts as 1
compared value.

The 2 equalities of the second output about rule 2 (`rule2_recomputed`) are
compared separately, each with sentinel T1 of `targets.json`. The second
equality, `rule_code_with_an_empty_execution_set_equals_rule2`, repeats the
rule-2 computation on the same unwidened input, so it shows only that the
computation is repeatable.

Some compared values come, on the second side, from `recompute/second.py` of
the toolkit, which `second_rule3.py` runs on the rule-3 targets (group
`toolkit_second_under_rule3`: the own test without the target and the O_T
deletion results). These set the toolkit's second computation against
`analyse3.py`; the table `TOOLKIT_SECOND_VALUES` names them. Of the per-case
table, only the field `own_test_without_target` of the items with a rule-3
target rests on that computation. Each of the other names rests on it as a
whole value.

Both programs call the same rule code: `second_rule3.py` imports
`reach/targets.py` of the toolkit and calls `compute_targets`, the function
that `trace/rule3.py` calls on its own widened copy of `checks.json`. A
compared value that is, on the second side, the output of that function, a
tally of that output or a constant of the rule module agrees by construction
once the 2 sides give the function the same input. Such a value does not
check the rule code. The table `RULE_CODE_VALUES` names these values. The
per-case values that carry a rule-3 target take that target from the rule
output (the target of the block of the case). The cases, their deciding
checks and whether the target decides them come from the records, so these
per-case values are not counted in `RULE_CODE_VALUES`.

Prints "compared N, agree N, differ N" first. Then it prints:

- the values from the toolkit's second computation, with the number of
  compared values that involve them and the number of fields that rest on
  that computation, and their names, 1 per line;
- the values from the rule code, with the number of compared values that
  involve them and the number of names, their names, 1 per line, and 2
  sentences on what the 2 sides compute separately;
- 1 line on the 2 rule-2 equalities;
- 1 line that says which values of expectations T1, T2 and T3 and which
  sentinels are compared and which are not;
- with `--second-targets`, 1 "not compared" line on the text
  `variant.reachable` and on the fields of `variant` that only
  `targets.json` holds;
- without `--second-targets`, 1 "not compared" line followed by the values
  of the rule output that are not compared, 1 per line, and 1 line on the
  fields of `variant` that only `targets.json` holds;
- every difference with both values.

Exit status:

- 0 when every compared value agrees;
- 1 when 1 differs, or when the table `TOOLKIT_SECOND_VALUES` or the table
  `RULE_CODE_VALUES` names a value that the mapping table lacks (the names
  that exist only with `--second-targets` are expected only then);
- 2 when an input is missing or malformed, or when `--class-a-tsv` is absent
  although the second output carries class-A cases.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

# -- names of the 2 programs, side by side --------------------------------------------

TRANSITION_NAMES = {  # second_rule3.py -> analyse3.py
    "gains a target": "gained a target",
    "keeps its target": "same target",
    "changes its target": "changed target",
    "loses its target": "lost a target",
    "no target under either rule": "no target under either",
}
OUTCOME_NAMES = {  # second_rule3.py (toolkit protocol, section 4) -> reach/analyse.py
    "the target decides the case": "decided by the target",
    "the target fires and another check decides": "the target fires and another check decides",
    "the target fires and no check decides": "the target fires and no check decides",
    "the target does not fire": "the target does not fire",
    "not decided by the target": "not decided by the target",
}
FIRED_STATUS = {  # second_rule3.py -> the tally of analyse3.py (compare.json "fired_checks")
    "function started under an entry point": "under an entry point",
    "function started only under no entry point": "started only under no entry point",
    "function did not start in the traced run": "function not started",
    "not a check of checks.json": "not in checks.json",
}
REACH_COUNTS = {  # second reachability.counts_all_checks -> rule3.py counts()
    "reachable_by_name_rule2_candidates": "reachable_by_name",
    "reachable_by_execution": "reachable_by_execution",
    "reachable_by_both": "reachable_by_both",
    "reachable_by_name_only": "reachable_by_name_only",
    "reachable_by_execution_only": "reachable_by_execution_only",
    "reachable_under_neither": "reachable_by_neither",
    "reachable_under_rule3_candidates": "reachable_under_rule_3",
}
FUNCTION_COUNTS = {  # second reachability.functions -> reach.json "counts" as compare.json repeats it
    "functions_in_checks_json": "functions_in_checks_json",
    "started_in_the_traced_run": "functions_started",
    "started_under_an_entry_point": "functions_started_under_an_entry_point",
    "started_only_under_no_entry_point": "functions_started_only_under_no_entry_point",
}
TIERS = ("assertion", "name")
NO_TARGET = "no target"

# The 2 equalities of the second output about rule 2 (rule2_recomputed), each compared on its
# own with sentinel T1 of targets.json, so that a difference names the equality that fails.
RULE2_EQUALITIES = (
    "rule2_recomputed.equals_deposited_targets_json_byte_for_byte (sentinel T1)",
    "rule2_recomputed.rule_code_with_an_empty_execution_set_equals_rule2 (sentinel T1)",
)

# Compared values whose second side comes from recompute/second.py of the toolkit, run by
# second_rule3.py on the rule-3 targets (group toolkit_second_under_rule3). They set the
# toolkit's second computation against analyse3.py, not a computation of second_rule3.py itself.
TOOLKIT_SECOND_VALUES = (
    "per case under rule 3: target, basis, tier, decided, target fires, own test without the target, "
    "raise site",
    "rule3 cases with a target by outcome, with the own test without the target",
    "O_T: deletions of deciding checks not detected",
    "O_T: deletions of checks that fire and never decide, not detected",
    "O_T withheld-as-failing: deletions of deciding checks not detected",
    "rule3 targets that decide a case, deletion not detected under O_T",
    "toolkit second.py Q1 flags",
)
TOOLKIT_SECOND_PARTS = {  # which part of a value rests on the toolkit's second computation
    TOOLKIT_SECOND_VALUES[0]: "field own_test_without_target of each item with a rule-3 target",
    TOOLKIT_SECOND_VALUES[1]: "the counts per outcome with the own test without the target",
    TOOLKIT_SECOND_VALUES[6]: "compared with the rule-3 flags of the second output itself, not with analyse3.py",
}

# The field variant of the rule output (--second-targets) against the field variant of targets.json.
VARIANT_COUNTS = {  # second variant -> targets.json variant.reachability
    "checks_reachable_by_execution": "reachable_by_execution",
    "checks_reachable_by_name": "reachable_by_name",
    "checks_reachable_under_rule3": "reachable_under_rule_3",
}
VARIANT_RULE_CODE = "variant rule_code"
VARIANT_REACH_DIGEST = "variant reach_json_sha256"
VARIANT_NAME = "variant name (targets.json) and rule_version of the rule output"
BLOCKS_ALL_FIELDS = "per block under rule 3: every field of the rule output"
BLOCKS_RULE3 = "per block under rule 3: target, basis, tier, reason"
BLOCKS_BY_BASIS = "blocks under rule 3 by basis or reason"
BLOCKS_WITH_TARGET = "included blocks with a target under rule 3"
BLOCKS_TARGETING = "blocks targeting each check under rule 3"

# Compared values that are, on the second side, the output of compute_targets of reach/targets.py
# of the toolkit (called by second_rule3.py on its widened copy of checks.json, and on the
# unchanged checks.json for the 2 rule-2 equalities), a tally of that output (alone or with the
# deposited rule-2 targets), or a constant of the rule module. trace/rule3.py calls the same
# function, so these values agree by construction once the 2 sides give it the same input.
# Not in this table:
# - the rule output field rule_version and the variant name, which each program writes as its own
#   text "reach-target-rule/3";
# - the variant counts and the digest of reach.json, which second_rule3.py computes from
#   checks.json and reach.json;
# - the per-case values, which take the target of the block of the case from the rule output but
#   rest on the records.
RULE_CODE_VALUES = (
    BLOCKS_RULE3,
    BLOCKS_ALL_FIELDS,
    "rule output field constants",
    "rule output field counts",
    VARIANT_RULE_CODE,
    BLOCKS_BY_BASIS,
    BLOCKS_WITH_TARGET,
) + tuple(f"block transition {t}" for t in TRANSITION_NAMES) + (
    BLOCKS_TARGETING,
) + RULE2_EQUALITIES
# The names of RULE_CODE_VALUES that the mapping table holds only with --second-targets.
RULE_CODE_ONLY_WITH_TARGETS = (
    BLOCKS_ALL_FIELDS,
    "rule output field constants",
    "rule output field counts",
    VARIANT_RULE_CODE,
)


class InputError(Exception):
    pass


def load_json(path: Path, what: str):
    if not path.is_file():
        raise InputError(f"{what} is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"{what} is not readable JSON: {path}: {exc}") from exc


def read_csv(path: Path, what: str, delimiter: str = ",") -> list[dict]:
    if not path.is_file():
        raise InputError(f"{what} is missing: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def yn(v: str) -> bool | None:
    return {"yes": True, "no": False}.get(v)


def nonzero(d: dict) -> dict:
    return {k: v for k, v in d.items() if v}


def site_label(site: dict | None) -> str:
    """The text that reach/analyse.py writes for the raise site of a raised case."""
    if site is None:
        return "outside package"
    if site.get("check"):
        return site["check"]
    return f"{site.get('kind')} ({site.get('file')}:{site.get('line')} {site.get('source')})"


def own_test_reason(reason: str) -> str:
    """The reason of recompute/second.py of the toolkit for an own test that is not
    counted, in the words of the column own_test_without_target of reach/analyse.py."""
    if reason.endswith("fires in no case of the study") or reason.endswith("lies outside the subject files"):
        return "target not deleted"
    return {"the deletion run exceeded the time limit": "time limit",
            "the deletion run gave no record": "no record"}.get(reason, reason)


# -- the 2 sides --------------------------------------------------------------------------

class Second:
    """Views of the output of second_rule3.py."""

    def __init__(self, doc: dict, targets_doc: dict | None) -> None:
        self.doc = doc
        self.targets = targets_doc
        self.cases = doc["cases"]
        self.rule = {r: doc["counts"][r] for r in ("rule2", "rule3")}
        own = doc["toolkit_second_under_rule3"]["own_test_without_the_target"]
        self.own = {}
        for kind in own["ids"].values():
            for res, ids in kind.items():
                for k in ids:
                    self.own[k] = res
        for reason, ids in own["not_counted_ids"].items():
            for k in ids:
                self.own[k] = own_test_reason(reason)

    def case_row(self, k: str) -> dict:
        c = self.cases[k]
        row = {}
        for rule, n in (("rule2", "2"), ("rule3", "3")):
            r = c[rule]
            t = r["target"]
            row[f"target_rule{n}"] = t or None
            row[f"basis_rule{n}"] = r["basis"] if t else None
            row[f"tier_rule{n}"] = r["tier"] if t else NO_TARGET
            row[f"decides_rule{n}"] = r["decides"] if t else None
        row["baseline_site"] = site_label(c["raise_site"])
        row["transition"] = TRANSITION_NAMES.get(c["transition"], c["transition"])
        return row

    def analysis_row(self, k: str) -> dict:
        """The columns of cases.csv of the analysis under rule 3."""
        c = self.cases[k]
        r = c["rule3"]
        t = r["target"]
        fired = c["fired"]
        return {"target": t or None, "basis": r["basis"] if t else None, "tier": r["tier"] if t else NO_TARGET,
                "reaches_target": r["decides"] if t else None,
                "target_fired": (t in fired) if (t and fired is not None) else None,
                "own_test_without_target": self.own.get(k) if t else None,
                "baseline_site": site_label(c["raise_site"])}

    def block_key(self, k: str) -> str:
        c = self.cases[k]
        return f"{c['block']}|{c['index']}"

    def with_target(self, rule: str) -> list[str]:
        return [k for k, c in self.cases.items() if c[rule]["target"]]

    def target_fires(self, k: str) -> bool:
        c = self.cases[k]
        t = c["rule3"]["target"]
        return bool(t) and c["fired"] is not None and t in c["fired"]

    def moved(self) -> dict:
        out = Counter()
        for c in self.cases.values():
            if c["transition"] in ("changes its target", "gains a target", "loses its target"):
                a = ("yes" if c["rule2"]["decides"] else "no") if c["rule2"]["target"] else "no target"
                b = ("yes" if c["rule3"]["decides"] else "no") if c["rule3"]["target"] else "no target"
                out[f"{a} -> {b}"] += 1
        return dict(sorted(out.items()))

    def outcome_with_own_test(self) -> dict:
        out = Counter()
        for k in self.with_target("rule3"):
            raw = self.cases[k]["rule3"]["outcome"]
            o = OUTCOME_NAMES.get(raw, f"unknown outcome {raw}")
            out[o] += 1
            own = self.own.get(k)
            out[f"{o}; own test without the target: {own}"] += 1
        return dict(sorted(out.items()))

    def blocks_targeting(self) -> dict:
        return dict(Counter(b["rule3"]["target"] for b in self.doc["blocks"]["per_block"].values()
                            if b["rule3"]["target"]))


class First:
    """Views of the outputs of rule3.py and analyse3.py for 1 subject."""

    def __init__(self, folder: Path, compare_path: Path, subject: str, class_a_tsv: Path | None) -> None:
        self.folder = folder
        doc = load_json(compare_path, "compare.json")
        rows = [r for r in doc if r.get("subject") == subject]
        if len(rows) != 1:
            raise InputError(f"compare.json holds {len(rows)} entries for {subject}")
        self.cmp = rows[0]
        self.targets = load_json(folder / "targets.json", "targets.json")
        self.reach_rows = {r["check"]: r for r in read_csv(folder / "checks-reachability.csv",
                                                          "checks-reachability.csv")}
        self.compare_rows = {f"{r['test_node']}|{r['block']}|{r['index']}": r
                             for r in read_csv(folder / "compare.csv", "compare.csv")}
        self.fired_rows = {r["check"]: r for r in read_csv(folder / "fired-functions.csv", "fired-functions.csv")}
        a = folder / "analysis"
        self.summary = load_json(a / "summary.json", "analysis/summary.json")
        self.analysis_cases = {f"{r['test_node']}|{r['block']}|{r['index']}": r
                               for r in read_csv(a / "cases.csv", "analysis/cases.csv")}
        self.flags = {f"{r['block']}|{r['index']}" for r in read_csv(a / "flags.csv", "analysis/flags.csv")}
        self.deletions = read_csv(a / "deletions.csv", "analysis/deletions.csv")
        self.checks_csv = {r["check"]: r for r in read_csv(a / "checks.csv", "analysis/checks.csv")}
        self.class_a = None
        if class_a_tsv is not None:
            rows = read_csv(class_a_tsv, "the first reading", delimiter="\t")
            self.class_a = sorted(f"{r['test_node']}|{r['block']}|{r['index']}" for r in rows if r["class"] == "A")

    def case_row(self, k: str) -> dict:
        r = self.compare_rows[k]
        row = {}
        for n in ("2", "3"):
            t = r[f"target_rule{n}"]
            row[f"target_rule{n}"] = t or None
            row[f"basis_rule{n}"] = r[f"basis_rule{n}"] or None if t else None
            row[f"tier_rule{n}"] = r[f"tier_rule{n}"] if t else NO_TARGET
            row[f"decides_rule{n}"] = yn(r[f"decides_rule{n}"]) if t else None
        row["baseline_site"] = r["baseline_site"]
        row["transition"] = r["transition"]
        return row

    def analysis_row(self, k: str) -> dict:
        r = self.analysis_cases[k]
        t = r["target"]
        own = r["own_test_without_target"]
        return {"target": t or None, "basis": (r["basis"] or None) if t else None,
                "tier": r["tier"] if t else NO_TARGET, "reaches_target": yn(r["reaches_target"]) if t else None,
                "target_fired": yn(r["target_fired"]) if t else None,
                "own_test_without_target": own if t else None,
                "baseline_site": r["baseline_site"]}

    def ids(self, rule: str, decided: bool | None) -> set:
        n = rule[-1]
        out = set()
        for k, r in self.compare_rows.items():
            if not r[f"target_rule{n}"]:
                continue
            if decided is None or yn(r[f"decides_rule{n}"]) is decided:
                out.add(k)
        return out

    def reach_set(self, which: str) -> set:
        name = {k: yn(r["reachable_by_name"]) for k, r in self.reach_rows.items()}
        exe = {k: yn(r["reachable_by_execution"]) for k, r in self.reach_rows.items()}
        r3 = {k: yn(r["reachable_rule_3"]) for k, r in self.reach_rows.items()}
        pick = {
            "reachable_by_name_rule2_candidates": lambda k: name[k],
            "reachable_by_execution": lambda k: exe[k],
            "reachable_by_both": lambda k: name[k] and exe[k],
            "reachable_by_name_only": lambda k: name[k] and not exe[k],
            "reachable_by_execution_only": lambda k: exe[k] and not name[k],
            "reachable_under_neither": lambda k: not r3[k],
            "reachable_under_rule3_candidates": lambda k: r3[k],
        }[which]
        return {k for k in self.reach_rows if pick(k)}

    def fired_status(self, r: dict) -> str:
        if r["started_under_an_entry_point"] == "yes":
            return "under an entry point"
        reason = r["reason"]
        if reason.startswith("the function started only"):
            return "started only under no entry point"
        if reason.startswith("the function did not start"):
            return "function not started"
        if reason.startswith("the check is not in checks.json"):
            return "not in checks.json"
        return f"other: {reason}"

    def deletion_set(self, deciding: bool, column: str) -> set:
        return {r["check"] for r in self.deletions
                if (int(r["cases_decided"] or 0) > 0) is deciding and r[column] == "no"}


# -- the mapping table --------------------------------------------------------------------

def mappings(s: Second, f: First) -> list[tuple[str, str, object, object, str]]:
    """(name, kind, second value, first value, place in the first outputs)."""
    sd, cmp, summ = s.doc, f.cmp, f.summary["counts"]
    reach = sd["reachability"]
    m: list[tuple] = []
    add = m.append

    # Reachability of the checks (PROTOCOL.md 4.2, 'Analysis')
    add(("checks", "number", reach["checks"], cmp["reachability"]["checks"], "compare.json reachability.checks"))
    for sk, fk in REACH_COUNTS.items():
        add((f"reachability count {sk}", "number", reach["counts_all_checks"][sk], cmp["reachability"][fk],
             f"compare.json reachability.{fk}"))
        add((f"reachability count {sk} (targets.json)", "number", reach["counts_all_checks"][sk],
             f.targets["variant"]["reachability"][fk], f"targets.json variant.reachability.{fk}"))
        add((f"reachability set {sk}", "set", set(reach["ids"][sk]), f.reach_set(sk),
             "checks-reachability.csv (columns reachable_by_name, reachable_by_execution, reachable_rule_3)"))
    add(("checks (targets.json)", "number", reach["checks"], f.targets["variant"]["reachability"]["checks"],
         "targets.json variant.reachability.checks"))
    add(("per check: file, function, role, by name, by execution, rule 3, entry points", "table",
         {k: {"file": v["file"], "function": v["function"], "role": v["role"], "by_name": v["by_name"],
              "by_execution": v["by_execution"], "rule3": v["rule3"], "entry_points": v["entry_points"]}
          for k, v in reach["per_check"].items()},
         {k: {"file": r["file"], "function": r["function"], "role": r["role"],
              "by_name": yn(r["reachable_by_name"]), "by_execution": yn(r["reachable_by_execution"]),
              "rule3": yn(r["reachable_rule_3"]),
              "entry_points": sorted(r["entry_points"].split())}
          for k, r in f.reach_rows.items()},
         "checks-reachability.csv, 1 row per check"))
    fn = reach["functions"]
    for sk, fk in FUNCTION_COUNTS.items():
        v = fn[sk]
        add((f"functions {sk}", "number", len(v) if isinstance(v, list) else v, cmp["trace_counts"][fk],
             f"compare.json trace_counts.{fk}"))

    # The rule code unchanged (README of trace/, sentinel T1)
    add(("digest of reach.json", "number", sd["inputs"]["reach_json_sha256"], f.targets["variant"]["reach_json_sha256"],
         "targets.json variant.reach_json_sha256"))
    sent = {x["name"].split(":")[0]: x["pass"] for x in f.targets["variant"]["sentinels"]}
    r2 = sd["rule2_recomputed"]
    add((RULE2_EQUALITIES[0], "number", r2["equals_deposited_targets_json_byte_for_byte"],
         sent.get("T1"), "targets.json variant.sentinels T1"))
    add((RULE2_EQUALITIES[1], "number", r2["rule_code_with_an_empty_execution_set_equals_rule2"],
         sent.get("T1"), "targets.json variant.sentinels T1"))

    # Targets of the included blocks under rule 3
    pb = sd["blocks"]["per_block"]
    tb = {b["key"]: b for b in f.targets["blocks"]}
    add((BLOCKS_RULE3, "table",
         {k: {"target": v["rule3"]["target"], "basis": v["rule3"]["basis"],
              "tier": v["rule3"]["tier"] if v["rule3"]["target"] else NO_TARGET, "reason": v["rule3"]["reason"]}
          for k, v in pb.items()},
         {k: {"target": b["target"], "basis": b["basis"], "tier": b["tier"] if b["target"] else NO_TARGET,
              "reason": b["reason"]} for k, b in tb.items()},
         "targets.json blocks"))
    if s.targets is not None:
        add((BLOCKS_ALL_FIELDS, "table",
             {b["key"]: b for b in s.targets["blocks"]}, tb, "targets.json blocks (all fields)"))
        for field in ("constants", "counts", "rule_version"):
            add((f"rule output field {field}", "number", s.targets.get(field), f.targets.get(field),
                 f"targets.json {field}"))
        sv, fv = s.targets["variant"], f.targets["variant"]
        for sk, fk in VARIANT_COUNTS.items():
            add((f"variant {sk}", "number", sv[sk], fv["reachability"][fk],
                 f"targets.json variant.reachability.{fk}"))
        add((VARIANT_REACH_DIGEST, "number", sv["reach_json_sha256"], fv["reach_json_sha256"],
             "targets.json variant.reach_json_sha256"))
        add((VARIANT_RULE_CODE, "number", sv["rule_code"], fv["rule_code"], "targets.json variant.rule_code"))
        add((VARIANT_NAME, "number", s.targets["rule_version"], fv["name"], "targets.json variant.name"))
    by3 = sd["blocks"]["by_rule"]["rule3"]
    add((BLOCKS_BY_BASIS, "number", by3["blocks_by_basis_or_reason"],
         f.targets["counts"], "targets.json counts"))
    add(("included blocks", "number", by3["included_blocks"], summ["included_blocks"],
         "analysis/summary.json counts.included_blocks"))
    add((BLOCKS_WITH_TARGET, "number", by3["blocks_with_a_target"],
         summ["included_blocks_with_target"], "analysis/summary.json counts.included_blocks_with_target"))
    for t, ft in TRANSITION_NAMES.items():
        add((f"block transition {t}", "number", sd["blocks"]["transitions"][t]["count"],
             cmp["block_transitions"][ft], f"compare.json block_transitions.{ft}"))
    add((BLOCKS_TARGETING, "table", s.blocks_targeting(),
         {k: int(r["blocks_targeting"]) for k, r in f.checks_csv.items() if int(r["blocks_targeting"])},
         "analysis/checks.csv blocks_targeting (non-zero rows)"))

    # Cases
    add(("cases of the study", "set", set(s.cases), set(f.compare_rows), "compare.csv rows"))
    add(("cases of the study (analysis under rule 3)", "set", set(s.cases), set(f.analysis_cases),
         "analysis/cases.csv rows"))
    add(("number of cases of the study", "number", sd["counts"]["cases_of_the_study"], summ["cases"],
         "analysis/summary.json counts.cases"))
    add(("per case: target, basis, tier, decides under rule 2 and rule 3; raise site; transition", "table",
         {k: s.case_row(k) for k in s.cases}, {k: f.case_row(k) for k in f.compare_rows}, "compare.csv"))
    add(("per case under rule 3: target, basis, tier, decided, target fires, own test without the target, "
         "raise site", "table", {k: s.analysis_row(k) for k in s.cases},
         {k: f.analysis_row(k) for k in f.analysis_cases}, "analysis/cases.csv"))

    # Counts per rule, overall and per tier
    for rule in ("rule2", "rule3"):
        c = s.rule[rule]
        for tier in TIERS + ("all",):
            x = c if tier == "all" else c["by_tier"][tier]
            y = cmp[rule][tier]
            add((f"{rule} {tier}: cases with a target", "number", x["cases_with_a_target"],
                 y["cases_with_a_target"], f"compare.json {rule}.{tier}.cases_with_a_target"))
            add((f"{rule} {tier}: decided by the target", "number", x["decided_by_the_target"],
                 y["decided_by_the_target"], f"compare.json {rule}.{tier}.decided_by_the_target"))
            add((f"{rule} {tier}: not decided (flags)", "number", x["not_decided_by_the_target"],
                 y["not_decided_flags"], f"compare.json {rule}.{tier}.not_decided_flags"))
        add((f"{rule}: cases decided by the target", "set", set(c["decided_ids"]),
             f.ids(rule, True), f"compare.csv decides_{rule}"))
        add((f"{rule}: cases not decided by the target (flags)", "set", set(c["not_decided_ids"]),
             f.ids(rule, False), f"compare.csv decides_{rule}"))
    c3 = s.rule["rule3"]
    add(("rule3 flags", "set", {s.block_key(k) for k in c3["not_decided_ids"]}, f.flags, "analysis/flags.csv"))
    add(("rule3 cases with a target", "number", c3["cases_with_a_target"], summ["cases_with_target"],
         "analysis/summary.json counts.cases_with_target"))
    add(("rule3 cases decided by the target", "number", c3["decided_by_the_target"], summ["cases_reaching_target"],
         "analysis/summary.json counts.cases_reaching_target"))
    add(("rule3 flags count", "number", c3["not_decided_by_the_target"], summ["flags"],
         "analysis/summary.json counts.flags"))
    add(("rule3 cases with a target by tier", "number",
         nonzero({t: c3["by_tier"][t]["cases_with_a_target"] for t in TIERS}),
         summ["cases_with_target_by_tier"], "analysis/summary.json counts.cases_with_target_by_tier"))
    add(("rule3 flags by tier", "number", nonzero({t: c3["by_tier"][t]["not_decided_by_the_target"] for t in TIERS}),
         summ["flags_by_tier"], "analysis/summary.json counts.flags_by_tier"))
    add(("rule3 cases with a target by basis", "number",
         nonzero({b: v["cases_with_a_target"] for b, v in c3["by_basis"].items()}),
         summ["cases_with_target_by_basis"], "analysis/summary.json counts.cases_with_target_by_basis"))
    add(("rule3 cases with a target by outcome, with the own test without the target", "number",
         s.outcome_with_own_test(), summ["cases_with_target_by_outcome"],
         "analysis/summary.json counts.cases_with_target_by_outcome"))
    add(("rule3 cases whose target fires", "number", sum(1 for k in s.with_target("rule3") if s.target_fires(k)),
         summ["cases_target_fires"], "analysis/summary.json counts.cases_target_fires"))
    add(("rule3 flags whose target fires", "number", sum(1 for k in c3["not_decided_ids"] if s.target_fires(k)),
         summ["flags_target_fires"], "analysis/summary.json counts.flags_target_fires"))

    # Oracle O_T and the toolkit's recomputation under the rule-3 targets
    ts = sd["toolkit_second_under_rule3"]
    add(("O_T: deletions of deciding checks not detected", "set", set(ts["O_T_not_detected_deciding_checks_ids"]),
         f.deletion_set(True, "O_T"), "analysis/deletions.csv (cases_decided > 0, O_T no)"))
    add(("O_T: deletions of checks that fire and never decide, not detected", "set",
         set(ts["O_T_not_detected_checks_that_fire_and_never_decide_ids"]), f.deletion_set(False, "O_T"),
         "analysis/deletions.csv (cases_decided 0, O_T no)"))
    add(("O_T withheld-as-failing: deletions of deciding checks not detected", "number",
         ts["O_T_not_detected_deciding_checks_withheld_as_failing"],
         summ["deletions_not_detected_withheld_as_failing_of_deciding_checks"]["O_T"],
         "analysis/summary.json counts.deletions_not_detected_withheld_as_failing_of_deciding_checks.O_T"))
    reached = {sd["cases"][k]["rule3"]["target"] for k in c3["decided_ids"]}
    add(("rule3 targets that decide at least 1 case", "number", len(reached), summ["reached_targets"],
         "analysis/summary.json counts.reached_targets"))
    add(("rule3 targets that decide a case, deletion not detected under O_T", "number",
         len(reached & set(ts["O_T_not_detected_deciding_checks_ids"])),
         summ["reached_targets_deletion_not_detected_O_T"],
         "analysis/summary.json counts.reached_targets_deletion_not_detected_O_T"))
    add(("toolkit second.py Q1 flags", "set", set(ts["Q1"]["flag_ids"]), set(c3["not_decided_ids"]),
         "the second output's own rule-3 flags (internal; analysis/flags.csv is compared above)"))

    # Transitions between the rules (section 2, note on the rule; 4.2 'Analysis')
    tr = sd["transitions"]
    for t, ft in TRANSITION_NAMES.items():
        add((f"case transition {t}", "number", tr["cases"][t]["count"], cmp["case_transitions"][ft],
             f"compare.json case_transitions.{ft}"))
        add((f"case transition {t}: cases", "set", set(tr["cases"][t]["ids"]),
             {k for k, r in f.compare_rows.items() if r["transition"] == ft}, "compare.csv transition"))
        for n in ("2", "3"):
            add((f"case transition {t}: decided by the rule-{n} target", "number",
                 tr["cases"][t][f"decided_by_the_rule{n}_target"],
                 sum(1 for r in f.compare_rows.values() if r["transition"] == ft and r[f"decides_rule{n}"] == "yes"),
                 f"compare.csv rows with transition {ft!r} and decides_rule{n} yes"))
    add(("decided under rule 2 -> rule 3 for cases that change, gain or lose a target", "number", s.moved(),
         cmp["decides_rule2_to_rule3_for_moved_cases"], "compare.json decides_rule2_to_rule3_for_moved_cases"))
    tiers = Counter()
    for r in f.compare_rows.values():
        a = r["tier_rule2"] if r["target_rule2"] else NO_TARGET
        b = r["tier_rule3"] if r["target_rule3"] else NO_TARGET
        tiers[(a, b)] += 1
    matrix: dict = {}
    for (a, b), n in sorted(tiers.items()):
        matrix.setdefault(f"rule2 {a}", {})[f"rule3 {b}"] = n
    add(("tier transitions", "number", tr["tier_transitions"], matrix, "compare.csv tier_rule2 x tier_rule3"))
    after = {}
    for k in f.ids("rule2", False):
        r = f.compare_rows[k]
        if not r["target_rule3"]:
            w = "no target under rule 3"
        elif r["decides_rule3"] == "yes":
            w = "target under rule 3 decides the case"
        else:
            w = "target under rule 3 does not decide the case"
        after.setdefault(w, set()).add(k)
    add(("rule-2 flags under rule 3", "table", {w: sorted(v["ids"]) for w, v in tr["rule2_flags_under_rule3"].items()},
         {w: sorted(v) for w, v in after.items()}, "compare.csv (rule-2 flags by their rule-3 columns)"))

    # Fired checks and the trace (README of trace/, sentinel T2)
    ff = sd["fired_functions"]
    add(("fired checks", "set", set(ff["checks"]), set(f.fired_rows), "fired-functions.csv rows"))
    add(("per fired check: file, function, status, entry points", "table",
         {k: {"file": v.get("file", ""), "function": v.get("function", ""),
              "status": FIRED_STATUS.get(v["status"], v["status"]), "entry_points": v.get("entry_points", [])}
          for k, v in ff["checks"].items()},
         {k: {"file": r["file"], "function": r["function"], "status": f.fired_status(r),
              "entry_points": sorted(r["entry_points"].split())} for k, r in f.fired_rows.items()},
         "fired-functions.csv"))
    t2_sentinel = {x["name"].split(":")[0]: x["pass"] for x in cmp["sentinels"]}.get("T2")
    add(("every fired check lies in a function that started (sentinel T2)", "number",
         ff["every_firing_function_started"], t2_sentinel, "compare.json sentinels T2"))
    add(("fired checks by status", "number",
         {FIRED_STATUS.get(k, k): v for k, v in ff["counts_by_status"].items()}, cmp["fired_checks"],
         "compare.json fired_checks"))

    # Expectations of section 2, from the first outputs with the thresholds of the protocol
    ex = sd["expectations"]
    y3 = cmp["rule3"]["all"]
    y2 = cmp["rule2"]["all"]
    add(("T1 rule-3 cases not decided by their target", "number", ex["T1"]["rule3_cases_not_decided_by_their_target"],
         y3["not_decided_flags"], "compare.json rule3.all.not_decided_flags"))
    add(("T1 rule-2 cases not decided by their target", "number", ex["T1"]["rule2_cases_not_decided_by_their_target"],
         y2["not_decided_flags"], "compare.json rule2.all.not_decided_flags"))
    add(("T1 rule-3 count at most 10", "number", ex["T1"]["rule3_at_most_10"], y3["not_decided_flags"] <= 10,
         "compare.json rule3.all.not_decided_flags <= 10"))
    add(("T3 rule-3 decided / with a target", "number", [ex["T3"]["rule3_decided"], ex["T3"]["rule3_with_a_target"]],
         [y3["decided_by_the_target"], y3["cases_with_a_target"]], "compare.json rule3.all"))
    add(("T3 rule-2 decided / with a target", "number", [ex["T3"]["rule2_decided"], ex["T3"]["rule2_with_a_target"]],
         [y2["decided_by_the_target"], y2["cases_with_a_target"]], "compare.json rule2.all"))
    add(("T3 holds (at least 85 %)", "number", ex["T3"]["holds"],
         (y3["decided_by_the_target"] * 100 >= 85 * y3["cases_with_a_target"]) if y3["cases_with_a_target"] else None,
         "compare.json rule3.all, decided * 100 >= 85 * with a target"))
    if f.class_a is not None:
        given = (ex["T2"].get("class_a_cases_given") or {}).get("cases") or {}
        add(("T2 class-A cases", "set", set(given), set(f.class_a), "the first reading, rows of class A"))
        add(("T2 class-A cases keep their target", "table", {k: v["keeps"] for k, v in given.items()},
             {k: f.compare_rows[k]["transition"] == "same target" for k in f.class_a if k in f.compare_rows},
             "compare.csv transition of the class-A cases"))
    return m


# -- comparing ----------------------------------------------------------------------------

def norm(v):
    """Lists and tuples compare as lists; numbers as numbers."""
    if isinstance(v, tuple):
        return list(v)
    return v


def compare(m: list[tuple]) -> tuple[int, int, list[str]]:
    compared, agree, out = 0, 0, []
    for name, kind, a, b, place in m:
        if kind == "number":
            compared += 1
            if norm(a) == norm(b):
                agree += 1
            else:
                out.append(f"DIFF {name} [{place}]: second {json.dumps(a, sort_keys=True)}, "
                           f"first {json.dumps(b, sort_keys=True)}")
        elif kind == "set":
            compared += 1
            only_a, only_b = sorted(a - b), sorted(b - a)
            if not only_a and not only_b:
                agree += 1
            else:
                out.append(f"DIFF {name} [{place}]: {len(a)} in second, {len(b)} in first; "
                           f"only in second {only_a}; only in first {only_b}")
        elif kind == "table":
            for k in sorted(set(a) | set(b)):
                compared += 1
                if k not in b:
                    out.append(f"DIFF {name} [{place}]: item {k} only in second: {json.dumps(a[k], sort_keys=True)}")
                elif k not in a:
                    out.append(f"DIFF {name} [{place}]: item {k} only in first: {json.dumps(b[k], sort_keys=True)}")
                elif norm(a[k]) == norm(b[k]):
                    agree += 1
                else:
                    x, y = a[k], b[k]
                    if isinstance(x, dict) and isinstance(y, dict):
                        fields = sorted(f for f in set(x) | set(y) if x.get(f) != y.get(f))
                        detail = "; ".join(f"{f}: second {json.dumps(x.get(f), sort_keys=True)}, "
                                           f"first {json.dumps(y.get(f), sort_keys=True)}" for f in fields)
                    else:
                        detail = f"second {json.dumps(x, sort_keys=True)}, first {json.dumps(y, sort_keys=True)}"
                    out.append(f"DIFF {name} [{place}]: item {k}: {detail}")
        else:
            raise ValueError(kind)
    return compared, agree, out


def toolkit_second_lines(m: list[tuple]) -> list[str]:
    """The summary lines that name the compared values resting on the toolkit's second computation.

    The number of compared values counts each item of a table, as compare() does. The number of
    fields counts what rests on the toolkit's second computation. Of the per-case table, this is the
    field own_test_without_target of each item with a rule-3 target on the second side;
    Second.analysis_row sets it to null for an item without a target. Each other name counts as 1
    whole value.
    """
    sizes, fields = {}, {}
    for name, kind, a, b, _place in m:
        if name in TOOLKIT_SECOND_VALUES:
            sizes[name] = len(set(a) | set(b)) if kind == "table" else 1
            if name == TOOLKIT_SECOND_VALUES[0]:
                fields[name] = sum(1 for v in a.values() if v.get("target"))
            else:
                fields[name] = 1
    missing = [n for n in TOOLKIT_SECOND_VALUES if n not in sizes]
    if missing:
        raise ValueError(f"names of TOOLKIT_SECOND_VALUES not in the mapping table: {missing}")
    lines = [("from the toolkit's second computation: recompute/second.py of the toolkit, run by "
              "second_rule3.py on the rule-3 targets, gives the second side of "
              f"{len(TOOLKIT_SECOND_VALUES)} names."),
             (f"  {sum(sizes.values())} compared values involve these names "
              "(each item of a table counts as 1)."),
             (f"  {sum(fields.values())} fields rest on that computation "
              f"({fields[TOOLKIT_SECOND_VALUES[0]]} fields own_test_without_target of per-case items "
              f"with a rule-3 target, and {len(TOOLKIT_SECOND_VALUES) - 1} whole values)."),
             ("  Apart from the Q1 flags, these set the toolkit's second computation against "
              "analyse3.py, not an independent computation of second_rule3.py."),
             "  Names:"]
    for n in TOOLKIT_SECOND_VALUES:
        part = f" ({TOOLKIT_SECOND_PARTS[n]})" if n in TOOLKIT_SECOND_PARTS else ""
        lines.append(f"  - '{n}'{part}: {sizes[n]} compared, {fields[n]} resting on that computation")
    return lines


def rule_code_lines(m: list[tuple], with_targets: bool) -> list[str]:
    """The summary lines that name the compared values resting on the rule code.

    The number of compared values counts each item of a table, as compare() does. The names of
    RULE_CODE_ONLY_WITH_TARGETS are expected in the mapping table only with --second-targets.
    """
    sizes = {}
    for name, kind, a, b, _place in m:
        if name in RULE_CODE_VALUES:
            sizes[name] = len(set(a) | set(b)) if kind == "table" else 1
    expected = [n for n in RULE_CODE_VALUES if with_targets or n not in RULE_CODE_ONLY_WITH_TARGETS]
    missing = [n for n in expected if n not in sizes]
    if missing:
        raise ValueError(f"names of RULE_CODE_VALUES not in the mapping table: {missing}")
    lines = [("from the rule code: on the second side, these names are the output of compute_targets "
              "of reach/targets.py of the toolkit, a tally of that output, or a constant of the rule "
              "module."),
             (f"  {sum(sizes[n] for n in expected)} compared values involve these names "
              f"(each item of a table counts as 1), under {len(expected)} names."),
             ("  trace/rule3.py calls the same function, so these values agree by construction once "
              "the 2 sides give it the same input, and they do not check the rule code."),
             ("  The 2 sides compute separately which checks are reachable by execution and under rule 3 "
              "(the widening of the field reachable), the cases of the study, the deciding check of each "
              "case from the records, and whether the target decides each case."),
             ("  They also compute separately the outcomes, the case transitions between the rules, the "
              "fired checks and where their functions started, and the quantities of T1 to T3, while each "
              "per-case value takes the rule-3 target of its block from the rule output."),
             "  Names:"]
    for n in expected:
        lines.append(f"  - '{n}': {sizes[n]} compared")
    return lines


def rule2_equalities_line() -> str:
    """The summary line on the 2 equalities of the second output about rule 2."""
    return ("rule 2: each of the 2 equalities of rule2_recomputed is compared with sentinel T1 of "
            "targets.json. The second equality, rule_code_with_an_empty_execution_set_equals_rule2, "
            "repeats the rule-2 computation on the same unwidened input, so it shows only that the "
            "computation is repeatable.")


# Compared only when --second-targets gives the rule output of second_rule3.py.
RULE_OUTPUT_VALUES = (
    f"{BLOCKS_ALL_FIELDS} (1 compared value per block)",
    "rule output field constants",
    "rule output field counts",
    "rule output field rule_version",
) + tuple(f"variant {sk} (with targets.json variant.reachability.{fk})" for sk, fk in VARIANT_COUNTS.items()) + (
    f"{VARIANT_REACH_DIGEST} (with targets.json variant.reach_json_sha256)",
    f"{VARIANT_RULE_CODE} (with targets.json variant.rule_code)",
    VARIANT_NAME,
)


def variant_only_first_text(with_targets: bool) -> str:
    """The sentences on the fields of variant that only targets.json holds."""
    name = ("name, compared with rule_version of the rule output" if with_targets else
            "name, compared with rule_version of the rule output only with --second-targets")
    return (f"The fields of variant that only targets.json holds: {name}; reachability, whose 8 counts "
            "are compared with the reachability counts of the second output; sentinels, whose T1 is "
            "compared with each of the 2 rule-2 equalities. The other sentinel, that every function of "
            "reach.json is a function of checks.json, is not compared: second_rule3.py writes no value "
            "for it and stops with exit status 2 when it fails.")


def not_compared_variant_line() -> str:
    """The "not compared" line of a run with --second-targets."""
    return ("not compared: variant.reachable of the rule output, a text that second_rule3.py and "
            "trace/rule3.py word differently. " + variant_only_first_text(True))


def not_compared_rule_output_lines() -> list[str]:
    """The "not compared" lines of a run without --second-targets."""
    lines = ["not compared: no --second-targets was given, so these values of the rule output are not compared:"]
    lines += [f"  - {v}" for v in RULE_OUTPUT_VALUES]
    lines.append("  - variant.reachable (not compared in any run: second_rule3.py and trace/rule3.py "
                 "word this text differently)")
    lines.append("  " + variant_only_first_text(False))
    return lines


def expectations_line(subject: str, class_a_given: bool) -> str:
    """The summary line that says which values of expectations T1, T2 and T3 are compared."""
    t1 = ("T1 compared: the rule-2 and rule-3 flag counts and the bound of 10. T1 not compared: 'falls', "
          "the combined verdict 'holds' and 'stated_values_for_joserfc' of second_rule3.py. The protocol "
          "states T1 for joserfc only, and the first outputs hold no T1 verdict in a file")
    if subject == "joserfc":
        t1 += "; for joserfc the trace README states 'not met'"
    if class_a_given:
        t2 = ("T2 compared: the set of class-A cases and, per case, whether it keeps its target. T2 not "
              "compared: the verdict 'holds' and the outcome-7 set, which the first outputs do not hold")
    else:
        t2 = ("T2 not compared: no --class-a-tsv was given, and the class-A cases come from a reading. "
              "The outcome-7 set has no counterpart in the first outputs")
    t3 = "T3 compared: the counts under both rules and the verdict (at least 85 %)"
    sentinels = ("Sentinels compared: T1 of targets.json with each of the 2 rule-2 equalities (see the "
                 "line on rule 2), and T2 of compare.json. Not compared: T4 and R2 of compare.json")
    return f"expectations: {t1}. {t2}. {t3}. {sentinels}."


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="compare second_rule3.py with rule3.py and analyse3.py")
    ap.add_argument("--second", required=True)
    ap.add_argument("--second-targets")
    ap.add_argument("--first", required=True)
    ap.add_argument("--first-compare")
    ap.add_argument("--class-a-tsv")
    args = ap.parse_args(argv)
    try:
        sdoc = load_json(Path(args.second), "the second output")
        stargets = load_json(Path(args.second_targets), "the second rule output") if args.second_targets else None
        folder = Path(args.first)
        cpath = Path(args.first_compare) if args.first_compare else folder.parent / "compare.json"
        if sdoc["expectations"]["T2"].get("class_a_cases_given") is not None and not args.class_a_tsv:
            raise InputError("the second output carries class-A cases (expectations.T2.class_a_cases_given); "
                             "give the first reading with --class-a-tsv")
        first = First(folder, cpath, sdoc["subject"], Path(args.class_a_tsv) if args.class_a_tsv else None)
        m = mappings(Second(sdoc, stargets), first)
    except InputError as exc:
        print(f"compare_rule3: {exc}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, AttributeError) as exc:
        print(f"compare_rule3: an input is malformed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    compared, agree, diffs = compare(m)
    print(f"{sdoc['subject']}: compared {compared}, agree {agree}, differ {compared - agree}")
    try:
        toolkit_lines = toolkit_second_lines(m)
        rule_lines = rule_code_lines(m, stargets is not None)
    except ValueError as exc:
        print(f"compare_rule3: {exc}", file=sys.stderr)
        return 1
    for line in toolkit_lines + rule_lines:
        print(line)
    print(rule2_equalities_line())
    print(expectations_line(sdoc["subject"], first.class_a is not None))
    if stargets is None:
        for line in not_compared_rule_output_lines():
            print(line)
    else:
        print(not_compared_variant_line())
    for d in diffs:
        print(d)
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

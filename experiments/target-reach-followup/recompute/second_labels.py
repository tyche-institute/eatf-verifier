"""Second computation of the label counts of PROTOCOL.md, for 1 subject.

    python3 -I -B recompute/second_labels.py \
        --subject ../target-reach/subjects/<name>/subject.json \
        --records ../target-reach/generated/<name>/records.tar.xz \
        --labels A.tsv [B.tsv] [--targets3 FILE] [--first FILE] --out FILE.json \
        [--toolkit DIR]

Inputs:

- `--subject`: `subject.json` of the toolkit; `checks.json`, `blocks.json` and
  `targets.json` (the targets of rule 2) are read beside it.
- `--records`: the deposited `records.tar.xz` of the toolkit, or a directory
  unpacked from it. The archive is unpacked by `recompute/second.py` of the
  toolkit (`records_root`), which checks its members.
- `--labels`: 1 or 2 labels files (TSV, csv excel-tab dialect, columns
  `block`, `label`, `basis`, `quote`, `note`), reading A and reading B.
- `--targets3`: optional `targets.json` of rule 3 (same format as the
  toolkit's `targets.json`).
- `--first`: optional transcription of the first reading of the flags (TSV,
  columns `block`, `index`, `test_node`, `class`, `target`,
  `deciding_check`, `described_check`, ...).
- `--toolkit`: the folder `target-reach` (default: `../../target-reach`
  relative to this file). Only `recompute/second.py` is imported from it,
  for the unpacking of the records and the status of a case in a deletion
  run (section 4 of the toolkit protocol, 'Status of a case').

Groups of counts in the output (sections of PROTOCOL.md):

- `readings`: the form of each labels file, the by-parameter labels and
  their resolution per case (section 4.1, 'Reading').
- `agreement`: per included block, 1 of 4 categories; the agreed label;
  the observed agreement and Cohen's kappa with every distinct label text
  as a category and with the 2 categories "names a check" and "none", with
  the marginal counts that a pooled kappa needs (section 4.1, 'Agreement').
- `outcomes`: for every case of the study, the outcome (1 to 8, or "fired
  checks not recorded") of each reading and of the agreed label (section
  4.1, 'Outcome of a case with an agreed label that names a check').
- `shadowed`: the cases of outcome 7 under the agreed label and under each
  reading, the cases that meet the same condition with the target of rule
  2 in place of the label, the class-A rows of the first reading, and for
  each shadowed case the sources that show it (section 4.1, 'shadowed').
- `program_vs_label`: for rule 2 and rule 3, per case and per block, 1 of 6
  categories, overall, per tier and per basis of the rule (section 4.1,
  'Program against label').
- `first_reading`: per flag of the first reading, its described check
  against the agreed label, overall and per class (section 4.1, 'First
  reading').
- `expectations`: L1, L2 and L3 with the units and counts behind each
  (section 2, 'Labels').
- `cases`: the per-case table from which every case count is taken.

A case is keyed `<test node>|<block>|<index>`. Every count that is the size
of a set comes with the list of its members. The script prints 1 summary
line and exits with 0; it exits with 2 when an input is missing or
malformed.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TOOLKIT = HERE.parent.parent / "target-reach"

NONE = "none"
NO_AGREED = "(no agreed label)"
UNRESOLVED = "(by-param label does not resolve)"

OUTCOMES = {
    1: "decided by its label",
    2: "label fires and another check decides",
    3: "label fires and no check decides",
    4: "label does not fire and no check decides",
    5: "deciding check not deleted or record missing",
    6: "label does not fire; case not observed on the copy without the deciding check",
    7: "label does not fire and decides once the deciding check is deleted",
    8: "label does not fire and does not decide then either",
}
NOT_RECORDED = "fired checks not recorded"
OUTCOME_KEYS = [f"{k} {v}" for k, v in OUTCOMES.items()] + [NOT_RECORDED]

AGREEMENT = ("same check", "both none", "1 check and 1 none", "2 different checks")
PVL = ("target equals agreed label", "target differs from agreed label",
       "target given, agreed label none", "no target, agreed label names a check",
       "both none", "no agreed label")
FIRST_CATS = ("agreed label equals described check", "agreed label differs from described check",
              "agreed label none, described check given", "agreed label names a check, no described check",
              "agreed label none, no described check", "no agreed label")


class InputError(Exception):
    """An input is missing or malformed."""


# -- loading ---------------------------------------------------------------------------

def load_json(path: Path):
    if not path.exists() or path.is_dir():
        raise InputError(f"missing file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise InputError(f"not readable as JSON: {path}: {e}")


def read_tsv(path: Path, required: list[str]) -> list[dict]:
    if not path.exists() or path.is_dir():
        raise InputError(f"missing file: {path}")
    try:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh, dialect="excel-tab")
            header = reader.fieldnames or []
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        raise InputError(f"not readable as TSV: {path}: {e}")
    missing = [c for c in required if c not in header]
    if missing:
        raise InputError(f"{path}: header lacks the columns {missing} (header: {header})")
    for i, r in enumerate(rows, start=2):
        if None in r:
            raise InputError(f"{path}: line {i} has more cells than the header")
    return rows


def import_second(toolkit: Path):
    path = toolkit / "recompute" / "second.py"
    if not path.is_file():
        raise InputError(f"missing file: {path}")
    spec = importlib.util.spec_from_file_location("toolkit_second", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -- labels ----------------------------------------------------------------------------

BY_PARAM = re.compile(r"^by-param\s+([^:]+?)\s*:\s*(.+)$")


def parse_label(text: str, check_ids: set) -> dict:
    """{'kind': 'check'|'none'|'by-param', 'text': normalized text, ...}.

    The text of a by-parameter label is normalized by sorting its values
    (section 4.1, 'Agreement'); white space around each part is stripped."""
    t = text.strip()
    if t == NONE:
        return {"kind": "none", "text": NONE}
    if t in check_ids:
        return {"kind": "check", "text": t, "check": t}
    m = BY_PARAM.match(t)
    if not m:
        raise InputError(f"label {t!r} is neither a check of checks.json, nor 'none', nor a by-param label")
    name = m.group(1).strip()
    values: dict[str, str] = {}
    for item in m.group(2).split(";"):
        item = item.strip()
        if not item:
            continue
        v, eq, target = item.partition("=")
        v, target = v.strip(), target.strip()
        if not eq or not v or not target:
            raise InputError(f"by-param label {t!r}: item {item!r} is not <value>=<id or none>")
        if "-" in v or "=" in v:
            raise InputError(f"by-param label {t!r}: value {v!r} holds a hyphen or an equals sign")
        if v in values:
            raise InputError(f"by-param label {t!r}: value {v!r} given 2 times")
        if target != NONE and target not in check_ids:
            raise InputError(f"by-param label {t!r}: {target!r} is not a check of checks.json")
        values[v] = target
    if len(values) < 2:
        raise InputError(f"by-param label {t!r}: fewer than 2 values")
    items = sorted(f"{v}={values[v]}" for v in values)
    return {"kind": "by-param", "text": f"by-param {name}: " + "; ".join(items),
            "param": name, "values": values}


def names_a_check(lab: dict) -> bool:
    """A label names a check when it is a check id, or a by-param label with at
    least 1 value that is a check id."""
    if lab["kind"] == "check":
        return True
    if lab["kind"] == "by-param":
        return any(v != NONE for v in lab["values"].values())
    return False


def bracket_parts(test_node: str) -> list[str]:
    i = test_node.find("[")
    if i < 0 or not test_node.endswith("]"):
        return []
    return test_node[i + 1:-1].split("-")


def resolve(lab: dict | None, test_node: str) -> str:
    """The label of 1 case: a check id, 'none', NO_AGREED or UNRESOLVED."""
    if lab is None:
        return NO_AGREED
    if lab["kind"] != "by-param":
        return lab["text"]
    parts = bracket_parts(test_node)
    hits = [v for v in lab["values"] if v in parts]
    if len(hits) != 1:
        return UNRESOLVED
    return lab["values"][hits[0]]


def read_labels(path: Path, included: list[str], check_ids: set) -> tuple[dict, list[str]]:
    """{block: parsed label}, and the form remarks that do not stop the computation."""
    rows = read_tsv(path, ["block", "label"])
    inc = set(included)
    out: dict[str, dict] = {}
    remarks: list[str] = []
    for i, r in enumerate(rows, start=2):
        b = (r.get("block") or "").strip()
        if b not in inc:
            raise InputError(f"{path}: line {i}: block {b!r} is not an included block of blocks.json")
        if b in out:
            raise InputError(f"{path}: line {i}: block {b} given 2 times")
        try:
            lab = parse_label(r.get("label") or "", check_ids)
        except InputError as e:
            raise InputError(f"{path}: line {i}: {e}")
        basis = (r.get("basis") or "").strip()
        note = (r.get("note") or "").strip()
        if "basis" in r:
            if lab["kind"] == "none" and basis != NONE:
                remarks.append(f"{b}: label none with basis {basis!r}")
            if lab["kind"] != "none" and (basis == NONE or not basis):
                remarks.append(f"{b}: label names a check with basis {basis!r}")
        if "note" in r and lab["kind"] == "none" and not note:
            remarks.append(f"{b}: label none without a note")
        out[b] = lab
    missing = sorted(inc - set(out))
    if missing:
        raise InputError(f"{path}: {len(missing)} included blocks have no row, first: {missing[0]}")
    return out, remarks


# -- statistics ------------------------------------------------------------------------

def fraction_text(f: Fraction) -> str:
    return f"{f.numerator}/{f.denominator}"


def kappa(a: list[str], b: list[str]) -> dict:
    """Observed agreement and Cohen's kappa of 2 lists of categories."""
    n = len(a)
    ca, cb = Counter(a), Counter(b)
    out = {"units": n, "categories": len(set(a) | set(b)),
           "marginals_reading_A": dict(sorted(ca.items())),
           "marginals_reading_B": dict(sorted(cb.items()))}
    if n == 0:
        out.update(agree=0, observed_agreement=None, expected_agreement=None, kappa=None,
                   kappa_note="no units")
        return out
    agree = sum(1 for x, y in zip(a, b) if x == y)
    po = Fraction(agree, n)
    pe = sum((Fraction(ca[k], n) * Fraction(cb[k], n) for k in set(ca) | set(cb)), Fraction(0))
    out.update(agree=agree, observed_agreement=round(float(po), 9),
               observed_agreement_fraction=fraction_text(po),
               expected_agreement=round(float(pe), 9), expected_agreement_fraction=fraction_text(pe))
    if pe == 1:
        out.update(kappa=None, kappa_note="1 category holds every label of both readings")
    else:
        k = (po - pe) / (1 - pe)
        out.update(kappa=round(float(k), 9), kappa_fraction=fraction_text(k))
    return out


def counted(groups: dict[str, list], order) -> dict:
    """{'counts': {category: n}, 'ids': {category: sorted ids}} in a fixed order."""
    return {"counts": {k: len(groups.get(k, [])) for k in order},
            "ids": {k: sorted(groups.get(k, [])) for k in order},
            "total": sum(len(v) for v in groups.values())}


# -- the computation -------------------------------------------------------------------

def compute(args, second) -> dict:
    subject_path = Path(args.subject)
    defs = subject_path.parent
    subject = load_json(subject_path)
    checks_doc = load_json(defs / "checks.json")
    blocks_doc = load_json(defs / "blocks.json")
    targets2_doc = load_json(defs / "targets.json")
    targets3_doc = load_json(Path(args.targets3)) if args.targets3 else None

    try:
        check_ids = {c["id"] for c in checks_doc["checks"]}
        blocks = {b["key"]: b for b in blocks_doc["blocks"]}
        included = sorted(k for k, b in blocks.items() if b["included"])
    except (KeyError, TypeError) as e:
        raise InputError(f"checks.json or blocks.json lacks an expected field: {e}")

    def targets_of(doc, name):
        try:
            rows = {r["key"]: r for r in doc["blocks"]}
        except (KeyError, TypeError) as e:
            raise InputError(f"{name}: lacks an expected field: {e}")
        if set(rows) != set(included):
            raise InputError(f"{name}: its blocks are not the included blocks of blocks.json "
                             f"({len(set(rows) - set(included))} extra, {len(set(included) - set(rows))} missing)")
        for k, r in rows.items():
            t = r.get("target")
            if t is not None and t not in check_ids:
                raise InputError(f"{name}: target {t!r} of {k} is not a check of checks.json")
        return {k: {"target": r.get("target"), "tier": r.get("tier"), "basis": r.get("basis")}
                for k, r in rows.items()}

    rules = {"rule 2": targets_of(targets2_doc, "targets.json")}
    if targets3_doc is not None:
        rules["rule 3"] = targets_of(targets3_doc, str(args.targets3))
    t2 = rules["rule 2"]

    # -- records --
    keep: list = []
    try:
        root = second.records_root(str(args.records), keep)
    except SystemExit as e:
        raise InputError(f"records: {e}")
    except Exception as e:  # a damaged or absent archive
        raise InputError(f"records: cannot be read: {args.records}: {e}")
    base1 = root / "base-1.json"
    if not base1.is_file():
        raise InputError(f"records: base-1.json is absent in {args.records}")
    base = load_json(base1)
    manifest_path = root / "deletions" / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    nr_path = root / "deletions" / "no-record.json"
    no_record = load_json(nr_path) if nr_path.is_file() else {}
    fired_recorded = bool(base.get("fired_recorded"))

    # cases of the study (toolkit protocol, section 4, 'Case')
    study = []
    for c in base.get("cases", []):
        if not c.get("included"):
            continue
        if c.get("raised") and c.get("rejection") and c.get("check_result") == "accepted":
            if c.get("block") not in blocks:
                raise InputError(f"records: case of unknown block {c.get('block')}")
            study.append(c)
    ck = second.case_key

    def decider(c):
        s = c.get("site") or {}
        return s.get("check") if s.get("kind") == "check" and s.get("check") else None

    deletion_runs: dict[str, dict | None] = {}

    def deletion_run(check: str):
        """(cases, tests) of the recorder run without `check`, or None."""
        if check in deletion_runs:
            return deletion_runs[check]
        run = None
        if check in manifest and check not in no_record:
            p = root / "deletions" / f"{manifest[check]['dir']}.json"
            if p.is_file():
                rec = load_json(p)
                run = ({ck(x): x for x in rec.get("cases", []) if x.get("included")},
                       {t["nodeid"]: t for t in rec.get("tests", [])})
        deletion_runs[check] = run
        return run

    def outcome(label: str, c: dict) -> str | None:
        """Section 4.1, the first outcome that applies, for a label that names a check."""
        d = decider(c)
        if label == d:
            return OUTCOME_KEYS[0]
        fired = c.get("fired")
        if not fired_recorded or fired is None:
            return NOT_RECORDED
        fires = label in set(fired) | ({d} if d else set())
        if fires and d is not None:
            return OUTCOME_KEYS[1]
        if fires:
            return OUTCOME_KEYS[2]
        if d is None:
            return OUTCOME_KEYS[3]
        run = deletion_run(d)
        if run is None:
            return OUTCOME_KEYS[4]
        run_cases, run_tests = run
        key = ck(c)
        if second.status_of(key, c["test"], run_cases, run_tests) != "observed":
            return OUTCOME_KEYS[5]
        site = run_cases[key].get("site") or {}
        if site.get("kind") == "check" and site.get("check") == label:
            return OUTCOME_KEYS[6]
        return OUTCOME_KEYS[7]

    # -- readings --
    reading_names = ["A", "B"][:len(args.labels)]
    readings: dict[str, dict] = {}
    remarks: dict[str, list] = {}
    for name, path in zip(reading_names, args.labels):
        readings[name], remarks[name] = read_labels(Path(path), included, check_ids)

    out: dict = {"subject": subject.get("name"), "version": subject.get("version"),
                 "protocol": "PROTOCOL.md, sections 2 (L1, L2, L3) and 4.1",
                 "inputs": {"readings": len(readings), "rule 3 targets given": targets3_doc is not None,
                            "first reading given": bool(args.first),
                            "fired checks recorded": fired_recorded,
                            "included blocks": len(included), "cases of the study": len(study),
                            "deletions in the manifest": len(manifest)}}

    out["readings"] = {}
    for name in reading_names:
        labs = readings[name]
        kinds = {k: sorted(b for b, l in labs.items() if l["kind"] == k) for k in ("check", "none", "by-param")}
        out["readings"][name] = {
            "file": Path(dict(zip(reading_names, args.labels))[name]).name,
            "blocks": len(labs),
            "blocks_labeled_with_a_check": len(kinds["check"]),
            "blocks_labeled_none": len(kinds["none"]),
            "blocks_labeled_by_param": len(kinds["by-param"]),
            "blocks_labeled_by_param_ids": kinds["by-param"],
            "form_remarks": remarks[name],
        }

    # -- agreement --
    agreed: dict[str, dict | None] = {}
    agreement: dict = {}
    if len(readings) == 2:
        A, B = readings["A"], readings["B"]
        groups: dict[str, list] = {}
        both_answers = {}
        for b in included:
            la, lb = A[b], B[b]
            ca, cb = names_a_check(la), names_a_check(lb)
            if la["text"] == lb["text"]:
                cat = AGREEMENT[0] if ca else AGREEMENT[1]
                agreed[b] = la
            else:
                if ca != cb:
                    cat, agreed[b] = AGREEMENT[2], None
                elif ca:
                    cat, agreed[b] = AGREEMENT[3], None
                else:
                    # 2 texts that name no check: 'none' and a by-param label whose
                    # every value is 'none'; both give 'none' for every case.
                    cat, agreed[b] = AGREEMENT[1], {"kind": "none", "text": NONE}
                if agreed[b] is None:
                    both_answers[b] = {"A": la["text"], "B": lb["text"]}
            groups.setdefault(cat, []).append(b)
        agreement = {
            "categories": counted(groups, AGREEMENT),
            "blocks_without_an_agreed_label_with_both_answers": dict(sorted(both_answers.items())),
            "every_label_text_as_a_category": kappa([A[b]["text"] for b in included],
                                                     [B[b]["text"] for b in included]),
            "names_a_check_or_none": kappa(
                ["names a check" if names_a_check(A[b]) else "none" for b in included],
                ["names a check" if names_a_check(B[b]) else "none" for b in included]),
        }
    else:
        only = readings["A"]
        for b in included:
            agreed[b] = only[b]
        agreement = {"categories": "1 reading: every block is single; its label is the agreed label",
                     "every_label_text_as_a_category": None, "names_a_check_or_none": None}
    agreed_blocks = {k: sorted(b for b in included if agreed[b] is not None
                               and (names_a_check(agreed[b]) if k == "check" else not names_a_check(agreed[b])))
                     for k in ("check", "none")}
    agreement["blocks_with_an_agreed_label_naming_a_check"] = len(agreed_blocks["check"])
    agreement["blocks_with_an_agreed_label_naming_a_check_ids"] = agreed_blocks["check"]
    agreement["blocks_with_agreed_label_none"] = len(agreed_blocks["none"])
    agreement["blocks_with_agreed_label_none_ids"] = agreed_blocks["none"]
    agreement["blocks_without_an_agreed_label"] = sum(1 for b in included if agreed[b] is None)
    out["agreement"] = agreement

    # -- per case --
    cases: dict[str, dict] = {}
    unresolved: dict[str, list] = {}
    for c in study:
        key = ck(c)
        b = c["block"]
        row = {"test": c["test"], "block": b, "index": c.get("index"), "deciding_check": decider(c),
               "raise_site_kind": (c.get("site") or {}).get("kind"),
               "fired": sorted(c.get("fired") or []) if c.get("fired") is not None else None}
        labels_here = {name: resolve(readings[name][b], c["test"]) for name in reading_names}
        labels_here["agreed"] = resolve(agreed[b], c["test"])
        row["labels"] = labels_here
        row["outcomes"] = {}
        for name, lab in labels_here.items():
            if lab == UNRESOLVED:
                unresolved.setdefault(name, []).append(key)
            if lab not in (NONE, NO_AGREED, UNRESOLVED):
                row["outcomes"][name] = outcome(lab, c)
            else:
                row["outcomes"][name] = None
        for rule, tg in rules.items():
            row[rule] = dict(tg[b])
        t = t2[b]["target"]
        row["rule 2 target outcome as label"] = outcome(t, c) if t else None
        cases[key] = row
    out["cases"] = cases
    out["readings"]["by_param_cases_that_do_not_resolve"] = {k: sorted(v) for k, v in sorted(unresolved.items())}

    # -- outcomes --
    outs = {}
    for name in reading_names + ["agreed"]:
        groups = {}
        for key, row in cases.items():
            o = row["outcomes"][name]
            if o is not None:
                groups.setdefault(o, []).append(key)
        lab_groups = Counter(
            "names a check" if row["labels"][name] not in (NONE, NO_AGREED, UNRESOLVED) else row["labels"][name]
            for row in cases.values())
        outs[name] = {"cases_by_label": dict(sorted(lab_groups.items())), "outcomes": counted(groups, OUTCOME_KEYS)}
    out["outcomes"] = outs

    # -- first reading --
    first_rows = []
    if args.first:
        first_rows = read_tsv(Path(args.first), ["block", "index", "test_node", "class", "target",
                                                  "deciding_check", "described_check"])
    flag_cases = []
    for i, r in enumerate(first_rows, start=2):
        b = (r["block"] or "").strip()
        try:
            idx = int((r["index"] or "").strip())
        except ValueError:
            raise InputError(f"{args.first}: line {i}: index {r['index']!r} is not a number")
        node = (r["test_node"] or "").strip()
        key = f"{node}|{b}|{idx}"
        desc = (r["described_check"] or "").strip() or None
        if desc is not None and desc not in check_ids:
            raise InputError(f"{args.first}: line {i}: described check {desc!r} is not a check of checks.json")
        flag_cases.append({"key": key, "block": b, "class": (r["class"] or "").strip(), "described": desc,
                           "target_in_row": (r["target"] or "").strip() or None,
                           "deciding_in_row": (r["deciding_check"] or "").strip() or None, "line": i})

    first: dict = {"given": bool(args.first), "rows": len(flag_cases)}
    if args.first:
        groups, by_class, rows_out = {}, {}, {}
        not_found, mismatches = [], []
        for f in flag_cases:
            row = cases.get(f["key"])
            if row is None:
                not_found.append(f["key"])
                continue
            lab = row["labels"]["agreed"]
            desc = f["described"]
            if lab in (NO_AGREED, UNRESOLVED):
                cat = FIRST_CATS[5]
            elif lab == NONE:
                cat = FIRST_CATS[2] if desc else FIRST_CATS[4]
            elif desc is None:
                cat = FIRST_CATS[3]
            else:
                cat = FIRST_CATS[0] if lab == desc else FIRST_CATS[1]
            groups.setdefault(cat, []).append(f["key"])
            by_class.setdefault(f["class"], {}).setdefault(cat, []).append(f["key"])
            if f["target_in_row"] != t2[f["block"]]["target"]:
                mismatches.append(f"{f['key']}: target in the row {f['target_in_row']}, "
                                  f"targets.json {t2[f['block']]['target']}")
            if f["deciding_in_row"] != row["deciding_check"]:
                mismatches.append(f"{f['key']}: deciding check in the row {f['deciding_in_row']}, "
                                  f"records {row['deciding_check']}")
            rows_out[f["key"]] = {"class": f["class"], "described_check": desc, "agreed_label": lab,
                                  "category": cat, "agreed_label_outcome": row["outcomes"]["agreed"],
                                  "rule 2 target": t2[f["block"]]["target"],
                                  "deciding_check": row["deciding_check"]}
        first.update({
            "categories": counted(groups, FIRST_CATS),
            "categories_by_class": {k: counted(v, FIRST_CATS) for k, v in sorted(by_class.items())},
            "rows_by_class": dict(sorted(Counter(f["class"] for f in flag_cases).items())),
            "rows_whose_case_is_not_a_case_of_the_study": sorted(not_found),
            "rows_that_differ_from_targets_json_or_the_records": mismatches,
            "per_flag": rows_out,
        })
    out["first_reading"] = first

    # -- shadowed --
    shadow_label = {name: sorted(k for k, r in cases.items() if r["outcomes"][name] == OUTCOME_KEYS[6])
                    for name in reading_names + ["agreed"]}
    shadow_target = sorted(k for k, r in cases.items() if r["rule 2 target outcome as label"] == OUTCOME_KEYS[6])
    class_a = [f for f in flag_cases if f["class"] == "A"]
    class_a_rows = {}
    for f in class_a:
        row = cases.get(f["key"])
        t = t2[f["block"]]["target"]
        class_a_rows[f["key"]] = {
            "rule 2 target": t,
            "target outcome as label": row["rule 2 target outcome as label"] if row else None,
            "meets the condition with the target in place of the label":
                bool(row) and row["rule 2 target outcome as label"] == OUTCOME_KEYS[6],
        }
    sources: dict[str, list] = {}
    for k in shadow_label["agreed"]:
        sources.setdefault(k, []).append("agreed label")
    for f in class_a:
        sources.setdefault(f["key"], []).append("first reading, class A (program target)")
    shadowed_cases = {}
    for k, src in sorted(sources.items()):
        r = cases.get(k)
        shadowed_cases[k] = {
            "sources": src,
            "described_check": (r["labels"]["agreed"] if "agreed label" in src else
                                t2[r["block"]]["target"]) if r else None,
            "deciding_check": r["deciding_check"] if r else None,
            "agreed_label": r["labels"]["agreed"] if r else None,
            "class_a_row_meets_the_condition_with_the_rule_2_target":
                class_a_rows[k]["meets the condition with the target in place of the label"]
                if k in class_a_rows else None,
        }
    out["shadowed"] = {
        "by_agreed_label": len(shadow_label["agreed"]),
        "by_agreed_label_ids": shadow_label["agreed"],
        "by_reading": {n: {"count": len(shadow_label[n]), "ids": shadow_label[n]} for n in reading_names},
        "by_rule_2_target_in_place_of_the_label": len(shadow_target),
        "by_rule_2_target_in_place_of_the_label_ids": shadow_target,
        "first_reading_class_a_rows": class_a_rows,
        "shadowed_cases_with_sources": shadowed_cases,
        "shadowed_cases_count": len(shadowed_cases),
    }

    # -- program against label --
    def pvl_category(target, lab) -> str:
        if lab in (NO_AGREED, UNRESOLVED):
            return PVL[5]
        if target and lab != NONE:
            return PVL[0] if target == lab else PVL[1]
        if target:
            return PVL[2]
        if lab != NONE:
            return PVL[3]
        return PVL[4]

    def pvl_block_category(target, lab: dict | None) -> str:
        if lab is None:
            return PVL[5]
        if lab["kind"] == "by-param":
            if not names_a_check(lab):
                return PVL[2] if target else PVL[4]
            if not target:
                return PVL[3]
            return PVL[0] if all(v == target for v in lab["values"].values()) else PVL[1]
        return pvl_category(target, lab["text"])

    pvl = {}
    for rule, tg in rules.items():
        per_case, per_tier, per_basis = {}, {}, {}
        for key, row in cases.items():
            info = tg[row["block"]]
            cat = pvl_category(info["target"], row["labels"]["agreed"])
            per_case.setdefault(cat, []).append(key)
            per_tier.setdefault(info["tier"] or "no target", {}).setdefault(cat, []).append(key)
            per_basis.setdefault(info["basis"] or "no target", {}).setdefault(cat, []).append(key)
        per_block, per_block_tier, per_block_basis = {}, {}, {}
        for b in included:
            info = tg[b]
            cat = pvl_block_category(info["target"], agreed[b])
            per_block.setdefault(cat, []).append(b)
            per_block_tier.setdefault(info["tier"] or "no target", {}).setdefault(cat, []).append(b)
            per_block_basis.setdefault(info["basis"] or "no target", {}).setdefault(cat, []).append(b)
        pvl[rule] = {
            "per_case": counted(per_case, PVL),
            "per_case_by_tier": {k: counted(v, PVL) for k, v in sorted(per_tier.items())},
            "per_case_by_basis": {k: counted(v, PVL) for k, v in sorted(per_basis.items())},
            "per_block": counted(per_block, PVL),
            "per_block_by_tier": {k: counted(v, PVL) for k, v in sorted(per_block_tier.items())},
            "per_block_by_basis": {k: counted(v, PVL) for k, v in sorted(per_block_basis.items())},
        }
    if "rule 3" in rules:
        moves = {}
        for b in included:
            a, z = rules["rule 2"][b]["target"], rules["rule 3"][b]["target"]
            kind = ("keeps" if a == z else "changes") if a and z else ("loses" if a else ("gains" if z else "neither"))
            moves.setdefault(kind, []).append(b)
        pvl["blocks_rule_2_to_rule_3"] = counted(moves, ("keeps", "changes", "gains", "loses", "neither"))
    else:
        pvl["rule 3"] = "not given"
    out["program_vs_label"] = pvl

    # -- expectations L1, L2, L3 --
    exp = {}
    if not args.first:
        exp["L1"] = {"status": "not applicable", "reason": "no first reading given", "units": 0}
        exp["L2"] = {"status": "not applicable", "reason": "no first reading given", "units": 0}
    else:
        units, ok, detail = [], [], {}
        for f in class_a:
            row = cases.get(f["key"])
            t = t2[f["block"]]["target"]
            labs = {n: (row["labels"][n] if row else None) for n in reading_names}
            good = bool(row) and t is not None and all(l == t for l in labs.values())
            units.append(f["key"])
            if good:
                ok.append(f["key"])
            detail[f["key"]] = {"rule 2 target": t, "labels": labs, "holds": good}
        exp["L1"] = {"units": len(units), "units_ids": sorted(units), "holding": len(ok),
                     "holding_ids": sorted(ok), "detail": detail, "readings_compared": reading_names,
                     "status": "not applicable" if not units else ("held" if len(ok) == len(units) else "not held")}
        units, ok, excluded, detail = [], [], [], {}
        for f in flag_cases:
            if f["class"] != "C":
                continue
            row = cases.get(f["key"])
            lab = row["labels"]["agreed"] if row else NO_AGREED
            if lab in (NONE, NO_AGREED, UNRESOLVED):
                excluded.append(f["key"])
                continue
            t = t2[f["block"]]["target"]
            units.append(f["key"])
            if lab != t:
                ok.append(f["key"])
            detail[f["key"]] = {"agreed label": lab, "rule 2 target": t, "holds": lab != t}
        exp["L2"] = {"units": len(units), "units_ids": sorted(units), "holding": len(ok),
                     "holding_ids": sorted(ok), "class_c_flags": sum(1 for f in flag_cases if f["class"] == "C"),
                     "class_c_flags_without_an_agreed_label_naming_a_check": sorted(excluded),
                     "detail": detail,
                     "status": "not applicable" if not units else ("held" if len(ok) == len(units) else "not held")}

    def l3(rule: str) -> dict:
        units, ok, bad = [], [], {}
        for key, row in cases.items():
            t = rules[rule][row["block"]]["target"]
            lab = row["labels"]["agreed"]
            if not t or row["deciding_check"] != t or lab in (NONE, NO_AGREED, UNRESOLVED):
                continue
            units.append(key)
            if lab == t:
                ok.append(key)
            else:
                bad[key] = {"target": t, "agreed label": lab}
        return {"units": len(units), "units_ids": sorted(units), "holding": len(ok),
                "not_holding": dict(sorted(bad.items())),
                "status": "not applicable" if not units else ("held" if not bad else "not held")}
    exp["L3"] = l3("rule 2")
    if "rule 3" in rules:
        exp["L3_with_rule_3_targets_supplementary"] = l3("rule 3")
    out["expectations"] = exp
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", required=True)
    ap.add_argument("--records", required=True)
    ap.add_argument("--labels", required=True, nargs="+")
    ap.add_argument("--targets3")
    ap.add_argument("--first")
    ap.add_argument("--out", required=True)
    ap.add_argument("--toolkit", default=str(DEFAULT_TOOLKIT))
    a = ap.parse_args(argv)
    try:
        if len(a.labels) > 2:
            raise InputError(f"--labels takes 1 or 2 files, not {len(a.labels)}")
        for p in [a.subject, a.records, *a.labels] + [x for x in (a.targets3, a.first) if x]:
            if not Path(p).exists():
                raise InputError(f"missing input: {p}")
        second = import_second(Path(a.toolkit))
        data = compute(a, second)
    except InputError as e:
        print(f"second_labels: {e}", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    o = data["outcomes"]["agreed"]["outcomes"]["counts"]
    e = data["expectations"]
    print(f"{data['subject']}: {data['inputs']['included blocks']} included blocks, "
          f"{data['inputs']['readings']} reading(s), {data['inputs']['cases of the study']} cases of the study, "
          f"{sum(o.values())} with an agreed label naming a check; outcomes "
          + " ".join(f"{k.split(' ')[0] if k[0].isdigit() else 'nr'}={v}" for k, v in o.items())
          + f"; shadowed {data['shadowed']['shadowed_cases_count']}; "
          + "; ".join(f"{k} {e[k]['status']}" for k in ("L1", "L2", "L3")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

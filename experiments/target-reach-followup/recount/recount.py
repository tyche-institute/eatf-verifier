"""Recounts from the deposited outputs of the toolkit "target reach".

Reads, for each subject, only deposited files of `../target-reach`:
`generated/<name>/{cases,checks,deletions,flags,pinning}.csv`, `summary.json`,
`records.tar.xz` (extracted into a work folder, of which only the first
baseline record `records/base-1.json` is read), `subjects/<name>/*.json` and
the table of `readings/<name>/FLAGS.md`. No library is run.

Writes `recount.json` and `RECOUNT.md`, then exits with status 1 unless every
sentinel holds. `README.md` beside this file defines every count.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tarfile
from collections import Counter
from pathlib import Path

SUBJECTS = ["pyjwt", "pyjwt-package", "jwcrypto", "google-auth", "oauthlib", "authlib", "joserfc"]
HELD_OUT = ["google-auth", "oauthlib", "authlib", "joserfc"]
PYJWT = ["pyjwt", "pyjwt-package"]
ORACLES = ["O_V", "O_Vfc", "O_C", "O_T", "O_S", "suite", "whole suite"]
SENTINEL_ORACLES = ["O_V", "O_Vfc", "O_C", "O_T", "whole suite"]
COLUMN = {"whole suite": "whole_suite"}
CLASSES = ["A", "B", "C", "D"]
TIERS = ["assertion", "name"]

# Totals over the 4 held-out libraries that the recount must reproduce.
HELD_OUT_TOTALS = {
    "cases": 402,
    "cases_with_target": 229,
    "cases_decided_by_target": 145,
    "flags": 84,
    "checks_deciding": 137,
    "not_detected": {"O_V": 24, "O_Vfc": 57, "O_C": 6, "O_T": 82, "whole suite": 5},
}


# -- reading ------------------------------------------------------------------------

def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def extract_records(archive: Path, dest: Path) -> Path:
    """Extracts `records.tar.xz` into `dest` and returns the path of base-1.json."""
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:xz") as tar:
        tar.extractall(dest, filter="data")
    return dest / "records" / "base-1.json"


CASE_LABEL = re.compile(r"^(?P<name>[^#\s]+)#(?P<k>\d+)(?: \[(?P<i>\d+)\])?$")


def parse_flags_md(text: str) -> tuple[list[dict], dict | None]:
    """Parses the table that starts with '| Case |' and the line 'Counts: A n, ...'.

    Each row gives the test node it names, the block number k, the execution
    index i (0 when the label has no '[i]'), the 2 mechanical columns and the
    class."""
    rows: list[dict] = []
    lines = text.splitlines()
    start = next((n for n, line in enumerate(lines) if line.startswith("| Case |")), None)
    if start is not None:
        for line in lines[start + 2:]:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            first = cells[0]
            ticks = re.findall(r"`([^`]*)`", first)
            m = CASE_LABEL.match(ticks[0])
            if m is None:
                raise ValueError(f"unparsed case label: {ticks[0]!r}")
            if "run under" in first:
                test_file = ticks[-1]
                block_file = ticks[1].rsplit(":", 1)[0]
            else:
                test_file = ticks[1].rsplit(":", 1)[0]
                block_file = test_file
            rows.append({
                "label": ticks[0],
                "test_node": test_file + "::" + m.group("name").replace(".", "::"),
                "block_file": block_file,
                "k": int(m.group("k")),
                "index": int(m.group("i") or 0),
                "target_fires": cells[3],
                "own_test_without_target": cells[4],
                "class": cells[5],
            })
    counts = None
    m = re.search(r"^Counts: A (\d+), B (\d+), C (\d+), D (\d+)\.", text, re.M)
    if m:
        counts = dict(zip(CLASSES, (int(x) for x in m.groups())))
    return rows, counts


# -- per subject --------------------------------------------------------------------

class Sentinels:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def check(self, subject: str, name: str, expected, found) -> None:
        holds = expected == found

        def shown(v):
            # A sentinel that holds keeps a large value only as its size.
            if holds and isinstance(v, (list, dict)) and len(json.dumps(v)) > 300:
                return f"{len(v)} items, equal"
            return v
        self.items.append({"subject": subject, "sentinel": name, "expected": shown(expected),
                           "found": shown(found), "holds": holds})

    def failed(self) -> list[dict]:
        return [s for s in self.items if not s["holds"]]


def key_of(row: dict) -> tuple[str, int, str]:
    return (row["block"], int(row["index"]), row["test_node"])


def recount_subject(name: str, source: Path, work: Path, sent: Sentinels) -> dict:
    g = source / "generated" / name
    subj_dir = source / "subjects" / name
    cases = read_csv(g / "cases.csv")
    checks = {r["check"]: r for r in read_csv(g / "checks.csv")}
    deletions = {r["check"]: r for r in read_csv(g / "deletions.csv")}
    flags_csv = read_csv(g / "flags.csv")
    pinning = read_csv(g / "pinning.csv")
    summary = read_json(g / "summary.json")
    sc = summary["counts"]
    targets_doc = read_json(subj_dir / "targets.json")
    blocks_doc = read_json(subj_dir / "blocks.json")
    checks_doc = read_json(subj_dir / "checks.json")
    base1 = read_json(extract_records(g / "records.tar.xz", work / name))

    targets = {b["key"]: b for b in targets_doc["blocks"]}
    blocks = {b["key"]: b for b in blocks_doc["blocks"]}

    # Value domains of the columns read.
    sent.check(name, "deletions.csv: every oracle column holds yes or no", [],
               [(d["check"], o) for d in deletions.values() for o in ORACLES
                if d[COLUMN.get(o, o)] not in ("yes", "no")])
    sent.check(name, "cases.csv: no row repeats its key (block, index, test)", len(cases),
               len({key_of(r) for r in cases}))

    # Cases of the study, from the first baseline record.
    study = [c for c in base1["cases"]
             if c["included"] and c.get("raised") and c.get("rejection")
             and c["check_result"] == "accepted"]
    rec = {(c["block"], c["index"], c["test"]): c for c in study}
    sent.check(name, "cases.csv rows are the cases of the study in records/base-1.json",
               sorted(rec), sorted(key_of(r) for r in cases))

    def site_check(row: dict) -> str | None:
        return row["baseline_site"] if row["baseline_site"] in checks else None

    # Raise sites agree between cases.csv and the record.
    disagree = []
    for r in cases:
        c = rec.get(key_of(r))
        if c is None:
            continue
        s = c["site"]
        if s["kind"] == "check":
            if r["baseline_site"] != s["check"]:
                disagree.append(key_of(r))
        elif site_check(r) is not None:
            disagree.append(key_of(r))
    sent.check(name, "raise site of every case agrees between cases.csv and records/base-1.json",
               [], disagree)

    # Targets agree with targets.json.
    tdis = [key_of(r) for r in cases
            if (targets.get(r["block"], {}).get("target") or "") != r["target"]
            or (targets.get(r["block"], {}).get("tier") or "") != r["tier"]]
    sent.check(name, "target and tier of every case agree with targets.json", [], tdis)

    with_target = [r for r in cases if r["target"]]
    decided = [r for r in with_target if r["baseline_site"] == r["target"]]
    flags = [r for r in with_target if r["baseline_site"] != r["target"]]
    deciding = sorted({r["baseline_site"] for r in cases if site_check(r)})
    cases_decided_by = Counter(r["baseline_site"] for r in cases if site_check(r))

    sent.check(name, "flags.csv rows are the cases with a target that the target does not decide",
               sorted((r["block"], int(r["index"])) for r in flags),
               sorted((r["block"], int(r["index"])) for r in flags_csv))
    sent.check(name, "checks.csv decides=yes are the deciding checks",
               deciding, sorted(c for c, r in checks.items() if r["decides"] == "yes"))
    sent.check(name, "checks.csv cases_decided agrees with cases.csv",
               {c: cases_decided_by.get(c, 0) for c in checks},
               {c: int(r["cases_decided"]) for c, r in checks.items()})

    # Deleted checks: the checks of the subject files that fire in at least 1 case.
    fired = set()
    for c in study:
        fired.update(c.get("fired") or [])
    subject_firing = sorted(c for c in fired if checks.get(c, {}).get("role") == "subject")
    sent.check(name, "deletions.csv rows are the subject-file checks that fire in a case (records/base-1.json)",
               subject_firing, sorted(deletions))

    def not_detected(ids) -> dict:
        rows = [deletions[c] for c in ids if c in deletions]
        return {o: sum(1 for d in rows if d[COLUMN.get(o, o)] == "no") for o in ORACLES}

    deleted_deciding = [c for c in deciding if c in deletions]
    nd_deciding = not_detected(deleted_deciding)

    # --- sentinels against summary.json
    reproduced = {
        "cases": len(cases),
        "cases_with_target": len(with_target),
        "cases_decided_by_target": len(decided),
        "flags": len(flags),
        "checks_deciding": len(deciding),
        "not_detected": {o: nd_deciding[o] for o in SENTINEL_ORACLES},
    }
    deposited = {
        "cases": sc["cases"],
        "cases_with_target": sc["cases_with_target"],
        "cases_decided_by_target": sc["cases_with_target_by_outcome"].get("decided by the target", 0),
        "flags": sc["flags"],
        "checks_deciding": sc["checks_deciding"],
        "not_detected": {o: sc["deletions_not_detected_of_deciding_checks"][o] for o in SENTINEL_ORACLES},
    }
    for k in ["cases", "cases_with_target", "cases_decided_by_target", "flags", "checks_deciding"]:
        sent.check(name, f"summary.json: {k}", deposited[k], reproduced[k])
    for o in SENTINEL_ORACLES:
        sent.check(name, f"summary.json: deletions of deciding checks not detected by {o}",
                   deposited["not_detected"][o], reproduced["not_detected"][o])
    sent.check(name, "summary.json: deletions of deciding checks",
               sc["deletions_of_deciding_checks"], len(deleted_deciding))

    # --- 1. O_T against its own denominator
    targeted_deciding = sorted({r["target"] for r in decided})
    targets_of_cases = {r["target"] for r in with_target}
    target_of_none = sorted(c for c in deciding if c not in targets_of_cases)
    target_only_undecided = sorted(c for c in deciding
                                   if c in targets_of_cases and c not in targeted_deciding)

    def group(ids) -> dict:
        deleted = [c for c in ids if c in deletions]
        return {"checks": len(ids), "deleted": len(deleted),
                "not_detected": not_detected(deleted), "list": ids}

    item1 = {
        "deciding_checks": len(deciding),
        "deciding_checks_deleted": len(deleted_deciding),
        "deletions_of_deciding_checks_not_detected": nd_deciding,
        "targeted_deciding": group(targeted_deciding),
        "target_of_no_case": group(target_of_none),
        "target_only_of_cases_not_decided": group(target_only_undecided),
        "cases_decided_by_their_target": len(decided),
    }
    sent.check(name, "item 1: the 3 groups partition the deciding checks", len(deciding),
               len(targeted_deciding) + len(target_of_none) + len(target_only_undecided))
    sent.check(name, "summary.json: reached_targets", sc["reached_targets"], len(targeted_deciding))
    sent.check(name, "summary.json: reached_targets_deletion_not_detected_O_T",
               sc["reached_targets_deletion_not_detected_O_T"],
               item1["targeted_deciding"]["not_detected"]["O_T"])

    # --- 2. Checks that fire and never decide
    fnd = sorted(c for c in deletions if c not in deciding)
    nd_fnd = not_detected(fnd)
    item2 = {"checks": len([c for c in fired if c in checks and c not in deciding]),
             "deleted": len(fnd), "not_detected": nd_fnd, "list": fnd}
    sent.check(name, "summary.json: checks_firing_and_never_deciding",
               sc["checks_firing_and_never_deciding"], item2["checks"])
    sent.check(name, "summary.json: deletions_of_checks_that_fire_and_never_decide",
               sc["deletions_of_checks_that_fire_and_never_decide"], len(fnd))
    for o in ORACLES:
        sent.check(name, f"summary.json: not detected by {o}, all deletions = deciding + fire-and-never-decide",
                   sc["deletions_not_detected"][o], nd_deciding[o] + nd_fnd[o])

    # --- 3. Cases decided by a statement that is not a check
    other_raises = {(o["file"], o["line"]): o for o in checks_doc.get("other_raises", [])}
    nonchk = []
    for r in cases:
        if site_check(r):
            continue
        c = rec[key_of(r)]
        s = c.get("site") or {}
        o = other_raises.get((s.get("file"), s.get("line")))
        nonchk.append({
            "test_node": r["test_node"], "block": r["block"], "index": int(r["index"]),
            "site_kind": s.get("kind"), "file": s.get("file"), "line": s.get("line"),
            "statement": s.get("source"), "listed_reason": o["reason"] if o else None,
            "listed_class": o["class_resolved"] if o else None,
            "listed_guard": o["guard"] if o else None,
            "class": c["class"], "target": r["target"] or None,
            "asserts": r["asserts"],
        })
    by_kind = Counter(x["site_kind"] for x in nonchk)
    sent.check(name, "summary.json: cases_by_site_kind",
               sc["cases_by_site_kind"], dict(Counter({"check": len(cases) - len(nonchk)}) + by_kind))
    pc = sc["pinning"]
    item3 = {
        "count": len(nonchk), "by_site_kind": dict(by_kind), "cases": nonchk,
        "pinning_denominators": {
            "cases_of_the_study": len(cases),
            "not_counted_no_deciding_check": len(nonchk),
            "not_counted_deciding_check_not_deleted": sum(
                1 for r in cases if site_check(r) and r["baseline_site"] not in deletions),
            "pinning_rows": len(pinning),
            "summary_pinning_cases": pc["cases"],
            "class_only_cases_of_the_study": sum(1 for r in cases if r["asserts"] == "class only"),
            "class_only_cases_without_deciding_check": sum(1 for x in nonchk if x["asserts"] == "class only"),
            "class_only_pinning_cases": pc["class_only"]["cases"],
        },
    }
    sent.check(name, "summary.json: pinning cases not counted, no deciding check",
               pc["cases_not_counted_no_deciding_check"], len(nonchk))
    sent.check(name, "summary.json: pinning cases not counted, deciding check not deleted",
               pc["cases_not_counted_deciding_check_not_deleted"],
               item3["pinning_denominators"]["not_counted_deciding_check_not_deleted"])
    pin_keys = sorted(key_of(r) for r in cases if site_check(r) and r["baseline_site"] in deletions)
    sent.check(name, "pinning.csv rows are the cases whose deciding check was deleted",
               pin_keys, sorted(key_of(r) for r in pinning))
    sent.check(name, "summary.json: pinning cases", pc["cases"], len(pinning))
    sent.check(name, "summary.json: pinning test passes", pc["test_passes"],
               sum(1 for r in pinning if r["test_passes"] == "yes"))

    # --- 4. Flags per tier and per class
    fpath = source / "readings" / name / "FLAGS.md"
    reading = None
    md_rows: list[dict] = []
    if fpath.exists():
        md_rows, md_counts = parse_flags_md(fpath.read_text(encoding="utf-8"))
        reading = "readings/" + name + "/FLAGS.md"
    flag_class: dict = {}
    flags_csv_by_key = {}
    for r in flags_csv:
        flags_csv_by_key.setdefault((r["block"], int(r["index"])), []).append(r)
    if reading:
        unmatched_rows = []
        used = Counter()
        for m in md_rows:
            hits = [r for r in flags if r["test_node"] == m["test_node"]
                    and r["block"].endswith("#" + str(m["k"])) and int(r["index"]) == m["index"]
                    and r["block"].split("::", 1)[0] == m["block_file"]]
            if len(hits) != 1:
                unmatched_rows.append(m["label"])
                continue
            k = key_of(hits[0])
            used[k] += 1
            flag_class[k] = m
        sent.check(name, f"{reading}: every row names exactly 1 flag", [], unmatched_rows)
        sent.check(name, f"{reading}: every flag has exactly 1 row",
                   sorted(key_of(r) for r in flags), sorted(k for k, v in used.items() if v == 1))
        found_counts = dict(Counter(m["class"] for m in flag_class.values()))
        sent.check(name, f"{reading}: classes agree with its line 'Counts:'",
                   {c: v for c, v in (md_counts or {}).items() if v}, found_counts)
        mech = []
        for r in flags:
            m = flag_class.get(key_of(r))
            if m is None:
                continue
            csvrows = flags_csv_by_key.get((r["block"], int(r["index"])), [])
            tf = r["target_fired"]
            ow = r["own_test_without_target"]
            if m["target_fires"] != tf or m["own_test_without_target"] != ow:
                mech.append(m["label"])
            if not any(x["target_fired"] == tf and x["own_test_without_target"] == ow for x in csvrows):
                mech.append(m["label"] + " (flags.csv)")
        sent.check(name, f"{reading}: columns 'Target fires' and 'Own test without the target' agree with the outputs",
                   [], mech)

    tiers = {}
    for t in TIERS:
        wt = [r for r in with_target if r["tier"] == t]
        fl = [r for r in flags if r["tier"] == t]
        by_class = None
        if reading:
            by_class = {c: sum(1 for r in fl if flag_class.get(key_of(r), {}).get("class") == c)
                        for c in CLASSES}
        tiers[t] = {"cases_with_target": len(wt),
                    "decided_by_target": sum(1 for r in wt if r["baseline_site"] == r["target"]),
                    "flags": len(fl), "flags_by_class": by_class}
    sent.check(name, "summary.json: cases_with_target_by_tier",
               {t: v for t, v in sc["cases_with_target_by_tier"].items()},
               {t: v["cases_with_target"] for t, v in tiers.items() if v["cases_with_target"]})
    sent.check(name, "summary.json: flags_by_tier", dict(sc["flags_by_tier"]),
               {t: v["flags"] for t, v in tiers.items() if v["flags"]})

    pin_by_key = {key_of(r): r for r in pinning}
    flags_pass = []
    for r in flags:
        p = pin_by_key.get(key_of(r))
        if p is None or p["test_passes"] != "yes":
            continue
        flags_pass.append({
            "test_node": r["test_node"], "block": r["block"], "index": int(r["index"]),
            "reading_class": flag_class.get(key_of(r), {}).get("class"),
            "tier": r["tier"], "target": r["target"], "deciding_check": r["baseline_site"],
            "class_after_deletion": p["class"], "site_after_deletion": p["site"],
            "what_the_case_does": p["what_the_case_does"],
        })
    item4 = {"reading": reading, "tiers": tiers,
             "flags_own_test_passes_without_deciding_check": flags_pass,
             "class_C_own_test_passes_without_deciding_check":
                 [x for x in flags_pass if x["reading_class"] == "C"]}

    # --- 5. Flags and pinning passes, with the assertions of the block
    def assertions(block_key: str) -> dict:
        b = blocks.get(block_key, {})
        return {"match": b.get("match"), "match_unparsed": b.get("match_unparsed"),
                "post": b.get("post"), "post_unparsed": b.get("post_unparsed")}

    item5 = {
        "flags": [{"test_node": r["test_node"], "block": r["block"], "index": int(r["index"]),
                   "tier": r["tier"], "target": r["target"], "deciding_check": r["baseline_site"],
                   "target_fired": r["target_fired"],
                   "own_test_without_target": r["own_test_without_target"],
                   "asserts": r["asserts"], "assertions": assertions(r["block"])}
                  for r in flags],
        "pinning_passes": [{"test_node": p["test_node"], "block": p["block"], "index": int(p["index"]),
                            "deleted_check": p["deleted_check"], "asserts": p["asserts"],
                            "class_after_deletion": p["class"], "site_after_deletion": p["site"],
                            "what_the_case_does": p["what_the_case_does"],
                            "assertions": assertions(p["block"])}
                           for p in pinning if p["test_passes"] == "yes"],
    }

    # --- 6. Checks inside an except handler
    in_h = sorted(c for c, r in checks.items() if r["in_handler"] == "yes")
    in_h_dec = [c for c in in_h if c in deciding]
    item6 = {"checks": len(in_h), "deciding": len(in_h_dec),
             "cases_decided": sum(cases_decided_by[c] for c in in_h_dec),
             "deleted": sum(1 for c in in_h if c in deletions),
             "deciding_list": [{"check": c, "cases_decided": cases_decided_by[c]} for c in in_h_dec]}
    sent.check(name, "summary.json: deletions_in_handler", sc["deletions_in_handler"], item6["deleted"])
    sent.check(name, "in_handler agrees between deletions.csv and checks.csv", [],
               [c for c, d in deletions.items() if d["in_handler"] != checks[c]["in_handler"]])

    return {"reproduced": reproduced, "deposited": deposited,
            "item1_ot_denominator": item1, "item2_fire_never_decide": item2,
            "item3_non_check_sites": item3, "item4_flags": item4,
            "item5_flags_and_pinning_passes": item5, "item6_in_handler": item6}


# -- totals and report --------------------------------------------------------------

def add(a, b):
    if isinstance(a, dict):
        return {k: add(a[k], b[k]) for k in a}
    return a + b


def totals(results: dict, names: list[str]) -> dict:
    t: dict = {}
    keys = {
        "reproduced": lambda r: r["reproduced"],
        "item1": lambda r: {
            "deciding_checks": r["item1_ot_denominator"]["deciding_checks"],
            "deciding_checks_deleted": r["item1_ot_denominator"]["deciding_checks_deleted"],
            "deletions_of_deciding_checks_not_detected":
                r["item1_ot_denominator"]["deletions_of_deciding_checks_not_detected"],
            **{g: {k: v for k, v in r["item1_ot_denominator"][g].items() if k != "list"}
               for g in ("targeted_deciding", "target_of_no_case", "target_only_of_cases_not_decided")},
            "cases_decided_by_their_target": r["item1_ot_denominator"]["cases_decided_by_their_target"],
        },
        "item2": lambda r: {k: v for k, v in r["item2_fire_never_decide"].items() if k != "list"},
        "item3": lambda r: {"count": r["item3_non_check_sites"]["count"]},
        "item4": lambda r: {tt: {k: v for k, v in r["item4_flags"]["tiers"][tt].items()} for tt in TIERS},
        "item6": lambda r: {k: v for k, v in r["item6_in_handler"].items() if k != "deciding_list"},
    }
    for k, f in keys.items():
        acc = None
        for n in names:
            v = f(results[n])
            acc = v if acc is None else add(acc, v)
        t[k] = acc
    return t


def md_table(header: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join("" if x is None else str(x) for x in r) + " |")
    return out


def code(x) -> str:
    return "`" + str(x).replace("|", "\\|") + "`" if x not in (None, "") else ""


def render(results: dict, tot: dict, sent: Sentinels, subjects: list[str]) -> str:
    cols = subjects + (["held out, total"] if tot else [])
    L: list[str] = []
    L += ["# Recount from the deposited outputs of target reach", "",
          "Computed by `recount/recount.py` from the deposited files of `../target-reach` "
          "(`generated/<name>/`, `subjects/<name>/`, `readings/<name>/FLAGS.md`). No library was "
          "run. `recount/README.md` defines every count. The last column is the sum over the 4 "
          "held-out libraries (google-auth, oauthlib, authlib, joserfc).", ""]
    failed = sent.failed()
    L += [f"Sentinels: {len(sent.items)}, of which {len(sent.items) - len(failed)} hold.", ""]

    def val(n, f):
        return f(tot) if n == "held out, total" else f(results[n])

    L += ["## Reproduced deposited counts", ""]
    rows = []
    for label, f in [
        ("cases", lambda r: r["reproduced"]["cases"]),
        ("cases with a target", lambda r: r["reproduced"]["cases_with_target"]),
        ("decided by the target", lambda r: r["reproduced"]["cases_decided_by_target"]),
        ("flags", lambda r: r["reproduced"]["flags"]),
        ("deciding checks", lambda r: r["reproduced"]["checks_deciding"]),
    ] + [(f"deletions of deciding checks not detected by {o}",
          (lambda o: lambda r: r["reproduced"]["not_detected"][o])(o)) for o in SENTINEL_ORACLES]:
        rows.append([label] + [val(n, f) for n in cols])
    L += md_table([""] + cols, rows) + [""]

    # Item 1
    L += ["## 1. O_T against its own denominator", ""]
    i1 = lambda r: r["item1"] if "item1" in r else r["item1_ot_denominator"]
    rows = []
    rows.append(["deciding checks"] + [val(n, lambda r: i1(r)["deciding_checks"]) for n in cols])
    rows.append(["deciding checks deleted"] + [val(n, lambda r: i1(r)["deciding_checks_deleted"]) for n in cols])
    for o in ORACLES:
        rows.append([f"all deleted deciding checks: not detected by {o}"] +
                    [val(n, (lambda o: lambda r: i1(r)["deletions_of_deciding_checks_not_detected"][o])(o))
                     for n in cols])
    for g, label in [("targeted_deciding", "targeted deciding checks"),
                     ("target_of_no_case", "deciding checks that are the target of no case"),
                     ("target_only_of_cases_not_decided",
                      "deciding checks that are a target only of cases they do not decide")]:
        rows.append([label] + [val(n, (lambda g: lambda r: i1(r)[g]["checks"])(g)) for n in cols])
        rows.append([f"{label}: deleted"] + [val(n, (lambda g: lambda r: i1(r)[g]["deleted"])(g)) for n in cols])
        for o in ORACLES:
            rows.append([f"{label}: not detected by {o}"] +
                        [val(n, (lambda g, o: lambda r: i1(r)[g]["not_detected"][o])(g, o)) for n in cols])
    rows.append(["cases decided by their target (O_T holds at baseline)"] +
                [val(n, lambda r: i1(r)["cases_decided_by_their_target"]) for n in cols])
    L += md_table([""] + cols, rows) + [""]

    # Item 2
    L += ["## 2. Checks that fire and never decide", ""]
    i2 = lambda r: r["item2"] if "item2" in r else r["item2_fire_never_decide"]
    rows = [["checks that fire and never decide"] + [val(n, lambda r: i2(r)["checks"]) for n in cols],
            ["deleted"] + [val(n, lambda r: i2(r)["deleted"]) for n in cols]]
    for o in ORACLES:
        rows.append([f"not detected by {o}"] + [val(n, (lambda o: lambda r: i2(r)["not_detected"][o])(o))
                                                for n in cols])
    L += md_table([""] + cols, rows) + [""]
    for n in subjects:
        lst = results[n]["item2_fire_never_decide"]["list"]
        if lst:
            L += [f"{n}: " + ", ".join(code(c) for c in lst), ""]

    # Item 3
    L += ["## 3. Cases decided by a statement that is not a check", ""]
    L += md_table([""] + cols, [["cases"] + [val(n, lambda r: (r["item3"] if "item3" in r else
                                                                 r["item3_non_check_sites"])["count"])
                                              for n in cols]]) + [""]
    for n in subjects:
        i3 = results[n]["item3_non_check_sites"]
        if not i3["cases"]:
            continue
        L += [f"### {n}", ""]
        L += md_table(["case", "index", "file", "line", "statement", "kind", "class label in checks.json",
                       "reason in checks.json", "guard in checks.json"],
                      [[code(x["block"]), x["index"], code(x["file"]), x["line"], code(x["statement"]),
                        x["site_kind"], code(x["listed_class"]), x["listed_reason"], code(x["listed_guard"])]
                       for x in i3["cases"]]) + [""]
        p = i3["pinning_denominators"]
        L += [f"The pinning table of {n} has 2 denominators. The {p['cases_of_the_study']} cases of the "
              f"study include {p['not_counted_no_deciding_check']} whose raise site is no check (the rows "
              f"above); pinning deletes the deciding check of a case, so these "
              f"{p['not_counted_no_deciding_check']} have nothing to delete and are not counted, and "
              f"{p['not_counted_deciding_check_not_deleted']} cases have a deciding check that was not "
              f"deleted. That leaves {p['pinning_rows']} counted cases ({p['summary_pinning_cases']} in "
              f"summary.json). Among the class-only cases the same difference holds: "
              f"{p['class_only_cases_of_the_study']} class-only cases of the study, "
              f"{p['class_only_cases_without_deciding_check']} of them without a deciding check, "
              f"{p['class_only_pinning_cases']} class-only cases in the pinning table.", ""]

    # Item 4
    L += ["## 4. Flags per tier and per class", "",
          "The classes are a reading of the sources (`readings/<name>/FLAGS.md`) and are reported "
          "apart from the mechanical counts. PyJWT has no reading of its flag.", ""]
    rows = []
    for t in TIERS:
        for label, f in [("cases with a target", "cases_with_target"), ("decided by the target", "decided_by_target"),
                         ("flags", "flags")]:
            rows.append([f"{t} tier: {label}"] + [val(n, (lambda t, f: lambda r: (r["item4"] if "item4" in r
                                                                                  else r["item4_flags"]["tiers"])[t][f])(t, f))
                                                 for n in cols])
        for c in CLASSES:
            def g(r, t=t, c=c):
                tiers = r["item4"] if "item4" in r else r["item4_flags"]["tiers"]
                bc = tiers[t].get("flags_by_class")
                return None if bc is None else bc[c]
            rows.append([f"{t} tier: flags of class {c}"] +
                        [("not read" if v is None else v) for v in
                         [g(tot) if n == "held out, total" else g(results[n]) for n in cols]])
    L += md_table([""] + cols, rows) + [""]
    L += ["### Flags whose own test still passes on the copy without the deciding check", ""]
    any_rows = []
    for n in subjects:
        for x in results[n]["item4_flags"]["flags_own_test_passes_without_deciding_check"]:
            any_rows.append([n, code(x["block"]), x["index"], x["reading_class"] or "not read",
                             code(x["deciding_check"]), code(x["class_after_deletion"]),
                             code(x["site_after_deletion"]), x["what_the_case_does"]])
    if any_rows:
        L += md_table(["subject", "case", "index", "class (reading)", "deleted deciding check",
                       "class raised then", "site then", "what the case does"], any_rows) + [""]
    else:
        L += ["None.", ""]

    # Item 5
    L += ["## 5. PyJWT: the flag and the pinning passes", ""]
    for n in [x for x in PYJWT if x in results]:
        i5 = results[n]["item5_flags_and_pinning_passes"]
        L += [f"### {n}", ""]
        L += md_table(["case", "test", "target", "deciding check", "target fires", "own test without the target",
                       "block asserts", "pattern", "assertions after the block"],
                      [[code(x["block"]), code(x["test_node"]), code(x["target"]), code(x["deciding_check"]),
                        x["target_fired"], x["own_test_without_target"], x["asserts"],
                        code(x["assertions"]["match"]), code(x["assertions"]["post"])] for x in i5["flags"]]) + [""]
        L += md_table(["case whose own test passes without its deciding check", "deleted check", "block asserts",
                       "pattern", "assertions after the block", "class raised then", "site then"],
                      [[code(x["block"]), code(x["deleted_check"]), x["asserts"], code(x["assertions"]["match"]),
                        code(x["assertions"]["post"]), code(x["class_after_deletion"]),
                        code(x["site_after_deletion"])] for x in i5["pinning_passes"]]) + [""]

    # Item 6
    L += ["## 6. Checks inside an except handler", ""]
    i6 = lambda r: r["item6"] if "item6" in r else r["item6_in_handler"]
    rows = [[lab] + [val(n, (lambda k: lambda r: i6(r)[k])(k)) for n in cols]
            for lab, k in [("checks in a handler", "checks"), ("of them deciding", "deciding"),
                           ("cases they decide", "cases_decided"), ("of them deleted", "deleted")]]
    L += md_table([""] + cols, rows) + [""]

    L += ["## Sentinels", ""]
    if failed:
        L += md_table(["subject", "sentinel", "expected", "found"],
                      [[s["subject"], s["sentinel"], code(json.dumps(s["expected"]))[:300],
                        code(json.dumps(s["found"]))[:300]] for s in failed]) + [""]
    else:
        L += [f"All {len(sent.items)} sentinels hold. Per subject they cover: the counts of summary.json "
              "reproduced from the CSV files; the CSV files against the first baseline record, targets.json "
              "and each other; and the reading FLAGS.md against the flags. The totals over the 4 held-out "
              "libraries equal the fixed values 402, 229, 145, 84, 137 and 24, 57, 6, 82, 5.", ""]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    exp = here.parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", type=Path, default=exp.parent / "target-reach")
    ap.add_argument("--work", type=Path, default=exp / "work" / "recount" / "records")
    ap.add_argument("--out", type=Path, default=exp / "generated" / "recount")
    ap.add_argument("--subjects", nargs="*", default=SUBJECTS)
    ap.add_argument("--held-out", nargs="*", default=HELD_OUT)
    ap.add_argument("--held-out-totals", type=Path, default=None,
                    help="JSON file with the totals to reproduce (default: the fixed values)")
    a = ap.parse_args(argv)

    sent = Sentinels()
    results = {n: recount_subject(n, a.source, a.work, sent) for n in a.subjects}
    held = [n for n in a.held_out if n in results]
    tot = totals(results, held) if held else {}
    expected_totals = read_json(a.held_out_totals) if a.held_out_totals else HELD_OUT_TOTALS
    if held:
        sent.check("held out, total", "totals over the held-out libraries", expected_totals, tot["reproduced"])

    a.out.mkdir(parents=True, exist_ok=True)
    doc = {"subjects": results, "held_out": held, "held_out_totals": tot,
           "sentinels": sent.items, "sentinels_failed": len(sent.failed())}
    (a.out / "recount.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (a.out / "RECOUNT.md").write_text(render(results, tot, sent, list(a.subjects)), encoding="utf-8")
    failed = sent.failed()
    for s in failed:
        print(f"sentinel does not hold: {s['subject']}: {s['sentinel']}", file=sys.stderr)
    print(f"{len(sent.items)} sentinels, {len(failed)} do not hold")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

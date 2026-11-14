"""Compare target labels assigned by reading with the runs and with the rule.

    python3 -I -B labels/analyse_labels.py --subject ../target-reach/subjects/<name>/subject.json \
        --labels <reading 1.tsv> [<reading 2.tsv>] [--targets3 <targets.json of rule 3>] \
        [--generated ../target-reach/generated/<name>] [--first labels/first/<name>.tsv] \
        [--out generated/labels/<name>]

Inputs: the definitions of the subject next to subject.json (blocks.json,
checks.json, targets.json), 1 or 2 labels files, and the deposited outputs
of the toolkit for the subject: cases.csv, deletions.csv, pinning.csv,
flags.csv, SHA256SUMS and the records in records.tar.xz, which are read from
the archive without unpacking it. With 1 labels file, its labels are the
agreed labels.

Outputs (in --out, default generated/labels/<name>/ of the experiment):

- agreement.csv: 1 row per included block, the 2 labels and the category:
  same check; both none; 1 check and 1 none; 2 different checks (with 1
  file: single). With 2 files, counts.json also gives the observed
  agreement and Cohen's kappa over the included blocks, 2 times: with each
  distinct label text as a category, and with the 2 categories "a check is
  named" and "none" (KAPPA below).
- outcomes.csv: 1 row per case of the study whose block has an agreed label
  that names a check, with the mechanical outcome (OUTCOMES below).
- rule-vs-label.csv: 1 row per case of the study and rule: the program's
  target, its tier, the agreed label and the category (CATEGORIES below).
  Rule 2 is the target of cases.csv; rule 3, when --targets3 is given, the
  target of its block in that file.
- rule-vs-label-blocks.csv: the same per included block.
- first-reading.csv: when a transcription of the first reading of the flags
  exists (--first, default labels/first/<name>.tsv), 1 row per flag: the
  check the first reading names as described, beside the labels.
- counts.json and COUNTS.md: every count and the sentinels.

The program writes every output and then exits with status 1 when a
sentinel does not hold (SENTINELS below).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tarfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOLLOWUP = HERE.parent
EXPERIMENTS = FOLLOWUP.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from labelslib import (NONE, Universe, csv_text, label_text, load_json, param_value_of,  # noqa: E402
                       read_csv, read_tsv, sha256_file, validate_labels)

OUTCOMES = [
    "decided by its label",
    "label fires and another check decides",
    "label fires and no check decides",
    "label does not fire and decides once the deciding check is deleted",
    "label does not fire and does not decide then either",
    "label does not fire; case not observed on the copy without the deciding check",
    "label does not fire and no check decides",
    "deciding check not deleted or record missing",
    "fired checks not recorded",
]
AGREEMENT = ["same check", "both none", "1 check and 1 none", "2 different checks"]
CATEGORIES = ["target equals label", "target differs from label", "target and label none",
              "label none", "no target", "no agreed label"]
BLOCK_CELLS = ["both, equal", "both, different", "rule only", "label only", "neither", "no agreed label"]
TIERS = ["assertion", "name", "none"]

SENTINELS = {
    1: "the deposited files of generated/<name>/ match SHA256SUMS",
    2: "cases.csv holds exactly the cases of the study of the first baseline record, with the same "
       "raise site and fired checks",
    3: "the target of each row of cases.csv is the target of its block in targets.json",
    4: "every labels file is valid: each included block exactly once, labels are check ids or none, "
       "bases are valid",
    5: "every by-param label resolves to exactly 1 value in every case of its block",
    6: "the agreement categories add up to the included blocks, the outcomes to the cases with an "
       "agreed label that names a check, and the rule categories to the cases of the study, for each "
       "rule and in each tier",
    7: "every case decided by its label has its label among its fired checks",
    8: "the deletion runs read here are those of deletions.csv, and for every case whose deciding "
       "check was deleted and gave a record, the status and raise site read from the records equal "
       "those of pinning.csv",
    9: "the transcription of the first reading matches flags.csv: the same cases, targets and "
       "deciding checks, in the same order",
}


def load_toolkit(path: Path):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    from reach.analyse import Run, site_label  # noqa: E402
    from reach.study import case_key, firing, study_cases  # noqa: E402
    return Run, site_label, case_key, firing, study_cases


def read_archive(path: Path) -> dict[str, dict]:
    out = {}
    with tarfile.open(path, "r:xz") as tar:
        for m in tar.getmembers():
            if m.isfile() and m.name.endswith(".json"):
                out[m.name] = json.loads(tar.extractfile(m).read().decode("utf-8"))
    return out


def check_sums(gen: Path) -> list[str]:
    problems = []
    sums = gen / "SHA256SUMS"
    if not sums.is_file():
        return ["SHA256SUMS is missing"]
    for line in sums.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        p = gen / name
        if not p.is_file():
            problems.append(f"{name}: listed and missing")
        elif sha256_file(p) != digest:
            problems.append(f"{name}: digest differs")
    for name in ("cases.csv", "deletions.csv", "pinning.csv", "flags.csv", "records.tar.xz"):
        if name not in sums.read_text(encoding="utf-8"):
            problems.append(f"{name}: not listed in SHA256SUMS")
    return problems


def resolve(label: tuple | None, test_node: str) -> tuple[str, str | None]:
    """('none' | 'check' | 'unresolved' | 'no label', check id or None) for 1 case."""
    if label is None:
        return "no label", None
    if label[0] == NONE:
        return NONE, None
    if label[0] == "check":
        return "check", label[1]
    cid, found = param_value_of(label, test_node)
    if len(found) != 1:
        return "unresolved", None
    return ("check", cid) if cid else (NONE, None)


def kappa(pairs: list[tuple[str, str]]) -> dict:
    """KAPPA: observed agreement and Cohen's kappa of 2 readings over the same items.

    `pairs` holds 1 pair of category names per item. The observed agreement
    p_o is the share of pairs whose 2 names are equal. The agreement expected
    by chance p_e is the sum, over the categories, of the product of the 2
    shares with which the readings use the category. kappa = (p_o - p_e) /
    (1 - p_e); it is not defined (None) when there is no item or p_e is 1.
    The fractions are exact; the values are rounded to 4 decimals.
    """
    from fractions import Fraction
    n = len(pairs)
    if n == 0:
        return {"items": 0, "categories": 0, "equal": 0, "observed": None, "expected": None,
                "kappa": None}
    first = Counter(a for a, _ in pairs)
    second = Counter(b for _, b in pairs)
    equal = sum(1 for a, b in pairs if a == b)
    p_o = Fraction(equal, n)
    p_e = sum(Fraction(first[k] * second[k], n * n) for k in set(first) | set(second))
    value = None if p_e == 1 else (p_o - p_e) / (1 - p_e)
    return {"items": n, "categories": len(set(first) | set(second)), "equal": equal,
            "observed": round(float(p_o), 4), "expected": round(float(p_e), 4),
            "kappa": None if value is None else round(float(value), 4)}


def agreement_category(a: tuple, b: tuple) -> str:
    if label_text(a) == label_text(b):
        return "both none" if a[0] == NONE else "same check"
    if a[0] == NONE or b[0] == NONE:
        return "1 check and 1 none"
    return "2 different checks"


def rule_category(target: str | None, kind: str, label: str | None) -> str:
    if kind in ("no label", "unresolved"):
        return "no agreed label"
    if target and kind == "check":
        return "target equals label" if target == label else "target differs from label"
    if target:
        return "label none"
    return "no target" if kind == "check" else "target and label none"


def block_cell(target: str | None, label: tuple | None) -> str:
    if label is None:
        return "no agreed label"
    if label[0] == NONE:
        values = set()
        has_none = True
    elif label[0] == "check":
        values, has_none = {label[1]}, False
    else:
        values = {c for _, c in label[2] if c}
        has_none = any(c is None for _, c in label[2])
    if target and values:
        return "both, equal" if values == {target} and not has_none else "both, different"
    if target:
        return "rule only"
    return "label only" if values else "neither"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", required=True, type=Path)
    ap.add_argument("--labels", required=True, nargs="+", type=Path)
    ap.add_argument("--targets3", type=Path)
    ap.add_argument("--generated", type=Path)
    ap.add_argument("--first", type=Path)
    ap.add_argument("--toolkit", type=Path, default=EXPERIMENTS / "target-reach")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    if len(a.labels) > 2:
        raise SystemExit("analyse_labels: 1 or 2 labels files")

    Run, site_label, case_key, firing, study_cases = load_toolkit(a.toolkit.resolve())
    subject_path = a.subject.resolve()
    defs = subject_path.parent
    subject = load_json(subject_path)
    name = subject["name"]
    gen = (a.generated or a.toolkit / "generated" / name).resolve()
    out = (a.out or FOLLOWUP / "generated" / "labels" / name).resolve()
    first_path = a.first if a.first else HERE / "first" / f"{name}.tsv"

    checks_doc = load_json(defs / "checks.json")
    blocks_doc = load_json(defs / "blocks.json")
    targets_doc = load_json(defs / "targets.json")
    targets2 = {t["key"]: t for t in targets_doc["blocks"]}
    targets3 = {t["key"]: t for t in load_json(a.targets3)["blocks"]} if a.targets3 else None
    included = sorted(b["key"] for b in blocks_doc["blocks"] if b["included"])
    uni = Universe.from_defs(checks_doc, blocks_doc)

    sentinels: dict[int, list[str]] = {k: [] for k in SENTINELS}
    counts: dict = {"subject": name, "labels_files": [p.name for p in a.labels],
                    "rule_3": a.targets3.name if a.targets3 else None}

    # -- the deposited outputs --------------------------------------------------------
    sentinels[1] += check_sums(gen)
    cases_rows = read_csv(gen / "cases.csv")
    deletions_rows = read_csv(gen / "deletions.csv")
    pinning_rows = read_csv(gen / "pinning.csv")
    flags_rows = read_csv(gen / "flags.csv")
    archive = read_archive(gen / "records.tar.xz")
    base = Run(archive["records/base-1.json"])
    fired_recorded = bool(archive["records/base-1.json"].get("fired_recorded"))
    study = study_cases(archive["records/base-1.json"])
    manifest = archive.get("records/deletions/manifest.json", {})
    runs = {}
    for cid, m in manifest.items():
        rec = archive.get(f"records/deletions/{m['dir']}.json")
        runs[cid] = Run(rec) if rec is not None else None

    def key_of(row: dict) -> str:
        return f"{row['test_node']}|{row['block']}|{row['index']}"

    case_by_key = {}
    for r in cases_rows:
        k = key_of(r)
        if k in case_by_key:
            sentinels[2].append(f"cases.csv names {k} twice")
        case_by_key[k] = r
    if set(case_by_key) != set(study):
        sentinels[2].append(f"cases.csv and the record differ: {len(set(case_by_key) - set(study))} "
                            f"only in cases.csv, {len(set(study) - set(case_by_key))} only in the record")
    for k, r in case_by_key.items():
        c = study.get(k)
        if c is None:
            continue
        if r["baseline_site"] != site_label(c):
            sentinels[2].append(f"{k}: raise site {r['baseline_site']!r} in cases.csv, "
                                f"{site_label(c)!r} in the record")
        if r["fired"] != "; ".join(c.get("fired") or []):
            sentinels[2].append(f"{k}: fired checks differ between cases.csv and the record")
        t = targets2.get(r["block"], {})
        if (r["target"] or None) != t.get("target") or (r["tier"] or None) != t.get("tier"):
            sentinels[3].append(f"{k}: target {r['target']!r} ({r['tier']}) in cases.csv, "
                                f"{t.get('target')!r} ({t.get('tier')}) in targets.json")
    keys = sorted(case_by_key)
    deletions_checks = {r["check"] for r in deletions_rows}
    if deletions_checks != set(manifest):
        sentinels[8].append(f"deletions.csv names {len(deletions_checks)} checks, the manifest of the "
                            f"records {len(manifest)}; differing: "
                            f"{sorted(deletions_checks ^ set(manifest))}")

    # -- the labels files -------------------------------------------------------------
    parsed = []
    for p in a.labels:
        header, rows = read_tsv(p)
        res = validate_labels(header, rows, uni)
        sentinels[4] += [f"{p.name}: {e}" for e in res["errors"]]
        parsed.append(res)
        counts.setdefault("labels", {})[p.name] = {
            "blocks_labeled": len(res["labels"]),
            "label_none": sum(1 for v in res["labels"].values() if v[0] == NONE),
            "label_check": sum(1 for v in res["labels"].values() if v[0] == "check"),
            "label_by_param": sum(1 for v in res["labels"].values() if v[0] == "param"),
            "by_basis": dict(sorted(Counter("+".join(v) for v in res["bases"].values()).items())),
            "warnings": len(res["warnings"]),
            "class_outside": res["class_outside"],
        }

    # -- agreement --------------------------------------------------------------------
    agreed: dict[str, tuple | None] = {}
    agreement_rows = []
    agreement = Counter()
    label_pairs: list[tuple[str, str]] = []
    for key in included:
        ls = [res["labels"].get(key) for res in parsed]
        if len(parsed) == 1:
            agreed[key] = ls[0]
            agreement_rows.append([key, label_text(ls[0]) if ls[0] else "", "", "single"])
            agreement["single"] += 1
            continue
        if ls[0] is None or ls[1] is None:
            cat = "label missing"
            agreed[key] = None
        else:
            cat = agreement_category(ls[0], ls[1])
            agreed[key] = ls[0] if cat in ("same check", "both none") else None
        agreement[cat] += 1
        agreement_rows.append([key] + [label_text(x) if x else "" for x in ls] + [cat])
        if ls[0] is not None and ls[1] is not None:
            label_pairs.append((label_text(ls[0]), label_text(ls[1])))
    counts["agreement"] = {c: agreement.get(c, 0) for c in (AGREEMENT if len(parsed) == 2 else ["single"])}
    if agreement.get("label missing"):
        counts["agreement"]["label missing"] = agreement["label missing"]
    if len(parsed) == 2:
        counts["agreement_statistics"] = {
            "labels": kappa(label_pairs),
            "check_or_none": kappa([(NONE if a == NONE else "check", NONE if b == NONE else "check")
                                    for a, b in label_pairs])}
        if counts["agreement_statistics"]["labels"]["equal"] != \
                agreement.get("same check", 0) + agreement.get("both none", 0):
            sentinels[6].append("agreement: the equal pairs of the statistics differ from the categories "
                                "same check and both none")
    if sum(agreement.values()) != len(included):
        sentinels[6].append(f"agreement: {sum(agreement.values())} blocks counted, {len(included)} included")

    # -- per case: the agreed label resolved ------------------------------------------
    case_label: dict[str, tuple[str, str | None]] = {}
    for k in keys:
        r = case_by_key[k]
        kind, cid = resolve(agreed.get(r["block"]), r["test_node"])
        if kind == "unresolved":
            sentinels[5].append(f"{k}: the by-param label of its block matches no single value of "
                                f"{r['test_node']}")
        case_label[k] = (kind, cid)

    # -- mechanical outcome per case with a label that names a check ------------------
    outcome_rows = []
    outcomes = Counter()
    pin_index = {}
    for p in pinning_rows:
        pin_index.setdefault((p["test_node"], p["block"], p["index"], p["deleted_check"]), p)
    pin_checked = 0
    for k in keys:
        c = study[k] if k in study else None
        if c is None:
            continue
        r = case_by_key[k]
        site = (c.get("site") or {}).get("check")
        # the deletion run of the deciding check, read for every case (sentinel 8)
        st = obs_site = obs = None
        label_fires_after = ""
        if site and site in runs and runs[site] is not None:
            run = runs[site]
            st = run.status(k, c["test"])
            obs = run.cases.get(k)
            obs_site = site_label(obs) if obs else ""
            p = pin_index.get((r["test_node"], r["block"], r["index"], site))
            if p is None:
                sentinels[8].append(f"{k}: no row of pinning.csv for the deletion of {site}")
            else:
                pin_checked += 1
                if p["status"] != st or p["site"] != obs_site:
                    sentinels[8].append(f"{k}: pinning.csv gives {p['status']}/{p['site']!r}, the "
                                        f"records {st}/{obs_site!r}")
        kind, label = case_label[k]
        if kind != "check":
            continue
        fired = firing(c)
        label_fired = label in fired
        if obs is not None and st == "observed":
            label_fires_after = "yes" if label in firing(obs) else "no"
        if site == label:
            outcome = "decided by its label"
            if fired_recorded and label not in (c.get("fired") or []):
                sentinels[7].append(f"{k}: decided by its label {label}, which is not among its fired checks")
        elif not fired_recorded:
            outcome = "fired checks not recorded"
        elif label_fired:
            outcome = ("label fires and another check decides" if site
                       else "label fires and no check decides")
        elif site is None:
            outcome = "label does not fire and no check decides"
        elif site not in runs or runs[site] is None:
            outcome = "deciding check not deleted or record missing"
        elif st != "observed":
            outcome = "label does not fire; case not observed on the copy without the deciding check"
        elif obs_site == label:
            outcome = "label does not fire and decides once the deciding check is deleted"
        else:
            outcome = "label does not fire and does not decide then either"
        outcomes[outcome] += 1
        outcome_rows.append([r["block"], r["index"], r["test_node"], label, site_label(c),
                             "yes" if label_fired else "no", outcome, st or "", obs_site or "",
                             label_fires_after])
    with_label = sum(1 for k in keys if case_label[k][0] == "check")
    counts["cases"] = len(keys)
    counts["cases_with_agreed_label_check"] = with_label
    counts["cases_with_agreed_label_none"] = sum(1 for k in keys if case_label[k][0] == NONE)
    counts["cases_without_agreed_label"] = sum(1 for k in keys if case_label[k][0] in ("no label", "unresolved"))
    counts["outcomes"] = {o: outcomes.get(o, 0) for o in OUTCOMES}
    counts["pinning_rows_compared"] = pin_checked
    if sum(outcomes.values()) != with_label:
        sentinels[6].append(f"outcomes: {sum(outcomes.values())} counted, {with_label} cases with a label")

    # -- rule against label ------------------------------------------------------------
    rule_rows, block_rows = [], []
    counts["rule_vs_label"] = {}
    counts["rule_vs_label_blocks"] = {}
    rules = [("rule 2", lambda b: targets2.get(b, {}))]
    if targets3 is not None:
        rules.append(("rule 3", lambda b: targets3.get(b, {})))
    for rule, get in rules:
        per_tier = {t: Counter() for t in TIERS}
        for k in keys:
            r = case_by_key[k]
            if rule == "rule 2":
                target, tier = r["target"] or None, r["tier"] or None
            else:
                t = get(r["block"])
                target, tier = t.get("target"), t.get("tier")
            tier = tier if target else "none"
            kind, label = case_label[k]
            cat = rule_category(target, kind, label)
            per_tier.setdefault(tier, Counter())[cat] += 1
            rule_rows.append([rule, r["block"], r["index"], r["test_node"], target or "", tier,
                              label if kind == "check" else ("none" if kind == NONE else ""), cat])
        total = Counter()
        for c in per_tier.values():
            total.update(c)
        counts["rule_vs_label"][rule] = {
            "all": {c: total.get(c, 0) for c in CATEGORIES},
            "by_tier": {t: {c: per_tier[t].get(c, 0) for c in CATEGORIES} for t in per_tier}}
        if sum(total.values()) != len(keys):
            sentinels[6].append(f"{rule}: {sum(total.values())} cases counted, {len(keys)} cases")
        if sum(sum(c.values()) for c in per_tier.values()) != sum(total.values()):
            sentinels[6].append(f"{rule}: the tiers do not add up")
        cells = Counter()
        by_basis: dict[str, Counter] = {}
        for key in included:
            t = get(key)
            cell = block_cell(t.get("target"), agreed.get(key))
            cells[cell] += 1
            basis = t.get("basis") or f"none: {t.get('reason')}"
            by_basis.setdefault(basis, Counter())[cell] += 1
            block_rows.append([rule, key, t.get("target") or "", t.get("basis") or "", t.get("tier") or "",
                               label_text(agreed[key]) if agreed.get(key) else "", cell])
        counts["rule_vs_label_blocks"][rule] = {
            "all": {c: cells.get(c, 0) for c in BLOCK_CELLS},
            "by_basis": {b: {c: v.get(c, 0) for c in BLOCK_CELLS} for b, v in sorted(by_basis.items())}}
        if sum(cells.values()) != len(included):
            sentinels[6].append(f"{rule}: {sum(cells.values())} blocks counted, {len(included)} included")

    # -- the first reading of the flags -------------------------------------------------
    first_rows_out = []
    if first_path.is_file():
        _, first = read_tsv(first_path)
        if [(f["block"], f["index"], f["target"], f["deciding_check"]) for f in first] != \
                [(f["block"], f["index"], f["target"], f["deciding_check"]) for f in flags_rows]:
            sentinels[9].append(f"{first_path.name} does not list the flags of flags.csv in order")
        for f in first:
            labels_here = []
            for res in parsed:
                kind, cid = resolve(res["labels"].get(f["block"]), f["test_node"])
                labels_here.append(cid if kind == "check" else (NONE if kind == NONE else ""))
            akind, acid = case_label.get(f"{f['test_node']}|{f['block']}|{f['index']}", ("no label", None))
            ag = acid if akind == "check" else (NONE if akind == NONE else "")
            row = [f["block"], f["index"], f["test_node"], f["class"], f["target"], f["deciding_check"],
                   f["described_check"]] + labels_here + ([""] if len(parsed) == 1 else []) + [
                ag, ("yes" if ag == f["described_check"] else "no") if ag and f["described_check"] else ""]
            first_rows_out.append(row)
        counts["first_reading"] = {
            "flags": len(first),
            "agreed_label_equals_described": sum(1 for r in first_rows_out if r[-1] == "yes"),
            "agreed_label_differs_from_described": sum(1 for r in first_rows_out if r[-1] == "no"),
            "not_compared": sum(1 for r in first_rows_out if r[-1] == "")}
    elif flags_rows:
        counts["first_reading"] = {"flags": len(flags_rows), "transcription": "absent"}

    # -- outputs ------------------------------------------------------------------------
    counts["sentinels"] = {str(k): {"text": SENTINELS[k], "holds": not v, "problems": v[:50],
                                    "problems_total": len(v)}
                           for k, v in sentinels.items()}
    if not first_path.is_file():
        counts["sentinels"]["9"]["holds"] = None
        counts["sentinels"]["9"]["note"] = "no transcription of the first reading for this subject"
    out.mkdir(parents=True, exist_ok=True)
    two = len(parsed) == 2
    (out / "agreement.csv").write_text(csv_text(["block", "label_1", "label_2", "category"],
                                                agreement_rows), encoding="utf-8")
    (out / "outcomes.csv").write_text(csv_text(
        ["block", "index", "test_node", "label", "deciding", "label_fired", "outcome",
         "status_without_deciding", "site_without_deciding", "label_fires_without_deciding"],
        outcome_rows), encoding="utf-8")
    (out / "rule-vs-label.csv").write_text(csv_text(
        ["rule", "block", "index", "test_node", "target", "tier", "label", "category"], rule_rows),
        encoding="utf-8")
    (out / "rule-vs-label-blocks.csv").write_text(csv_text(
        ["rule", "block", "target", "basis", "tier", "label", "cell"], block_rows), encoding="utf-8")
    if first_rows_out:
        (out / "first-reading.csv").write_text(csv_text(
            ["block", "index", "test_node", "class", "target", "deciding_check", "described_first",
             "label_1", "label_2", "agreed_label", "agreed_equals_described"], first_rows_out),
            encoding="utf-8")
    (out / "counts.json").write_text(json.dumps(counts, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
    (out / "COUNTS.md").write_text(counts_md(counts, two), encoding="utf-8")
    failed = [k for k, v in sentinels.items() if v and not (k == 9 and not first_path.is_file())]
    print(f"analyse_labels: {name}: {len(included)} included blocks, {len(keys)} cases, {with_label} with an "
          f"agreed label that names a check; sentinels not holding: {failed or 'none'}")
    return 1 if failed else 0


def counts_md(c: dict, two: bool) -> str:
    L = [f"# Labels by reading: {c['subject']}", "",
         f"Labels files: {', '.join(c['labels_files'])}" + (f"; rule 3: {c['rule_3']}" if c["rule_3"] else ""),
         ""]
    for f, v in c.get("labels", {}).items():
        L.append(f"- {f}: {v['blocks_labeled']} blocks labeled; check {v['label_check']}, none "
                 f"{v['label_none']}, by parameter {v['label_by_param']}; bases "
                 + ", ".join(f"{k} {n}" for k, n in v["by_basis"].items())
                 + f"; {len(v['class_outside'])} labels whose class is not an expected class or a subclass "
                   f"of one; {v['warnings']} warnings")
    L += ["", "## Agreement (included blocks)", "", "| Category | Blocks |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in c["agreement"].items()]
    if "agreement_statistics" in c:
        L += ["", "| Categories | Blocks | Categories used | Equal | Observed agreement | Expected by chance "
                  "| Cohen's kappa |", "|---|---|---|---|---|---|---|"]
        for title, key in (("each label text", "labels"), ("a check is named, or none", "check_or_none")):
            v = c["agreement_statistics"][key]
            L.append(f"| {title} | {v['items']} | {v['categories']} | {v['equal']} | {v['observed']} "
                     f"| {v['expected']} | {v['kappa']} |")
    L += ["", f"Cases of the study: {c['cases']}; with an agreed label that names a check: "
              f"{c['cases_with_agreed_label_check']}; agreed label none: {c['cases_with_agreed_label_none']}; "
              f"no agreed label: {c['cases_without_agreed_label']}.", "",
          "## Outcome of the cases with an agreed label that names a check", "",
          "| Outcome | Cases |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in c["outcomes"].items()]
    for rule, v in c["rule_vs_label"].items():
        L += ["", f"## {rule} against the agreed label (cases)", "",
              "| Tier of the target | " + " | ".join(CATEGORIES) + " |",
              "|---|" + "---|" * len(CATEGORIES)]
        for t, row in list(v["by_tier"].items()) + [("all", v["all"])]:
            L.append(f"| {t} | " + " | ".join(str(row[k]) for k in CATEGORIES) + " |")
    for rule, v in c["rule_vs_label_blocks"].items():
        L += ["", f"## {rule} against the agreed label (included blocks)", "",
              "| Basis of the target, or reason for none | " + " | ".join(BLOCK_CELLS) + " |",
              "|---|" + "---|" * len(BLOCK_CELLS)]
        for b, row in list(v["by_basis"].items()) + [("all", v["all"])]:
            L.append(f"| {b} | " + " | ".join(str(row[k]) for k in BLOCK_CELLS) + " |")
    if "first_reading" in c:
        L += ["", "## First reading of the flags", ""]
        L += [f"- {k}: {v}" for k, v in c["first_reading"].items()]
    L += ["", "## Sentinels", ""]
    for k, v in c["sentinels"].items():
        state = "holds" if v["holds"] else ("not applicable" if v["holds"] is None else "does not hold")
        L.append(f"{k}. {v['text']}: {state}" + (f" ({v['problems_total']} problems)" if v["problems_total"] else ""))
        L += [f"   - {p}" for p in v["problems"][:10]]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())

"""Independent recomputation of analysis C (labels that rest on a test's name).

Reads only cases.json, checks.json and generated/outcomes.jsonl of the second
study (and its generated/summary.json for the reproduction sentinel), and
writes recomputed.json next to this file. Standard library only.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[2] / "mutation-adequacy-pyjwt"
OUT = HERE / "recomputed.json"


def fail(msg):
    sys.stderr.write("SENTINEL FAILED: " + msg + "\n")
    sys.exit(2)


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


cases_doc = load_json(STUDY / "cases.json")
checks_doc = load_json(STUDY / "checks.json")
summary = load_json(STUDY / "generated" / "summary.json")
with open(STUDY / "generated" / "outcomes.jsonl", encoding="utf-8") as f:
    lines = [json.loads(x) for x in f if x.strip()]
header, runs = lines[0], lines[1:]
FIELDS = header["fields"]
IDX = {name: i for i, name in enumerate(FIELDS)}

blocks = {b["key"]: b for b in cases_doc["blocks"] if b["included"]}
checks = {c["id"]: c for c in checks_doc["checks"]}


def block_labels(block):
    """List of (param value or None, label dict with target/segment/basis)."""
    lab = block["label"]
    if "by_param" in lab:
        return [(v, lab["values"][v]) for v in sorted(lab["values"])]
    return [(None, lab)]


SETS = {
    "all": lambda basis: True,
    "without name-only": lambda basis: not basis.startswith("name:"),
    "without any name": lambda basis: "name:" not in basis,
    # Supplementary, not a protocol set: a basis that begins with the name but
    # also records another part (after ';') is kept, i.e. "the name alone" read
    # by substance rather than by the text prefix.
    "supplementary: name alone by substance": lambda basis: not (basis.startswith("name:") and ";" not in basis),
}


def label_for_case(case, keep):
    """Target and segment of a header case under a label set, from cases.json."""
    block = blocks.get(case["key"])
    if block is None:
        fail("case key not in cases.json: " + case["key"])
    lab = block["label"]
    if "by_param" in lab:
        value = case["params"].get(lab["by_param"])
        sub = lab["values"].get(value)
        if sub is None:
            fail("no label value for " + case["case"])
    else:
        sub = lab
    if sub.get("target") is None:
        return None, None
    if not keep(sub["basis"]):
        return None, None
    return sub["target"], sub.get("segment")


cases = header["cases"]
order = [c["case"] for c in cases]
if len(set(order)) != len(order):
    fail("duplicate case ids")
base = {c["case"]: c["baseline"] for c in cases}


def observed(obs):
    return obs is not None and obs[0] == "observed"


def holds_oc(case, obs):
    return obs[IDX["outcome"]] == "raised" and obs[IDX["class"]] == case_B[case]


def holds_ot(target, segment, obs):
    if obs[IDX["outcome"]] != "raised":
        return False
    if obs[IDX["site_check"]] != target:
        return False
    return segment is None or obs[IDX["site_segment"]] == segment


# B(c): the class the unmutated library raises (first baseline record).
case_B = {}
for cid in order:
    b = base[cid]
    if not observed(b) or b[IDX["outcome"]] != "raised":
        fail("baseline case did not raise: " + cid)
    case_B[cid] = b[IDX["class"]]

# Sentinel on the header: the B recorded by the study equals the baseline class.
for c in cases:
    if c["B"] != case_B[c["case"]]:
        fail("B differs from baseline class for " + c["case"])


def run_obs(run):
    """Per case: full observation list, or a status-only list, or None for not ran."""
    if run["state"] != "ran" or run["cases"] is None:
        return None
    out = {}
    for cid, o in zip(order, run["cases"]):
        out[cid] = base[cid] if o is None else o
    return out


def kill(run, s_set, holds):
    """Kill decision under one oracle; returns (killed, credited cases)."""
    obs = run_obs(run)
    if obs is None:
        return True, []
    statuses = [o[0] for o in obs.values()]
    if not any(st == "observed" for st in statuses):
        return True, []  # load failure: no case observed
    crashed_any = any(st == "crashed" for st in statuses)
    credited = []
    for cid in order:
        if cid not in s_set:
            continue
        o = obs[cid]
        if o[0] == "crashed":
            credited.append(cid)
        elif o[0] == "observed" and not holds(cid, o):
            credited.append(cid)
        # withheld / missing: excluded
    return (crashed_any or bool(credited)), credited


def mutant_function(run_name):
    # e.g. jwt.api_jws.xǁPyJWSǁ_load__mutmut_3
    module, rest = run_name.split(".xǁ", 1)
    cls, meth = rest.split("ǁ", 1)
    meth = meth.rsplit("__mutmut_", 1)[0]
    return module.replace(".", "/") + ".py", cls + "." + meth


mutants = [r for r in runs if r["set"] == "mutant"]
deletions = [r for r in runs if r["set"] == "deletion"]
if len({r["run"] for r in mutants}) != len(mutants):
    fail("duplicate mutant runs")

# O_C, independent of the labels.
S_OC = {cid for cid in order if holds_oc(cid, base[cid])}
kills_oc = set()
for r in mutants:
    k, _ = kill(r, S_OC, lambda cid, o: holds_oc(cid, o))
    if k:
        kills_oc.add(r["run"])

# Reached checks: baseline raise site of some case, among checks of the mutated files.
reached = sorted({base[cid][IDX["site_check"]] for cid in order} & {c for c in checks if checks[c]["mutated"]})

results = {}
for set_name, keep in SETS.items():
    tgt = {}
    for c in cases:
        t, seg = label_for_case(c, keep)
        if t is not None:
            if t not in checks:
                fail("unknown target check " + t)
            tgt[c["case"]] = (t, seg)
    labelled_blocks = 0
    for key, block in blocks.items():
        if any(sub.get("target") is not None and keep(sub["basis"]) for _, sub in block_labels(block)):
            labelled_blocks += 1
    S_OT = {cid for cid in tgt if holds_ot(*tgt[cid], base[cid])}

    def h_ot(cid, o, tgt=tgt):
        return holds_ot(*tgt[cid], o)

    kills_ot, credited_ot = set(), {}
    for r in mutants:
        k, cred = kill(r, S_OT, h_ot)
        if k:
            kills_ot.add(r["run"])
        credited_ot[r["run"]] = cred
    undetected = []
    for r in deletions:
        if r["run"] not in reached:
            continue
        k, _ = kill(r, S_OT, h_ot)
        if not k:
            undetected.append(r["run"])
    # P5
    p5_cases, p5_failing, p5_counts = [], [], {}
    for cid in sorted(S_OT):
        check = checks[tgt[cid][0]]
        if not check["mutated"]:
            continue
        func = (check["file"], check["function"])
        n = sum(1 for r in mutants if mutant_function(r["run"]) == func and cid in credited_ot[r["run"]])
        p5_cases.append(cid)
        p5_counts[cid] = n
        if n == 0:
            p5_failing.append(cid)
    results[set_name] = {
        "labelled_blocks": labelled_blocks,
        "cases_with_target": len(tgt),
        "P1_O_T_holds_at_baseline": len(S_OT),
        "P1_O_T_misses": sorted(set(tgt) - S_OT),
        "reached_deletions_undetected_O_T": sorted(undetected),
        "kills_O_T": len(kills_ot),
        "kills_O_C": len(kills_oc),
        "O_T_minus_O_C": sorted(kills_ot - kills_oc),
        "O_C_minus_O_T": sorted(kills_oc - kills_ot),
        "P5_cases": len(p5_cases),
        "P5_cases_with_kill": len(p5_cases) - len(p5_failing),
        "P5_failing": p5_failing,
        "P5_kills_by_case": p5_counts,
        "cases_dropped_vs_all": [],
    }

# cases dropped relative to "all"
tg_all = {c["case"] for c in cases if label_for_case(c, SETS["all"])[0] is not None}
for set_name, keep in SETS.items():
    tg = {c["case"] for c in cases if label_for_case(c, keep)[0] is not None}
    results[set_name]["cases_dropped_vs_all"] = sorted(tg_all - tg)

# Reproduction sentinel for "all", against the study's own summary.json.
a = results["all"]
checks_vs_study = {
    "labelled_blocks": (a["labelled_blocks"], cases_doc["counts"]["labelled_blocks"]),
    "cases_with_target": (a["cases_with_target"], summary["cases"]["labelled"]),
    "S_O_T": (a["P1_O_T_holds_at_baseline"], summary["cases"]["S"]["O_T"]),
    "kills_O_T": (a["kills_O_T"], summary["totals"]["O_T"]["killed"]),
    "kills_O_C": (a["kills_O_C"], summary["totals"]["O_C"]["killed"]),
    "O_T - O_C": (a["O_T_minus_O_C"], sorted(summary["predictions"]["P3"]["killed_O_T_not_O_C"])),
    "O_C - O_T": (len(a["O_C_minus_O_T"]), summary["gaps"]["O_C - O_T"]),
    "undetected O_T": (a["reached_deletions_undetected_O_T"],
                       sorted(k for k, v in summary["deletions"].items() if v["reached"] and not v["O_T"])),
    "P5 cases": (a["P5_cases"], summary["predictions"]["P5"]["cases"]),
    "P5 failing": (a["P5_failing"], sorted(summary["predictions"]["P5"]["failing"])),
    "P1 misses": (a["P1_O_T_misses"], sorted(m["case"] for m in summary["predictions"]["P1"]["O_T_misses"])),
}
for name, (mine, theirs) in sorted(checks_vs_study.items()):
    if mine != theirs:
        fail(f"row 'all' does not reproduce the study: {name}: {mine!r} != {theirs!r}")

out = {"label_sets": {k: results[k] for k in sorted(results)}, "reached_checks": len(reached)}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, sort_keys=True, ensure_ascii=False)
    f.write("\n")
for k in SETS:
    r = results[k]
    print(k, {x: (len(v) if isinstance(v, list) else v) for x, v in r.items()})

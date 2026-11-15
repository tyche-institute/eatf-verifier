"""Compare recomputed.json with the implementer's generated/label-sensitivity.json."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
mine = json.load(open(HERE / "recomputed.json", encoding="utf-8"))["label_sets"]
theirs = {s["label_set"]: s for s in json.load(open(HERE.parents[1] / "generated" / "label-sensitivity.json", encoding="utf-8"))["label_sets"]}
PAIRS = [
    ("labelled_blocks", "labelled_blocks", None),
    ("cases_with_target", "cases_with_target", None),
    ("P1_O_T_holds_at_baseline", "P1_O_T_holds", None),
    ("P1_O_T_misses", "P1_O_T_fails_on", sorted),
    ("kills_O_T", "kills_O_T", None),
    ("kills_O_C", "kills_O_C", None),
    ("O_T_minus_O_C", "O_T_not_O_C", sorted),
    ("O_C_minus_O_T", "O_C_not_O_T", sorted),
    ("P5_cases", "P5_cases", None),
    ("P5_failing", "P5_failing", sorted),
]
diffs = 0
for name in sorted(set(theirs) | {k for k in mine if not k.startswith('supplementary')}):
    m, t = mine.get(name), theirs.get(name)
    if m is None or t is None:
        print("label set missing:", name); diffs += 1; continue
    for a, b, norm in PAIRS:
        x, y = m[a], t[b]
        if norm: y = norm(y)
        if x != y:
            diffs += 1; print(name, a, x, "!=", y)
    dels = t.get("deletions_undetected_O_T")
    print(name, "theirs deletions_undetected_O_T:", dels, "mine:", m["reached_deletions_undetected_O_T"])
    rows = {r["case"]: r["kills_O_T"] for r in t["P5_rows"]}
    if rows != m["P5_kills_by_case"]:
        diffs += 1
        for c in sorted(set(rows) | set(m["P5_kills_by_case"])):
            if rows.get(c) != m["P5_kills_by_case"].get(c): print(name, "P5 row", c, m["P5_kills_by_case"].get(c), rows.get(c))
print("differences:", diffs)

import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
mine = json.loads((HERE / "recompute-b.json").read_text())
theirs = json.loads((HERE.parents[1] / "generated" / "shared-operators.json").read_text())
VAR = {"all mutants": "all", "without code-literal mutants": "without_code_literal"}
GRP = {"all operators": "all_operators", "shared classes": "shared_classes", "outside the table": "outside_classes"}
diffs, seen = [], set()
for r in theirs["rows"]:
    p, g, v = r["port"], r["group"], VAR[r["variant"]]
    blk = mine[p][GRP[g]] if g in GRP else mine[p]["per_class"][g]
    m = blk[v]
    seen.add((p, g, v))
    pairs = {"mutants": m["subject_mutants"], "killed_O_V": m["killed_O_V"], "killed_O_C": m["killed_O_C"],
             "gap": m["gap_mutants"], "later_guard_share": m["later_guard_share_of_gap"],
             "gap_mixed": 0}
    for d, n in m["gap_by_direction"].items():
        pairs["gap_" + d.replace(" ", "_")] = n
    for k, val in pairs.items():
        if r.get(k) != val:
            diffs.append((p, g, v, k, r.get(k), val))
    extra = set(r) - set(pairs) - {"group", "port", "tool", "variant", "operators"}
    if extra:
        diffs.append((p, g, v, "unexpected keys", sorted(extra), None))
expected = {(p, g, v) for p in mine for g in [*GRP, *mine[p]["per_class"]] for v in VAR.values()}
for miss in sorted(expected - seen):
    diffs.append((*miss, "row missing in implementer output", None, None))
print(f"rows compared: {len(theirs['rows'])}; differences: {len(diffs)}")
for d in diffs:
    print(d)
# headline
for v, vk in VAR.items():
    for p in ("python", "typescript"):
        for g in ("all operators", "shared classes"):
            h = theirs["headline"][v][p][g]; m = mine[p][GRP[g]][vk]
            if (h["gap"], h["later_guard"], h["later_guard_share"]) != (m["gap_mutants"], m["gap_by_direction"]["later guard"], m["later_guard_share_of_gap"]):
                print("headline diff", v, p, g, h, m)
print("top-level keys:", sorted(theirs))

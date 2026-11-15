import ast, csv, json, sys
from pathlib import Path
S = Path(__file__).resolve().parents[3] / "mutation-adequacy-pyjwt"
checks = json.loads((S / "checks.json").read_text())
reached = {r["check"] for r in csv.DictReader((S / "generated/deletions.csv").open()) if r["reached"] == "yes"}
print("reached", len(reached))
handlers = {}
for f in {c["file"] for c in checks["checks"]}:
    src = (S / "work/pyjwt" / f).read_text()
    tree = ast.parse(src)
    hs = []
    raises = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler):
            hs.append((n.lineno, n.end_lineno))
        if isinstance(n, ast.Raise):
            raises.append(n)
    handlers[f] = (hs, raises, src.splitlines())
out = []
for c in checks["checks"]:
    if not c["mutated"]:
        continue
    hs, raises, lines = handlers[c["file"]]
    inh = []
    for k, (a, b) in zip(c["raises"], c["lines"]):
        # confirm a Raise node sits at those lines
        rn = [r for r in raises if r.lineno == a and r.end_lineno == b]
        assert len(rn) == 1, (c["id"], a, b)
        if any(h0 < a and b <= h1 for h0, h1 in hs):
            inh.append((k, a, b))
    if inh:
        out.append((c["id"], c["id"] in reached, inh, c["raises"], c["lines"]))
for o in out:
    print(o)
print("handler & reached:", sorted(o[0] for o in out if o[1]))

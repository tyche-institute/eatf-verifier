"""Independent check of analysis D for three handler checks: own copy, own edit, own run."""
import sys
sys.dont_write_bytecode = True
import ast, csv, difflib, importlib.util, json, os, shutil, subprocess
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROB = HERE.parents[1]
S = ROB.parent / "mutation-adequacy-pyjwt"
SUBJ = S / "work/pyjwt"
PY = S / "work/venv/bin/python"
CHECKS = json.loads((S / "checks.json").read_text())
CK = {c["id"]: c for c in CHECKS["checks"]}
PICK = {"jws.segment-encoding": [3], "jwt.iat-type": [0], "jws.header-json": [2]}

spec = importlib.util.spec_from_file_location("a2", S / "analyse_s2.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

def build(cid, inh):
    c = CK[cid]
    dest = HERE / "copies" / cid
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ig = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(SUBJ / "jwt", dest / "jwt", ignore=ig)
    shutil.copytree(SUBJ / "tests", dest / "tests", ignore=ig)
    shutil.copy2(SUBJ / "pyproject.toml", dest / "pyproject.toml")
    p = dest / c["file"]
    lines = p.read_text().split("\n")
    for k, (a, b) in zip(c["raises"], c["lines"]):
        first = lines[a - 1]
        indent = first[: len(first) - len(first.lstrip())]
        assert first.lstrip().startswith("raise "), first
        lines[a - 1] = indent + ("raise" if k in inh else "pass")
        for i in range(a, b):
            lines[i] = ""
    p.write_text("\n".join(lines))
    orig = (SUBJ / c["file"]).read_text().splitlines(keepends=True)
    new = p.read_text().splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(orig, new, c["file"], c["file"] + " (R)", n=0))
    (HERE / f"{cid}.diff").write_text(diff)
    impl = ROB / "work/copies/R" / cid / c["file"]
    same_as_impl = impl.exists() and impl.read_bytes() == p.read_bytes()
    return dest, diff, same_as_impl

def run(cid, dest):
    out = HERE / "records" / f"{cid}.json"
    out.parent.mkdir(exist_ok=True)
    if out.exists(): out.unlink()
    env = {"PATH": f"{S/'work/venv/bin'}:/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp"),
           "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": str(S / "plugin"), "S2_CASES": str(S / "cases.json"), "S2_CHECKS": str(S / "checks.json"),
           "S2_OUT": str(out), "S2_PACKAGE": "jwt", "S2_SELECT": "cases"}
    cmd = [str(PY), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:randomly", "--rootdir=.",
           "--tb=native", "-p", "s2_recorder", "--continue-on-collection-errors"]
    subprocess.run(cmd, cwd=dest, env=env, capture_output=True, text=True, timeout=120)
    return json.loads(out.read_text())

# own line map: (file, line) -> check, from checks.json line ranges of the unmodified source
LINEMAP = {}
for c in CHECKS["checks"]:
    for (a, b) in c["lines"]:
        for l in range(a, b + 1):
            LINEMAP[(c["file"], l)] = c["id"]

base = json.loads((S / "work/records/baseline/base-1.json").read_text())
cases = A.baseline_cases(base)
bstate = A.run_state(S / "work/records/baseline/base-1.json", None, cases)
SO = {o: {cid for cid, (k, r) in bstate["cases"].items() if k == "observed" and A.holds(o, cases[cid], r)}
      for o in A.ORACLES}

impl_cases = list(csv.DictReader((ROB / "generated/handler-variant-cases.csv").open()))
impl_rows = {(r["check"], r["variant"]): r for r in csv.DictReader((ROB / "generated/handler-variant.csv").open())}
report = {}
for cid, inh in PICK.items():
    dest, diff, same = build(cid, inh)
    rec = run(cid, dest)
    remap = 0
    for b in rec["blocks"]:
        site = b.get("site")
        if not b["included"] or not site or not site["frames"]:
            continue
        inner = site["frames"][-1]
        chk = LINEMAP.get((inner["file"], inner["line"]))
        seg = site["segment"] if chk == site["check"] else None
        if chk != site["check"]:
            remap += 1
            site["check"], site["segment"] = chk, seg
    obs = {A.case_id(b): b for b in rec["blocks"] if b["included"]}
    changed, mine = [], {}
    crashed = False
    for k, case in cases.items():
        r = obs.get(k)
        if r is None:
            changed.append((k, "not observed")); crashed = True; continue
        st = r.get("site") or {}
        if (r.get("class") != case["B"] or st.get("check") != case["site"] or st.get("segment") != case["site_segment"]
                or r.get("message") != case["message"] or r.get("real") != "ok"):
            cls = r.get("class") if r.get("outcome") == "raised" else "no exception"
            changed.append((k, cls))
            mine[k] = {"class": cls, "site": st.get("check") or "", **{A.NAMES[o]: "yes" if A.holds(o, case, r) else "no" for o in A.ORACLES}}
    kills = {}
    for o in A.ORACLES:
        kills[A.NAMES[o]] = "yes" if (crashed or any(k in SO[o] and k in obs and not A.holds(o, cases[k], obs[k]) for k in cases)) else "no"
    theirs = {r["case"]: r for r in impl_cases if r["check"] == cid}
    case_diffs = []
    for k in sorted(set(mine) | set(theirs)):
        if k not in mine or k not in theirs:
            case_diffs.append((k, "missing in " + ("mine" if k not in mine else "theirs"))); continue
        for f in ["class", "site", "O_V", "O_V^fc", "O_C", "O_T", "O_S"]:
            if mine[k][f] != theirs[k][f]:
                case_diffs.append((k, f, mine[k][f], theirs[k][f]))
    row = impl_rows[(cid, "R")]
    row_diffs = {o: (kills[o], row[o]) for o in kills if kills[o] != row[o]}
    cls_mine = "; ".join(f"{a} {b}" for a, b in sorted(Counter(c for _, c in changed).items()))
    report[cid] = {"copy_identical_to_implementers": same, "diff_hunks": diff.count("\n@@"), "lines_changed": diff,
                   "kills_mine": kills, "row_diffs": row_diffs, "cases_changed": len(changed),
                   "cases_changed_impl": row["cases_changed"], "classes_mine": cls_mine,
                   "classes_impl": row["changed_case_classes"], "case_diffs": case_diffs, "sites_remapped_by_line": remap}
print(json.dumps(report, indent=1, sort_keys=True))

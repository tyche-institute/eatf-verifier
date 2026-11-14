"""The offline check of criterion I5 for 1 subject.

    python3 -I -B selection/offline_check.py DEFINITION CLONE VENV_PYTHON WORK

DEFINITION is subjects/<name>/draft.json or subjects/<name>/subject.json.
Copies the items of its "copy" list from the clone to WORK and runs every suite
run there, unmodified and without the recorder, 1 time plainly and 1 time with
the offline module `guard/reach_offline.py`, which refuses every connection
attempt to an address that is not a loopback address and every lookup of a
host name. Prints 1 line per suite run: pytest's summary line of both runs,
the number of tests whose outcome differs between them, the number of refused
attempts and the tests that made them. The check holds when both runs end with
a summary line and every test has the same outcome in both.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from reach.run import GUARD, OFFLINE, SUMMARY, junit_outcomes  # noqa: E402


def main(argv: list[str]) -> int:
    draft = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    clone, python, work = Path(argv[1]).resolve(), Path(argv[2]).absolute(), Path(argv[3]).resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for item in draft["copy"]:
        src = clone / item
        if src.is_dir():
            shutil.copytree(src, work / item, ignore=ignore)
        else:
            (work / item).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, work / item)
    env = {"PATH": f"{python.parent}:/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp"),
           "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}
    src_root = draft.get("source_root", ".")
    base_path = [str(work / src_root)] if src_root not in (".", "") else []
    ok = True
    for run in draft["suite_runs"]:
        lines, outcomes, attempts = [], [], None
        for offline in (False, True):
            label = "offline" if offline else "plain"
            xml = work.parent / f"{work.name}.{run['name']}.{label}.xml"
            out = work.parent / f"{work.name}.{run['name']}.attempts.json"
            for old in (xml, out):
                if old.exists():
                    old.unlink()
            cmd = [str(python), "-m", "pytest", "-q", *draft.get("pytest_args", []), *run.get("args", []),
                   *(OFFLINE if offline else []), "--rootdir=.", "--tb=no", f"--junitxml={xml}",
                   *run["paths"]]
            path = base_path + ([str(GUARD)] if offline else [])
            run_env = dict(env, **({"PYTHONPATH": os.pathsep.join(path)} if path else {}))
            if offline:
                run_env["OFFLINE_OUT"] = str(out)
            proc = subprocess.run(cmd, cwd=work, env=run_env, capture_output=True, text=True, timeout=7200)
            found = SUMMARY.findall(proc.stdout + proc.stderr)
            lines.append(found[-1] if found else None)
            outcomes.append(junit_outcomes(xml, run["name"]) if xml.exists() else None)
            if offline and out.exists():
                attempts = json.loads(out.read_text(encoding="utf-8"))
        plain, with_module = outcomes
        differ = (None if plain is None or with_module is None
                  else sorted(k for k in set(plain) | set(with_module) if plain.get(k) != with_module.get(k)))
        holds = None not in lines and differ == [] and attempts is not None
        ok = ok and holds
        shown = [line or "no summary line" for line in lines]
        print(f"{draft['name']} {draft['version']} | run {run['name']} | plain: {shown[0]} | "
              f"offline: {shown[1]} | tests: {None if plain is None else len(plain)} | "
              f"tests with another outcome: {None if differ is None else len(differ)} | "
              f"refused attempts: {None if attempts is None else attempts['attempts']}")
        for test, n in (attempts or {}).get("tests", {}).items():
            print(f"    {n} refused in {test or '(no test running)'}")
        for attempt in sorted(set((attempts or {}).get("first", []))):
            print(f"    attempt: {attempt}")
        for key in (differ or [])[:20]:
            print(f"    another outcome: {key}: plain {plain.get(key)}, offline {with_module.get(key)}")
    print(f"{draft['name']}: offline check {'holds' if ok else 'DOES NOT HOLD'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

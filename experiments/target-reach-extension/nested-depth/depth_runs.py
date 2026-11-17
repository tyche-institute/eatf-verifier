#!/usr/bin/env python3
"""Which check of PyJWT 2.15.1 rejects a header of deeply nested JSON arrays, by Python version.

    python3 -I -B depth_runs.py [--dry] [--clone DIR] [--python VERSION=PYTHON ...]
                                [--depths N ...] [--variants NAME ...] [--timeout SECONDS] [--stack-kib KIB]
                                [--work DIR] [--out FILE] [--checks FILE] [--checks-earlier FILE]

Adapted from ../../target-reach-followup/versions/nested_header.py (called "the
earlier script" below): the same commit, the same 2 variants, the same copy of
`jwt/`, `tests/` and `pyproject.toml`, the same payload and signature parts of
the token, and a fresh interpreter for every decode. The differences:

1. The header holds N nested arrays, `b"[" * N + b"]" * N`, for each N of
   --depths (default 10000 and 50000); the earlier script used the 1000 of the
   test `test_decode_deeply_nested_header_throws_decode_error`.
2. The decode is `jwt.decode(token, "secret", algorithms=["HS256"])`, the
   entry point of the package; the earlier script called `PyJWS().decode`.
3. No pytest call: no test of the package holds these headers. Each run is 1
   child process `PYTHON -I -B depth_runs.py --child COPY VARIANT N` with a
   time limit (--timeout, default 60 s) and the environment of the toolkit's
   runner (PATH starting with the folder of the interpreter, HOME inherited,
   LANG and LC_ALL C.UTF-8, PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1; the
   child runs with -I, which makes Python ignore the PYTHON* variables, and with
   -B, which keeps bytecode out of the copy). The soft stack size limit of the
   child is --stack-kib (default 8192 KiB, the `ulimit -s` of depth.jsonl next
   to the earlier script; 0 keeps the caller's); the child reports its limit.
4. Each row records what the decode gives: `outcome` is `rejected by a check`
   (an exception raised by a raise statement of a check), `exception outside
   the checks` (an exception raised elsewhere, for instance a RecursionError
   that leaves `json.loads` at line 372), `accepted` (no exception),
   `interpreter failed` (the child ends by a signal or without its row) or
   `timed out`. For an exception: its class, message (first 200 characters),
   cause, the innermost frame inside the copy (`raise_site`), the innermost
   frame of the traceback, and the check at the raise site, by the line ranges
   of 2 definition files read at run time: `check`, the id of
   ../../target-reach/subjects/pyjwt-package/checks.json, and
   `check_earlier_study`, the id of ../../mutation-adequacy-pyjwt/checks.json
   (the ids of the earlier script).
5. Variant `released` is the commit as released; variant `before-fix` is a
   copy where the JSON check catches `ValueError` only, the line before
   upstream commit 0657369 ("Handle recursive JWS headers as decode errors"),
   which this script reads from the clone with `git show` (sentinel N2).

Interpreters (--python VERSION=PYTHON; default the environments of
../work/nested-depth/venvs/): 3.12.3 (py312, made from /usr/bin/python3.12),
3.13.14 (py313) and 3.14.6 (py314), made from the builds of `uv python install`
in ../work/pythons/. The environments hold no package: PyJWT 2.15.1 needs none
on Python 3.11 and later (its pyproject.toml asks for typing_extensions on
earlier versions only).

Sentinels. The program stops at once when N1, N2, N4 or N5 does not hold; it
prints every row and exits with status 1 when another does not:
N1  the clone is at COMMIT;
N2  `git show 0657369 -- jwt/api_jws.py` removes exactly the line BEFORE_FIX
    and adds exactly the line RELEASED;
N3  in each copy, lines 372, 374 and 377 of jwt/api_jws.py hold the statements
    of LINES, and the 2 definition files give checks at lines 374 and 377;
N4  the variant edit replaces exactly 1 except clause;
N5  `jwt` is imported from the copy;
N6  the interpreter is CPython in the version of --python;
N7  the C scanner of `json` is the one in use;
N8  the child runs with the stack limit asked for.

--dry prints the interpreters (with the version each reports), the checks of
N1 and N2, and every child command with its copy, environment, time limit and
stack limit; it makes no copy and decodes nothing.

Output: --out (default results.jsonl next to this file), 1 JSON object per run,
by interpreter, variant and depth, each with the settings the child prints first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import shutil
import signal
import subprocess
import sys
import sysconfig
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent                      # target-reach-extension/nested-depth
EXTENSION = HERE.parent
EXPERIMENTS = EXTENSION.parent
WORK = EXTENSION / "work" / "nested-depth"
COMMIT = "7d5ef55e42ce42221f58dc49943e92ccad1fa66a"          # PyJWT 2.15.1
FIX_COMMIT = "06573692ebcdec8831c3927513b3e87c31fbbb62"      # "Handle recursive JWS headers as decode errors"
RELEASED = "        except (ValueError, RecursionError) as e:\n"
BEFORE_FIX = "        except ValueError as e:\n"
LINES = {372: 'header: dict[str, Any] = json.loads(header_data)',
         374: 'raise DecodeError(f"Invalid header string: {e}") from e',
         377: 'raise DecodeError("Invalid header string: must be a json object")'}
PAYLOAD = "eyJoZWxsbyI6ICJ3b3JsZCJ9"                          # the token parts of the test, as in the earlier script
SIGNATURE = "tvagLDLoaiJKxOKqpBXSEGy7SYSifZhjntgm9ctpyj8"
CHECKS = EXPERIMENTS / "target-reach" / "subjects" / "pyjwt-package" / "checks.json"
CHECKS_EARLIER = EXPERIMENTS / "mutation-adequacy-pyjwt" / "checks.json"
PYTHONS = {"3.12.3": WORK / "venvs" / "py312" / "bin" / "python",
           "3.13.14": WORK / "venvs" / "py313" / "bin" / "python",
           "3.14.6": WORK / "venvs" / "py314" / "bin" / "python"}
DEPTHS = (10_000, 50_000)
VARIANTS = ("released", "before-fix")
TIMEOUT = 60.0
STACK_KIB = 8192
MESSAGE = 200


# -- in the child: 1 decode --------------------------------------------------------------

def frame(f, copy: Path) -> dict:
    path = Path(f.filename)
    try:
        rel = path.resolve().relative_to(copy.resolve()).as_posix()
        where = "copy"
    except ValueError:
        stdlib = Path(sysconfig.get_paths()["stdlib"]).resolve()
        try:
            rel, where = path.resolve().relative_to(stdlib).as_posix(), "stdlib"
        except ValueError:
            rel, where = str(path), "other"
    return {"file": rel, "line": f.lineno, "function": f.name, "in": where}


def child(copy: Path, variant: str, depth: int) -> int:
    sys.path.insert(0, str(copy))
    import json.scanner                                        # binds the local name json to the package
    import jwt                                                 # the copy, checked next (N5)
    from jwt.utils import base64url_encode
    if not Path(jwt.__file__).resolve().is_relative_to(copy.resolve()):
        print(f"N5: jwt imported from {jwt.__file__}, not from the copy", file=sys.stderr)
        return 3
    header = b"[" * depth + b"]" * depth
    token = ".".join((base64url_encode(header).decode(), PAYLOAD, SIGNATURE))
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    row = {"python": platform.python_version(), "implementation": platform.python_implementation(),
           "executable": sys.executable, "base_prefix": sys.base_prefix,
           "variant": variant, "depth": depth, "recursion_limit": sys.getrecursionlimit(),
           "json_c_scanner": json.scanner.c_make_scanner is not None,
           "stack_limit_kib": None if soft == resource.RLIM_INFINITY else soft // 1024}
    print(json.dumps(row), flush=True)                         # the settings, kept if the decode ends the process
    start = time.monotonic()
    try:
        value = jwt.decode(token, "secret", algorithms=["HS256"])
        row.update(decoded=True, value_type=type(value).__name__, exception=None)
    except Exception as e:                                     # noqa: BLE001  (every outcome is recorded)
        frames = traceback.extract_tb(e.__traceback__)
        inside = [f for f in frames if Path(f.filename).resolve().is_relative_to(copy.resolve())]
        cause = e.__cause__
        row.update(decoded=False, exception=f"{type(e).__module__}.{type(e).__qualname__}",
                   message=str(e)[:MESSAGE],
                   cause=None if cause is None else f"{type(cause).__module__}.{type(cause).__qualname__}",
                   cause_message=None if cause is None else str(cause)[:MESSAGE],
                   raise_site=frame(inside[-1], copy) if inside else None,
                   innermost_frame=frame(frames[-1], copy) if frames else None,
                   frames=len(frames))
    row["seconds"] = round(time.monotonic() - start, 6)
    print(json.dumps(row), flush=True)
    return 0


# -- in the parent ---------------------------------------------------------------------

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def site_problems(api_jws: Path) -> list[str]:
    """N3: the lines named by LINES hold the expected statements."""
    lines = api_jws.read_text(encoding="utf-8").splitlines()
    out = []
    for number, statement in sorted(LINES.items()):
        found = lines[number - 1].strip() if number <= len(lines) else None
        if found != statement:
            out.append(f"N3: line {number} of {api_jws.name} is {found!r}, expected {statement!r}")
    return out


def check_index(path: Path) -> dict[tuple[str, int], str]:
    """(file, line) -> check id, from the line ranges of a checks.json."""
    out = {}
    for c in json.loads(path.read_text(encoding="utf-8"))["checks"]:
        for a, z in c["lines"]:
            for line in range(a, z + 1):
                out[(c["file"], line)] = c["id"]
    return out


def fix_problems(clone: Path) -> list[str]:
    """N2: commit FIX_COMMIT changes the except clause of the JSON check from BEFORE_FIX to RELEASED."""
    show = subprocess.run(["git", "-C", str(clone), "show", "--format=", FIX_COMMIT, "--", "jwt/api_jws.py"],
                          capture_output=True, text=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    if show.returncode != 0:
        return [f"N2: git show {FIX_COMMIT[:7]} failed: {show.stderr.strip()[-200:]}"]
    removed = [ln[1:] for ln in show.stdout.splitlines() if ln.startswith("-") and not ln.startswith("---")]
    added = [ln[1:] for ln in show.stdout.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    if removed != [BEFORE_FIX.rstrip("\n")] or added != [RELEASED.rstrip("\n")]:
        return [f"N2: {FIX_COMMIT[:7]} removes {removed} and adds {added} in jwt/api_jws.py"]
    return []


def head_of(clone: Path) -> str:
    return subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True,
                          env=dict(os.environ, GIT_OPTIONAL_LOCKS="0")).stdout.strip()


def child_env(python: Path) -> dict[str, str]:
    """The environment of the toolkit's runner (Context.env of ../../target-reach/reach/run.py)."""
    return {"PATH": f"{python.parent}:/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}


def probe(python: Path) -> str:
    done = subprocess.run([str(python), "-I", "-c",
                           "import platform; print(platform.python_implementation(), platform.python_version())"],
                          capture_output=True, text=True)
    return done.stdout.strip() or f"? (exit {done.returncode}: {done.stderr.strip()[-120:]})"


def make_copy(clone: Path, dest: Path, variant: str) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(clone / "jwt", dest / "jwt", ignore=ignore)
    shutil.copytree(clone / "tests", dest / "tests", ignore=ignore)
    shutil.copy2(clone / "pyproject.toml", dest / "pyproject.toml")
    path = dest / "jwt" / "api_jws.py"
    if variant == "before-fix":
        src = path.read_text(encoding="utf-8")
        if src.count(RELEASED) != 1:
            raise SystemExit("N4: the JSON check's except clause is not where expected")
        path.write_text(src.replace(RELEASED, BEFORE_FIX), encoding="utf-8")
    elif variant != "released":
        raise SystemExit(f"unknown variant {variant!r}")
    return path


def limit_stack(kib: int):
    if kib <= 0:
        return None

    def apply() -> None:
        _soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        want = kib * 1024
        resource.setrlimit(resource.RLIMIT_STACK, (want if hard == resource.RLIM_INFINITY else min(want, hard), hard))
    return apply


def classify(row: dict, index: dict, earlier: dict) -> None:
    site = row.get("raise_site")
    key = (site["file"], site["line"]) if site and site["in"] == "copy" else None
    row["check"] = index.get(key) if key else None
    row["check_earlier_study"] = earlier.get(key) if key else None
    if row["decoded"]:
        row["outcome"] = "accepted"
    elif row["check"] is not None:
        row["outcome"] = "rejected by a check"
    else:
        row["outcome"] = "exception outside the checks"


def child_rows(stdout) -> tuple[dict | None, dict | None]:
    """The settings that the child prints before the decode, and its row with the result (None when absent).
    `stdout` is bytes when it comes from subprocess.TimeoutExpired."""
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", "replace")
    settings = row = None
    for line in (stdout or "").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "decoded" in value:
            row = value
        elif isinstance(value, dict) and settings is None:
            settings = value
    return settings, row


def settings_problems(row: dict, expect: str, args) -> list[str]:
    """N6 to N8, from the settings that the child reported."""
    out = []
    if f"{row.get('implementation')} {row.get('python')}" != f"CPython {expect}":
        out.append(f"N6: {row['python_path']} is {row.get('implementation')} {row.get('python')}, not CPython {expect}")
    if not row.get("json_c_scanner"):
        out.append(f"N7: {expect}: the C scanner of json is not in use")
    if args.stack_kib and row.get("stack_limit_kib") != args.stack_kib:
        out.append(f"N8: {expect}: the child runs with a stack limit of {row.get('stack_limit_kib')} KiB")
    return out


def signal_name(returncode: int) -> str | None:
    if returncode >= 0:
        return None
    try:
        return signal.Signals(-returncode).name
    except ValueError:
        return f"signal {-returncode}"


def one_run(python: Path, expect: str, copy: Path, variant: str, depth: int, args, index, earlier) -> tuple[dict, list]:
    cmd = [str(python), "-I", "-B", str(Path(__file__).resolve()), "--child", str(copy), variant, str(depth)]
    start = time.monotonic()
    base = {"interpreter": expect, "python_path": str(python), "variant": variant, "depth": depth,
            "timeout_seconds": args.timeout, "stack_kib_asked": args.stack_kib or None}
    try:
        done = subprocess.run(cmd, env=child_env(python), capture_output=True, text=True, timeout=args.timeout,
                              preexec_fn=limit_stack(args.stack_kib))
    except subprocess.TimeoutExpired as e:
        settings, _ = child_rows(e.stdout)
        row = {**base, **(settings or {}), "outcome": "timed out", "returncode": None,
               "wall_seconds": round(time.monotonic() - start, 3)}
        return row, settings_problems(row, expect, args) if settings else []
    wall = round(time.monotonic() - start, 3)
    if done.returncode == 3 and "N5:" in done.stderr:
        raise SystemExit(done.stderr.strip())
    settings, result = child_rows(done.stdout)
    if result is None or done.returncode < 0:              # "the child ends by a signal or without its row"
        row = {**base, **(settings or {}), "outcome": "interpreter failed", "returncode": done.returncode,
               "signal": signal_name(done.returncode), "stderr_tail": done.stderr[-500:], "wall_seconds": wall}
        if result is not None:
            row["row_before_the_signal"] = result
        return row, settings_problems(row, expect, args) if settings else []
    classify(result, index, earlier)
    row = {**base, **result, "returncode": done.returncode, "wall_seconds": wall}
    return row, settings_problems(row, expect, args)


def main(argv: list[str]) -> int:
    if len(argv) == 4 and argv[0] == "--child":
        return child(Path(argv[1]), argv[2], int(argv[3]))
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--clone", default=str(WORK / "pyjwt"))
    parser.add_argument("--python", action="append", help="VERSION=PYTHON (default: the 3 environments)")
    parser.add_argument("--depths", nargs="+", type=int, default=list(DEPTHS))
    parser.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=list(VARIANTS))
    parser.add_argument("--timeout", type=float, default=TIMEOUT)
    parser.add_argument("--stack-kib", type=int, default=STACK_KIB)
    parser.add_argument("--work", default=str(WORK))
    parser.add_argument("--out", default=str(HERE / "results.jsonl"))
    parser.add_argument("--checks", default=str(CHECKS))
    parser.add_argument("--checks-earlier", default=str(CHECKS_EARLIER))
    args = parser.parse_args(argv)
    pythons = dict(PYTHONS)
    if args.python:
        pythons = {}
        for value in args.python:
            version, sep, path = value.partition("=")
            if not sep:
                raise SystemExit(f"--python takes VERSION=PYTHON, not {value!r}")
            pythons[version] = Path(path).absolute()           # not resolved: a venv's python is a link
    clone = Path(args.clone).resolve()
    copies = Path(args.work).resolve() / "copies"

    head = head_of(clone)
    if head != COMMIT:
        raise SystemExit(f"N1: clone at {head or '?'}, not at {COMMIT}")
    fix = fix_problems(clone)
    if fix:
        raise SystemExit("; ".join(fix))
    index, earlier = check_index(Path(args.checks)), check_index(Path(args.checks_earlier))
    problems = site_problems(clone / "jwt" / "api_jws.py")
    for name, idx in (("checks", index), ("checks-earlier", earlier)):
        if not idx.get(("jwt/api_jws.py", 374)) or not idx.get(("jwt/api_jws.py", 377)):
            problems.append(f"N3: --{name} gives no check at line 374 or 377 of jwt/api_jws.py")
    print(f"clone {clone} at {head}; {FIX_COMMIT[:7]} replaces the except clause as expected; "
          f"checks {args.checks} (sha256 {sha256(Path(args.checks))}), "
          f"{args.checks_earlier} (sha256 {sha256(Path(args.checks_earlier))})", file=sys.stderr, flush=True)

    plan = [(v, p, variant, d) for v, p in pythons.items() for variant in args.variants for d in args.depths]
    if args.dry:
        for version, python in pythons.items():
            print(f"interpreter {version}: {python} reports {probe(python)}", flush=True)
        for version, python, variant, depth in plan:
            copy = copies / f"{version}-{variant}-{depth}"
            cmd = [str(python), "-I", "-B", str(Path(__file__).resolve()), "--child", str(copy), variant, str(depth)]
            print(json.dumps({"interpreter": version, "variant": variant, "depth": depth, "copy": str(copy),
                              "edit": "none" if variant == "released"
                              else f"jwt/api_jws.py: {RELEASED.strip()!r} -> {BEFORE_FIX.strip()!r}",
                              "cmd": cmd, "env": child_env(python), "timeout_seconds": args.timeout,
                              "stack_kib": args.stack_kib or "inherited"}), flush=True)
        for p in problems:
            print(p, file=sys.stderr)
        return 1 if problems else 0

    rows = []
    for version, python, variant, depth in plan:
        copy = copies / f"{version}-{variant}-{depth}"
        api_jws = make_copy(clone, copy, variant)
        problems += [f"{version} {variant} {depth}: {p}" for p in site_problems(api_jws)]
        row, found = one_run(python, version, copy, variant, depth, args, index, earlier)
        problems += found
        rows.append(row)
        print(json.dumps(row), flush=True)
        shutil.rmtree(copy)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {out}: {len(rows)} rows", file=sys.stderr)
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

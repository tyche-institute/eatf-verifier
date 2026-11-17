#!/usr/bin/env python3
"""Row 15 of no-fire/sample.csv: authlib, jose.rfc7516.jwe.JsonWebEncryption.get_header_zip#1.

    <venv>/bin/python -I -B 15.py [--clone DIR] [--work DIR] [--toolkit DIR] [--only NAME ...]

<venv> is the environment of the first study, `T/work/venvs/authlib` (CPython
3.12.3 with the pins of `T/subjects/authlib/requirements.txt`; T is
`../../../../target-reach`). The clone is `T/work/src/authlib` at the commit of
`T/subjects/authlib/subject.json`; it is only read.

For each input below, the script

1. makes a fresh copy of the release in `<work>/copy` (default `<work>` is
   `../../../work/reach/authlib`): the paths of `copy` in `subject.json`, without
   `__pycache__`, `*.pyc` and `.pytest_cache`, as the toolkit's `make_copy` makes
   a copy (`T/reach/run.py`, lines 310-330), and stops unless every subject file
   of the copy has the SHA-256 that `T/subjects/authlib/checks.json` gives it;
2. runs the input in a new interpreter (this one, with `-I -B`), from the copy,
   with the copy first on `sys.path` and the environment variables that the
   toolkit gives its pytest calls (`T/reach/run.py`, lines 155-165);
3. there, builds the artifact without any function of the package, sets a
   tracer (`sys.settrace`) that records each execution of a line of a raise
   statement of the check in the copy's file, calls the entry point, and
   records what reaches the caller: the exception with the innermost frame of
   its traceback inside the copy (its raise site), or the value returned.

Nothing of the package, of its dependencies or of its tests is changed,
patched or replaced. The script prints 1 JSON document on stdout.

The check: `authlib/jose/rfc7516/jwe.py`, the 2 statements
`raise UnsupportedCompressionAlgorithmError()` of
`JsonWebEncryption.get_header_zip` (lines 724-731), at line 728 (the header
holds "zip", line 725, the instance has a list of algorithms and the value of
"zip" is not in it, line 727) and at line 730 (the value is not a key of
`ZIP_REGISTRY`, line 729, which holds only "DEF": `authlib/jose/rfc7518/__init__.py`,
line 26, and `authlib/jose/rfc7518/jwe_zips.py`, lines 10-12).
`JsonWebEncryption.deserialize_compact` calls it at line 473 and
`deserialize_json` at line 561, before any key is used.

Inputs (the key, a 16-byte secret given as bytes, has no default):

- `a`: `JsonWebEncryption().deserialize_compact(token, key)`, with a compact
  JWE, protected header {"alg":"dir","enc":"A128GCM","zip":"XYZ"}, the payload
  encrypted with AES-128-GCM under the key; the raise expected is line 730;
- `b`: `JsonWebEncryption(algorithms=["dir","A128GCM"]).deserialize_compact(token, key)`,
  with a compact JWE, protected header {"alg":"dir","enc":"A128GCM","zip":"DEF"},
  the payload compressed with DEFLATE and encrypted under the key; the raise
  expected is line 728. Setting not the default: `algorithms`, the parameter
  of the constructor (`authlib/jose/rfc7516/jwe.py`, lines 49-51), here a list
  without "DEF"; the documentation shows the parameter for `JsonWebSignature`
  (`docs/jose/jws.rst`, line 110) and, with "DEF" in the list, for
  `JsonWebToken` (`docs/upgrades/changelog.rst`, lines 509-512);
- `c`: `JsonWebEncryption().deserialize(text, key)`, with the text of a JWE
  JSON serialization in the general syntax: the protected header of `a`, 1
  recipient with an empty encrypted key, and the payload encrypted under the
  key. `JsonWebEncryption.deserialize` calls `deserialize_json` for a text that
  starts with "{" and ends with "}" (`authlib/jose/rfc7516/jwe.py`, lines
  679-681); the raise expected is line 730.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROW = 15
CHECK = "jose.rfc7516.jwe.JsonWebEncryption.get_header_zip#1"
INPUT_NAMES = ("a", "b", "c")

HERE = Path(__file__).resolve().parent
EXTENSION = HERE.parents[2]
TOOLKIT = EXTENSION.parent / "target-reach"


# -- the inputs (run in the child, after the copy is on sys.path) -------------------

def b64url(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64json(obj: dict) -> str:
    return b64url(json.dumps(obj, separators=(",", ":")).encode("utf-8"))


def seal(protected: str, plaintext: bytes) -> tuple[bytes, bytes]:
    """AES-128-GCM under KEY, with the protected header segment as additional data (cryptography only)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    sealed = AESGCM(KEY).encrypt(IV, plaintext, protected.encode("ascii"))
    return sealed[:-16], sealed[-16:]


def compact_jwe(header: dict, plaintext: bytes) -> str:
    protected = b64json(header)
    ciphertext, tag = seal(protected, plaintext)
    return ".".join([protected, "", b64url(IV), b64url(ciphertext), b64url(tag)])


def raw_deflate(data: bytes) -> bytes:
    import zlib
    compressor = zlib.compressobj(level=9, wbits=-15)
    return compressor.compress(data) + compressor.flush()


KEY = b"row 15 dir key!!"
IV = b"row-15-iv-12"
PAYLOAD = b'{"sub":"row-15","iat":1700000000}'
HEADER_XYZ = {"alg": "dir", "enc": "A128GCM", "zip": "XYZ"}
HEADER_DEF = {"alg": "dir", "enc": "A128GCM", "zip": "DEF"}


def input_a():
    from authlib.jose import JsonWebEncryption
    token = compact_jwe(HEADER_XYZ, PAYLOAD)
    return {
        "entry_point": "authlib.jose.rfc7516.jwe.JsonWebEncryption.deserialize_compact",
        "settings": "JsonWebEncryption() (algorithms=None, private_headers=None: the defaults); "
                    "key: 16-byte secret (bytes)",
        "input": 'compact JWE, protected header {"alg":"dir","enc":"A128GCM","zip":"XYZ"}, '
                 "payload encrypted with AES-128-GCM under the key",
        "token": token,
        "call": lambda: JsonWebEncryption().deserialize_compact(token, KEY),
    }


def input_b():
    from authlib.jose import JsonWebEncryption
    token = compact_jwe(HEADER_DEF, raw_deflate(PAYLOAD))
    return {
        "entry_point": "authlib.jose.rfc7516.jwe.JsonWebEncryption.deserialize_compact",
        "settings": 'not the default: JsonWebEncryption(algorithms=["dir","A128GCM"]); '
                    "key: 16-byte secret (bytes)",
        "input": 'compact JWE, protected header {"alg":"dir","enc":"A128GCM","zip":"DEF"}, '
                 "payload compressed with DEFLATE and encrypted with AES-128-GCM under the key",
        "token": token,
        "call": lambda: JsonWebEncryption(algorithms=["dir", "A128GCM"]).deserialize_compact(token, KEY),
    }


def input_c():
    from authlib.jose import JsonWebEncryption
    protected = b64json(HEADER_XYZ)
    ciphertext, tag = seal(protected, PAYLOAD)
    text = json.dumps({"protected": protected, "recipients": [{"encrypted_key": ""}],
                       "iv": b64url(IV), "ciphertext": b64url(ciphertext), "tag": b64url(tag)},
                      separators=(",", ":"))
    return {
        "entry_point": "authlib.jose.rfc7516.jwe.JsonWebEncryption.deserialize",
        "settings": "JsonWebEncryption() (the defaults); key: 16-byte secret (bytes)",
        "input": 'JWE JSON serialization (general syntax, text), protected header '
                 '{"alg":"dir","enc":"A128GCM","zip":"XYZ"}, 1 recipient with an empty encrypted key, '
                 "payload encrypted with AES-128-GCM under the key",
        "token": text,
        "call": lambda: JsonWebEncryption().deserialize(text, KEY),
    }


INPUTS = {"a": input_a, "b": input_b, "c": input_c}


# -- the harness (the same in every script of this folder) --------------------------

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_definitions(toolkit: Path) -> tuple[dict, dict, dict]:
    subject = json.loads((toolkit / "subjects" / "authlib" / "subject.json").read_text(encoding="utf-8"))
    checks = json.loads((toolkit / "subjects" / "authlib" / "checks.json").read_text(encoding="utf-8"))
    check = next(c for c in checks["checks"] if c["id"] == CHECK)
    return subject, checks, check


def make_copy(clone: Path, dest: Path, subject: dict, checks: dict) -> int:
    """A fresh copy of the release, as T/reach/run.py make_copy and make_copy_check make it."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for item in subject["copy"]:
        src = clone / item
        if src.is_dir():
            shutil.copytree(src, dest / item, ignore=ignore)
        else:
            (dest / item).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / item)
    if subject.get("source_root", ".") not in (".", ""):
        raise SystemExit("this script expects source_root '.'")
    differ = [rel for rel, digest in checks["sha256"].items() if sha256(dest / rel) != digest]
    if differ:
        raise SystemExit(f"copy {dest}: {len(differ)} subject files differ from checks.json: {differ[:3]}")
    return len(checks["sha256"])


def child(name: str, copy: Path, check: dict) -> dict:
    copy = copy.resolve()
    sys.path.insert(0, str(copy))
    import authlib
    authlib_file = Path(authlib.__file__).resolve()
    if copy not in authlib_file.parents:
        raise SystemExit(f"authlib imported from {authlib_file}, not from the copy {copy}")
    target_file = str((copy / check["file"]).resolve())
    raise_lines = sorted({line for start, end in check["lines"] for line in range(start, end + 1)})
    source = Path(target_file).read_text(encoding="utf-8").splitlines()
    raise_text = {line: source[line - 1].strip() for line in raise_lines}
    hits: dict[int, int] = {}
    entered: dict[str, int] = {}   # functions of the check's file entered while the entry point ran
    events = {"line": 0}           # line events in the check's file, to show that the tracer saw it

    def local(frame, event, arg):
        if event == "line":
            events["line"] += 1
            if frame.f_lineno in raise_text:
                hits[frame.f_lineno] = hits.get(frame.f_lineno, 0) + 1
        return local

    def global_trace(frame, event, arg):
        if frame.f_code.co_filename != target_file:
            return None
        entered[frame.f_code.co_qualname] = entered.get(frame.f_code.co_qualname, 0) + 1
        return local

    spec = INPUTS[name]()
    call = spec.pop("call")
    outcome: dict
    sys.settrace(global_trace)
    try:
        value = call()
        outcome = {"kind": "returned", "value": repr(value)[:300]}
    except Exception as exc:  # the exception that reaches the caller
        site = None
        tb = exc.__traceback__
        while tb is not None:
            path = tb.tb_frame.f_code.co_filename
            if path.startswith(str(copy) + os.sep):
                site = {"file": os.path.relpath(path, copy), "line": tb.tb_lineno,
                        "function": tb.tb_frame.f_code.co_qualname}
            tb = tb.tb_next
        outcome = {"kind": "raised", "class": f"{type(exc).__module__}.{type(exc).__qualname__}",
                   "str": str(exc), "error": getattr(exc, "error", None),
                   "description": getattr(exc, "description", None), "raise_site": site}
    finally:
        sys.settrace(None)
    imported = sorted(m for m, mod in list(sys.modules.items())
                      if getattr(mod, "__file__", None) and str(Path(mod.__file__).resolve()) == target_file)
    import importlib.metadata
    return {"name": name, "within_4_4": True, **spec,
            "raise_lines": {str(k): v for k, v in raise_text.items()},
            "raise_lines_executed": {str(k): v for k, v in sorted(hits.items())},
            "functions_entered_in_file": dict(sorted(entered.items())),
            "line_events_in_file": events["line"],
            "module_of_file_imported": imported,
            "reached": bool(hits), "outcome": outcome,
            "authlib_file": str(authlib_file), "python": sys.version.split()[0],
            "cryptography": importlib.metadata.version("cryptography"),
            "executable": sys.executable}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--toolkit", default=str(TOOLKIT))
    parser.add_argument("--clone", default=str(TOOLKIT / "work" / "src" / "authlib"))
    parser.add_argument("--work", default=str(EXTENSION / "work" / "reach" / "authlib"))
    parser.add_argument("--only", nargs="+", choices=INPUT_NAMES)
    parser.add_argument("--child", choices=INPUT_NAMES, help=argparse.SUPPRESS)
    parser.add_argument("--copy", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    toolkit = Path(args.toolkit)
    subject, checks, check = load_definitions(toolkit)

    if args.child:
        print(json.dumps(child(args.child, Path(args.copy), check), sort_keys=True))
        return 0

    clone, work = Path(args.clone), Path(args.work)
    copy = work / "copy"
    venv_bin = Path(sys.executable).parent
    env = {"PATH": f"{venv_bin}:/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp"),
           "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}
    doc = {"row": ROW, "check": CHECK, "file": check["file"],
           "raise_lines": [start for start, _end in check["lines"]],
           "script": str(Path(__file__).resolve()), "script_sha256": sha256(Path(__file__)),
           "clone": str(clone.resolve()), "copy": str(copy.resolve()) if copy.exists() else str(copy),
           "interpreter": sys.executable, "python": sys.version.split()[0],
           "checks_json_sha256": sha256(toolkit / "subjects" / "authlib" / "checks.json"),
           "inputs": []}
    status = 0
    for name in args.only or INPUT_NAMES:
        start = utc()
        files = make_copy(clone, copy, subject, checks)
        proc = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child", name,
                               "--copy", str(copy.resolve()), "--toolkit", str(toolkit)],
                              cwd=copy, env=env, capture_output=True, text=True, timeout=600)
        end = utc()
        entry = {"name": name, "start": start, "end": end, "copy_subject_files_checked": files,
                 "returncode": proc.returncode, "stderr": proc.stderr.strip()[-2000:]}
        if proc.returncode == 0:
            entry.update(json.loads(proc.stdout))
        else:
            status = 1
            entry["stdout"] = proc.stdout[-2000:]
        doc["inputs"].append(entry)
    # the result rests only on the inputs that 4.4 of PROTOCOL.md admits
    doc["reached"] = any(e.get("reached") and e.get("within_4_4") for e in doc["inputs"])
    print(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False))
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

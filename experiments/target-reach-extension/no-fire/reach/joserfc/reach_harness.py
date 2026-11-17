#!/usr/bin/env python3
"""Shared code of the scripts 16.py to 20.py: the 5 sampled checks of joserfc
(rows 16 to 20 of `no-fire/sample.csv`), each sought through an entry point of
`../target-reach/subjects/joserfc/subject.json` (PROTOCOL.md, section 4.4).

A script is run as

    python3 -I <this folder>/<n>.py

and runs each of its cases 2 times, each time in a fresh interpreter on a fresh
copy. For every run, this process (the outer one):

  1. makes a fresh copy of the clone of the first study in
     `work/reach/joserfc/copy` of the extension, as `make_copy` of the toolkit
     does (`reach/run.py`, lines 310-322: the items of `copy` of subject.json,
     without `__pycache__`, `*.pyc` and `.pytest_cache`), and compares every
     subject file with `sha256` of checks.json and every test file with
     `test_files_sha256` of blocks.json;
  2. reads the commit of the clone from its `.git` files (no git command) and
     compares it with `commit` of subject.json; checks the interpreter of the
     environment (CPython 3.12.3) and its packages against requirements.txt, by
     the rule of `environment_problems` (`reach/run.py`, lines 278-305);
  3. runs the case in the interpreter of the environment,
     `python -I -B <n>.py --inner <case> <copy>`, with the working folder in the
     copy and the environment variables of the toolkit (`reach/run.py`, lines
     155-165); `-I` makes the interpreter ignore the PYTHON* variables, `-B`
     keeps it from writing bytecode;
  4. checks that no file of the copy was added, removed or changed by the run;
  5. writes the record of all runs to `<n>.json` beside the script.

The inner process puts the copy's source root first on `sys.path`, imports the
package from the copy (and stops if it comes from anywhere else), builds the
input with the tracer off, and calls the entry point with the tracer on. Only
the call is traced. Its record names `sys.prefix` (the venv) and the files of
the 2 dependencies that build the tokens, so it shows the environment it ran in. The tracer uses `sys.monitoring` with the tool ids that the
toolkit's recorder uses (4, then 3) and records, for the files of the package:
the lines executed (LINE), the functions entered (PY_START, first entry), and
every RAISE event. A RAISE event is a firing of a check under the rule of the
toolkit's recorder (`reach/recorder.py`, lines 237-264): the frame of the event
runs the code object of the event, its line is a line of a raise statement of
the check, the exception has the bare class name of the check (`class_name` of
checks.json) and the instruction at the offset is `RAISE_VARARGS`. The
exception that reaches the caller is recorded with its class, message, the
innermost frame of its traceback inside the package (as `site` of the
recorder, lines 194-210) and whether it is the object raised at the check.

Nothing of the package, of its dependencies or of its tests is changed,
patched or replaced. The tokens are built with the dependencies of the
environment (`cryptography`, `pycryptodome`), not with the package, and with
fixed keys and nonces, so the same tokens are built in every run.
"""
from __future__ import annotations

import base64
import csv
import dataclasses
import datetime
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent            # X/no-fire/reach/joserfc
EXTENSION = HERE.parents[2]                        # X
DEPOSIT = EXTENSION.parents[1]                     # M
TOOLKIT = EXTENSION.parent / "target-reach"        # T
LIBRARY = "joserfc"
DEFS = TOOLKIT / "subjects" / LIBRARY
CLONE = TOOLKIT / "work" / "src" / LIBRARY
VENV_PYTHON = TOOLKIT / "work" / "venvs" / LIBRARY / "bin" / "python"
COPY = EXTENSION / "work" / "reach" / LIBRARY / "copy"
SAMPLE = EXTENSION / "no-fire" / "sample.csv"
SAMPLE_SHA256 = "5637e6bc9241273992552eb79331b9e5095ee5c8e8b291afc718f2efeea3a8fa"
RUNS_PER_CASE = 2
TIMEOUT_SECONDS = 300
MAX_RAISE_EVENTS = 200

INTERPRETER_PROBE = "import platform, sys; print(platform.python_implementation(), sys.version.split()[0])"
PACKAGES_PROBE = ("import importlib.metadata as m, json\n"
                  "print(json.dumps(sorted([d.metadata['Name'] or '', d.version] for d in m.distributions())))\n")


# -- small helpers ---------------------------------------------------------------------

def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def from_deposit(path: Path | str) -> str:
    """A path relative to the root of the deposit, when it is inside it. Links
    are not followed, so the interpreter of the environment is named by its own
    path (`bin/python` of the venv), not by the system interpreter it links to."""
    p = Path(os.path.abspath(path))
    try:
        return p.relative_to(DEPOSIT).as_posix()
    except ValueError:
        return str(p)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def header_segment(header: dict) -> bytes:
    return b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))


# -- the tokens (the other party's side; built without the package) -----------------------

def jwe_dir_gcm(key: bytes, plaintext: bytes, iv: bytes, enc: str, encrypted_key: bytes = b"") -> str:
    """A JWE Compact Serialization with "alg": "dir" and an AES GCM "enc"
    (RFC 7516, section 7.1; RFC 7518, sections 4.5 and 5.3). The additional
    authenticated data is the encoded protected header (RFC 7516, section 5.1,
    step 14); `encrypted_key` is the content of the second segment."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    protected = header_segment({"alg": "dir", "enc": enc})
    sealed = AESGCM(key).encrypt(iv, plaintext, protected)
    ciphertext, tag = sealed[:-16], sealed[-16:]
    return b".".join([protected, b64url(encrypted_key), b64url(iv), b64url(ciphertext), b64url(tag)]).decode("ascii")


def jwe_dir_xc20p(key: bytes, plaintext: bytes, nonce: bytes) -> str:
    """A JWE Compact Serialization with "alg": "dir" and "enc": "XC20P"
    (XChaCha20-Poly1305: a 256-bit key and a 192-bit nonce), sealed with the
    pycryptodome cipher of the environment."""
    from Crypto.Cipher import ChaCha20_Poly1305
    protected = header_segment({"alg": "dir", "enc": "XC20P"})
    cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
    cipher.update(protected)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return b".".join([protected, b"", b64url(nonce), b64url(ciphertext), b64url(tag)]).decode("ascii")


def p256_private_key(secret: int):
    from cryptography.hazmat.primitives.asymmetric import ec
    return ec.derive_private_key(secret, ec.SECP256R1())


def p256_public_jwk(private_key, with_kty: bool = True) -> dict:
    numbers = private_key.public_key().public_numbers()
    jwk = {"kty": "EC", "crv": "P-256",
           "x": b64url(numbers.x.to_bytes(32, "big")).decode("ascii"),
           "y": b64url(numbers.y.to_bytes(32, "big")).decode("ascii")}
    if not with_kty:
        del jwk["kty"]
    return jwk


def jwe_ecdh_es_gcm(recipient_public, ephemeral_private, plaintext: bytes, iv: bytes, epk: dict) -> str:
    """A JWE Compact Serialization with "alg": "ECDH-ES" (direct key agreement)
    and "enc": "A128GCM" (RFC 7518, section 4.6): the content encryption key is
    the Concat KDF (SHA-256) of the shared secret, with AlgorithmID = "A128GCM",
    empty PartyUInfo and PartyVInfo, and SuppPubInfo = 128. `epk` is put in the
    protected header as given."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.concatkdf import ConcatKDFHash

    def with_length(data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + data

    shared = ephemeral_private.exchange(ec.ECDH(), recipient_public)
    other_info = with_length(b"A128GCM") + with_length(b"") + with_length(b"") + struct.pack(">I", 128)
    cek = ConcatKDFHash(algorithm=hashes.SHA256(), length=16, otherinfo=other_info).derive(shared)
    protected = header_segment({"alg": "ECDH-ES", "enc": "A128GCM", "epk": epk})
    sealed = AESGCM(cek).encrypt(iv, plaintext, protected)
    ciphertext, tag = sealed[:-16], sealed[-16:]
    return b".".join([protected, b"", b64url(iv), b64url(ciphertext), b64url(tag)]).decode("ascii")


def segment_lengths(token: str) -> list[int]:
    return [len(part) for part in token.split(".")]


# -- the cases of a script ----------------------------------------------------------------

@dataclasses.dataclass
class Case:
    """1 call. `kind` is "input" (a call of an entry point, PROTOCOL.md 4.4) or
    "control" (a call that is not an input and does not decide the result).
    `build` runs in the inner interpreter with the tracer off and returns the
    call (no arguments) and facts about the input; only the call is traced."""
    name: str
    kind: str
    entry_point: str
    settings: str
    description: str
    build: Callable[[], tuple[Callable[[], Any], dict]]


# -- the tracer (inner interpreter) ---------------------------------------------------------

class Tracer:
    def __init__(self, pkg_dir: str, src_root: str, checks: dict, target: str) -> None:
        import dis
        self.raise_varargs = dis.opmap["RAISE_VARARGS"]
        self.pkg_dir = pkg_dir
        self.src_root = src_root
        self.target = target
        self.lines: dict[str, dict[int, str]] = {}
        self.check_class: dict[str, str] = {}
        for c in checks["checks"]:
            self.check_class[c["id"]] = c.get("class_name", c["class"])
            for (a, z) in c["lines"]:
                for line in range(a, z + 1):
                    self.lines.setdefault(c["file"], {})[line] = c["id"]
        self.rel_cache: dict[str, str | None] = {}
        self.executed: dict[str, set[int]] = {}
        self.entered: list[str] = []
        self.raises: list[dict] = []
        self.raises_dropped = 0
        self.fired: list[str] = []
        self.target_exception: BaseException | None = None
        self.tool_id: int | None = None

    def rel(self, filename: str) -> str | None:
        if filename not in self.rel_cache:
            path = os.path.realpath(filename)
            self.rel_cache[filename] = (os.path.relpath(path, self.src_root).replace(os.sep, "/")
                                        if path.startswith(self.pkg_dir + os.sep) else None)
        return self.rel_cache[filename]

    def start(self) -> None:
        mon = sys.monitoring
        for tool_id in (4, 3):
            try:
                mon.use_tool_id(tool_id, "reach-input")
            except ValueError:
                continue
            self.tool_id = tool_id
            break
        if self.tool_id is None:
            raise RuntimeError("no free sys.monitoring tool id among 4 and 3")
        ev = mon.events
        mon.register_callback(self.tool_id, ev.RAISE, self.on_raise)
        mon.register_callback(self.tool_id, ev.LINE, self.on_line)
        mon.register_callback(self.tool_id, ev.PY_START, self.on_start)
        mon.set_events(self.tool_id, ev.RAISE | ev.LINE | ev.PY_START)

    def stop(self) -> None:
        if self.tool_id is None:
            return
        mon = sys.monitoring
        mon.set_events(self.tool_id, 0)
        for event in (mon.events.RAISE, mon.events.LINE, mon.events.PY_START):
            mon.register_callback(self.tool_id, event, None)
        mon.free_tool_id(self.tool_id)

    def on_start(self, code, offset):
        rel = self.rel(code.co_filename)
        if rel is not None:
            self.entered.append(f"{rel}:{code.co_firstlineno} {code.co_qualname}")
        return sys.monitoring.DISABLE

    def on_line(self, code, line):
        rel = self.rel(code.co_filename)
        if rel is not None:
            self.executed.setdefault(rel, set()).add(line)
        return sys.monitoring.DISABLE

    def on_raise(self, code, offset, exception) -> None:
        rel = self.rel(code.co_filename)
        if rel is None:
            return
        frame = sys._getframe(1)
        same_frame = frame.f_code is code
        line = frame.f_lineno if same_frame else None
        check = self.lines.get(rel, {}).get(line) if line is not None else None
        is_raise = code.co_code[offset] == self.raise_varargs
        fired = (same_frame and check is not None and is_raise
                 and type(exception).__name__ == self.check_class[check])
        if fired:
            if check not in self.fired:
                self.fired.append(check)
            if check == self.target and self.target_exception is None:
                self.target_exception = exception
        if len(self.raises) < MAX_RAISE_EVENTS:
            self.raises.append({"file": rel, "line": line, "function": code.co_qualname,
                                "exception": type(exception).__name__,
                                "instruction_is_raise_varargs": is_raise,
                                "check_of_line": check, "firing": check if fired else None})
        else:
            self.raises_dropped += 1


def describe_site(tb, pkg_dir: str, src_root: str, lines: dict[str, dict[int, str]]) -> dict | None:
    """The innermost frame of the traceback inside the package (as `site` of the recorder)."""
    inner = None
    while tb is not None:
        path = os.path.realpath(tb.tb_frame.f_code.co_filename)
        if path.startswith(pkg_dir + os.sep):
            inner = (path, tb.tb_frame.f_code, tb.tb_lineno)
        tb = tb.tb_next
    if inner is None:
        return None
    path, code, line = inner
    rel = os.path.relpath(path, src_root).replace(os.sep, "/")
    return {"file": rel, "function": code.co_qualname.replace(".<locals>", ""), "line": line,
            "check": lines.get(rel, {}).get(line)}


def package_frames(tb, pkg_dir: str, src_root: str) -> list[str]:
    out = []
    for frame in traceback.extract_tb(tb):
        path = os.path.realpath(frame.filename)
        if path.startswith(pkg_dir + os.sep):
            out.append(f"{os.path.relpath(path, src_root)}:{frame.lineno} {frame.name}")
    return out


def describe_value(value: Any) -> dict:
    out = {"type": f"{type(value).__module__}.{type(value).__qualname__}"}
    plaintext = getattr(value, "plaintext", None)
    if isinstance(plaintext, bytes):
        out["plaintext_length"] = len(plaintext)
        out["plaintext_sha256"] = sha256_bytes(plaintext)
    keys = getattr(value, "keys", None)
    if isinstance(keys, list):
        out["keys"] = len(keys)
    return out


def inner(script: Path, cases: list[Case], check_id: str, case_name: str, copy: Path) -> int:
    src = copy / "src"
    sys.path.insert(0, str(src))
    import joserfc  # noqa: E402  (from the copy)
    pkg_dir = os.path.realpath(os.path.dirname(joserfc.__file__))
    if pkg_dir != os.path.realpath(src / "joserfc"):
        raise SystemExit(f"joserfc was imported from {pkg_dir}, not from the copy")
    from joserfc.errors import JoseError
    checks = load_json(DEFS / "checks.json")
    case = next(c for c in cases if c.name == case_name)
    call, facts = case.build()

    import warnings
    tracer = Tracer(pkg_dir, os.path.realpath(src), checks, check_id)
    outcome: dict[str, Any]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        tracer.start()
        try:
            value = call()
        except BaseException as error:  # the exception that reaches the caller
            tracer.stop()
            outcome = {"raised": {
                "class": f"{type(error).__module__}.{type(error).__qualname__}",
                "message": str(error),
                "is_rejection_class": isinstance(error, JoseError),
                "site": describe_site(error.__traceback__, pkg_dir, os.path.realpath(src), tracer.lines),
                "package_frames": package_frames(error.__traceback__, pkg_dir, os.path.realpath(src)),
                "is_the_object_raised_at_the_check": (tracer.target_exception is not None
                                                      and error is tracer.target_exception),
                "cause": None if error.__cause__ is None else type(error.__cause__).__name__,
                "context": None if error.__context__ is None else type(error.__context__).__name__,
            }}
        else:
            tracer.stop()
            outcome = {"returned": describe_value(value)}
    check = next(c for c in checks["checks"] if c["id"] == check_id)
    raise_lines = sorted({line for (a, z) in check["lines"] for line in range(a, z + 1)})
    executed_in_check_file = sorted(tracer.executed.get(check["file"], set()))
    import cryptography  # noqa: E402  (the dependencies that build the tokens, from the environment)
    import Crypto  # noqa: E402
    record = {
        "case": case.name,
        "python": sys.version.split()[0],
        "prefix": from_deposit(sys.prefix),
        "base_prefix": sys.base_prefix,
        "dependency_files": {"cryptography": from_deposit(cryptography.__file__),
                             "Crypto (pycryptodome)": from_deposit(Crypto.__file__)},
        "flags": {"isolated": sys.flags.isolated, "dont_write_bytecode": sys.flags.dont_write_bytecode,
                  "hash_randomization": sys.flags.hash_randomization},
        "package_file": from_deposit(joserfc.__file__),
        "input_facts": facts,
        "outcome": outcome,
        "target_fired": check_id in tracer.fired,
        "target_raise_line_executed": any(line in executed_in_check_file for line in raise_lines),
        "checks_fired": tracer.fired,
        "raise_events": tracer.raises,
        "raise_events_not_kept": tracer.raises_dropped,
        "functions_entered": tracer.entered,
        "lines_executed": {rel: sorted(v) for rel, v in sorted(tracer.executed.items())},
        "warnings": [{"category": w.category.__name__, "message": str(w.message),
                      "file": from_deposit(w.filename), "line": w.lineno} for w in caught],
    }
    sys.stdout.write(json.dumps(record) + "\n")
    return 0


# -- the outer process ----------------------------------------------------------------------

def clone_commit() -> str:
    git = CLONE / ".git"
    head = (git / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head
    ref = head[5:]
    if (git / ref).is_file():
        return (git / ref).read_text(encoding="utf-8").strip()
    for line in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
        if line.endswith(" " + ref):
            return line.split()[0]
    raise SystemExit(f"the commit of {ref} is not found in {git}")


def toolkit_env() -> dict[str, str]:
    """`Context.env` of `reach/run.py` (lines 155-165)."""
    return {
        "PATH": f"{VENV_PYTHON.parent}:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def canonical(name: str) -> str:
    import re
    return re.sub(r"[-_.]+", "-", name).lower()


def environment_check(subject: dict) -> dict:
    """The interpreter and the packages of the environment, by the rules of
    `interpreter_problem` and `environment_problems` of `reach/run.py`."""
    import re
    problems = []
    probe = subprocess.run([str(VENV_PYTHON), "-I", "-B", "-c", INTERPRETER_PROBE], capture_output=True,
                           text=True, cwd="/", env=toolkit_env())
    reported = probe.stdout.strip()
    if reported != f"CPython {subject['python']}":
        problems.append(f"the interpreter is {reported or 'unknown'}, not CPython {subject['python']}")
    pins = {}
    for line in (DEFS / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"([A-Za-z0-9._-]+)==(\S+)", line)
        if m is None:
            problems.append(f"requirements.txt: `{line}` is no pin")
            continue
        pins[canonical(m.group(1))] = m.group(2)
    found = subprocess.run([str(VENV_PYTHON), "-I", "-B", "-c", PACKAGES_PROBE], capture_output=True,
                           text=True, cwd="/", env=toolkit_env())
    installed = {canonical(n): v for n, v in json.loads(found.stdout)}
    installed.pop("pip", None)
    for name, version in sorted(pins.items()):
        if installed.get(name) != version:
            problems.append(f"requirements.txt pins {name}=={version}; installed: {installed.get(name)}")
    for name in sorted(set(installed) - set(pins)):
        problems.append(f"{name}=={installed[name]} is installed and not in requirements.txt")
    return {"interpreter": reported, "packages": dict(sorted(installed.items())), "problems": problems}


def make_copy(subject: dict, checks: dict, blocks: dict) -> dict:
    """A fresh copy as `make_copy` of `reach/run.py` makes it, and its check
    against the digests of the definitions."""
    if COPY.exists():
        shutil.rmtree(COPY)
    COPY.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for item in subject["copy"]:
        src = CLONE / item
        if src.is_dir():
            shutil.copytree(src, COPY / item, ignore=ignore)
        else:
            (COPY / item).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, COPY / item)
    source_root = subject.get("source_root", ".")
    differ = []
    for rel, digest in checks["sha256"].items():
        path = COPY / (rel if source_root in (".", "") else f"{source_root.rstrip('/')}/{rel}")
        if not path.is_file() or sha256_file(path) != digest:
            differ.append(rel)
    for rel, digest in blocks["test_files_sha256"].items():
        if not (COPY / rel).is_file() or sha256_file(COPY / rel) != digest:
            differ.append(rel)
    if differ:
        raise SystemExit(f"copy {COPY}: {', '.join(differ)} differ from the definitions")
    return {"subject_files_match": len(checks["sha256"]), "test_files_match": len(blocks["test_files_sha256"])}


def tree_state(root: Path) -> dict:
    entries = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() or p.is_symlink()):
        entries.append(f"{path.relative_to(root).as_posix()}\0{sha256_file(path)}\n")
    pycache = sorted(p.relative_to(root).as_posix() for p in root.rglob("__pycache__"))
    return {"files": len(entries), "sha256": sha256_bytes("".join(entries).encode("utf-8")), "pycache": pycache}


def sample_row(row: int) -> dict:
    if sha256_file(SAMPLE) != SAMPLE_SHA256:
        raise SystemExit(f"{SAMPLE} is not the committed sample")
    with SAMPLE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[row - 1]


DETERMINISTIC = ("input_facts", "outcome", "target_fired", "target_raise_line_executed", "checks_fired",
                 "raise_events", "functions_entered", "lines_executed", "warnings")


def outer(script: Path, row: int, check_id: str, cases: list[Case]) -> int:
    started = utc_now()
    sample = sample_row(row)
    if sample["library"] != LIBRARY or sample["check"] != check_id:
        raise SystemExit(f"row {row} of the sample is {sample['library']} {sample['check']}, not {check_id}")
    subject = load_json(DEFS / "subject.json")
    checks = load_json(DEFS / "checks.json")
    blocks = load_json(DEFS / "blocks.json")
    check = next(c for c in checks["checks"] if c["id"] == check_id)
    commit = clone_commit()
    if commit != subject["commit"]:
        raise SystemExit(f"the clone is at {commit}, not at {subject['commit']}")
    environment = environment_check(subject)
    if environment["problems"]:
        raise SystemExit("environment: " + "; ".join(environment["problems"]))
    record: dict[str, Any] = {
        "library": LIBRARY, "row": row, "check": check_id, "file": check["file"], "lines": check["lines"],
        "class": check["class_name"], "function": check["function"],
        "script": from_deposit(script), "harness": from_deposit(__file__),
        "harness_sha256": sha256_file(Path(__file__)), "script_sha256": sha256_file(script),
        "started": started,
        "outer_python": sys.version.split()[0],
        "clone": {"path": from_deposit(CLONE), "commit": commit, "read_from": ".git/HEAD (no git command)"},
        "environment": {"python": from_deposit(VENV_PYTHON), **environment},
        "copy": from_deposit(COPY),
        "definitions_sha256": {from_deposit(p): sha256_file(p) for p in
                               (DEFS / "subject.json", DEFS / "checks.json", DEFS / "blocks.json",
                                DEFS / "requirements.txt", SAMPLE)},
        "sample_row": sample,
        "cases": [],
    }
    for case in cases:
        runs = []
        for index in range(1, RUNS_PER_CASE + 1):
            run: dict[str, Any] = {"run": index, "started": utc_now()}
            run["copy_check"] = make_copy(subject, checks, blocks)
            before = tree_state(COPY)
            command = [str(VENV_PYTHON), "-I", "-B", str(script), "--inner", case.name, str(COPY)]
            done = subprocess.run(command, capture_output=True, text=True, cwd=str(COPY), env=toolkit_env(),
                                  timeout=TIMEOUT_SECONDS)
            after = tree_state(COPY)
            run["ended"] = utc_now()
            run["command"] = [from_deposit(VENV_PYTHON), "-I", "-B", from_deposit(script), "--inner", case.name,
                              from_deposit(COPY)]
            run["returncode"] = done.returncode
            run["stderr_tail"] = done.stderr[-2000:]
            run["copy_before"] = before
            run["copy_after"] = after
            run["copy_unchanged"] = before == after and not after["pycache"]
            lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
            run["inner"] = json.loads(lines[-1]) if done.returncode == 0 and lines else None
            runs.append(run)
        inners = [r["inner"] for r in runs]
        identical = all(i is not None for i in inners) and all(
            {k: i[k] for k in DETERMINISTIC} == {k: inners[0][k] for k in DETERMINISTIC} for i in inners)
        record["cases"].append({"name": case.name, "kind": case.kind, "entry_point": case.entry_point,
                                "settings": case.settings, "input": case.description,
                                "runs": runs, "runs_identical": identical})
    inputs = [c for c in record["cases"] if c["kind"] == "input"]
    record["fired_by_an_input"] = any(
        all(r["inner"] is not None and r["inner"]["target_fired"] for r in c["runs"]) for c in inputs)
    record["all_runs_clean"] = all(r["returncode"] == 0 and r["copy_unchanged"]
                                   for c in record["cases"] for r in c["runs"])
    record["ended"] = utc_now()
    out = script.with_suffix(".json")
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in record["cases"]:
        last = c["runs"][-1]["inner"]
        result = None if last is None else last["outcome"]
        print(f"{row} {c['name']} ({c['kind']}): fired={None if last is None else last['target_fired']} "
              f"identical={c['runs_identical']} outcome={json.dumps(result)[:300]}")
    print(f"{row}: fired by an input: {record['fired_by_an_input']}; clean: {record['all_runs_clean']}; "
          f"record {from_deposit(out)}")
    return 0


def main(script_file: str, row: int, check_id: str, cases: list[Case]) -> int:
    script = Path(script_file).resolve()
    if len(sys.argv) >= 4 and sys.argv[1] == "--inner":
        return inner(script, cases, check_id, sys.argv[2], Path(sys.argv[3]))
    return outer(script, row, check_id, cases)

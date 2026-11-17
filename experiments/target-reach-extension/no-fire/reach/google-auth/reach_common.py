"""Shared code of 1.py to 5.py, which run the inputs for the 5 sampled checks
of google-auth (rows 1 to 5 of `../../sample.csv`; `../../../PROTOCOL.md`,
section 4.4). Each of those scripts names its row and check, the inputs it
runs through an entry point and a control, and calls `main`.

Parent mode, `python3 -I -B <n>.py` (CPython 3.12.3), from any folder:

1. checks that row <n> of `sample.csv` is the check that the script names,
   and reads the check from `T/subjects/google-auth/checks.json`;
2. makes a fresh copy of the release as the toolkit's `make_copy` makes it
   (`T/reach/run.py`, lines 310-330): the paths of `copy` in `subject.json`,
   taken from the clone without `__pycache__`, `*.pyc` and `.pytest_cache`,
   into `../../../work/reach/google-auth/copy`, removed first; then checks the
   SHA-256 of every subject file against `checks.json`, as `make_copy_check`
   does;
3. runs the same script again in child mode in the environment of the first
   study (`T/work/venvs/google-auth/bin/python`, CPython 3.12.3), with the
   environment variables that the toolkit gives its pytest calls
   (`T/reach/run.py`, lines 155-165);
4. checks the digests of the copy again, and writes `<n>.json` beside the
   script.

Child mode imports `google.auth.jwt` and `google.auth._jwt_async` from the
copy, builds the artifacts (tokens signed with the key files of the copy's
`tests/data/` through the `cryptography` package of the environment, never
through a function of google-auth) and runs each input under
`sys.monitoring`, tool id 4 or 3 as the toolkit's recorder claims them:

- LINE events at the lines of the raise statements of the sampled check: the
  tracer of section 4.4;
- RAISE events whose instruction is `RAISE_VARARGS`, on a line of a raise
  statement of any check of `checks.json`, with an exception whose class has
  the check's bare class name: a firing, as the recorder defines it
  (`T/reach/recorder.py`, lines 32-36 and 237-270); every other `RAISE_VARARGS` in the
  package is kept as a raise;
- PY_START events of code in the package directory: the functions entered.

It records the exception that reaches the caller, with its raise site, the
innermost frame of its traceback in the package directory, as the recorder's
`site` reads it (`T/reach/recorder.py`, lines 194-210). After the inputs it
runs the control of the script: the function of the check called directly
with a value that the check rejects. The control is no input through an entry
point; it shows that the tracer records the raise statement when it executes.
"""

from __future__ import annotations

import base64
import csv
import dis
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent             # no-fire/reach/google-auth
X = HERE.parents[2]                                # experiments/target-reach-extension
T = X.parent / "target-reach"
SUBJECT_PATH = T / "subjects/google-auth/subject.json"
CHECKS_PATH = T / "subjects/google-auth/checks.json"
CLONE = T / "work/src/google-auth/packages/google-auth"
VENV_PYTHON = T / "work/venvs/google-auth/bin/python"
SAMPLE = X / "no-fire/sample.csv"
WORK = X / "work/reach/google-auth"
COPY = WORK / "copy"
LIBRARY = "google-auth"
ENTRY_POINTS = {
    "google.auth.jwt.decode": "google/auth/jwt.py:234",
    "google.auth._jwt_async.decode": "google/auth/_jwt_async.py:71",
}
RAISE_VARARGS = dis.opmap["RAISE_VARARGS"]


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# -- parent mode ---------------------------------------------------------------------

def sample_row(row: int) -> dict:
    with SAMPLE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[row - 1]


def make_copy(subject: dict, checks: dict) -> int:
    """The toolkit's make_copy and make_copy_check, for this copy. Returns the
    number of subject files whose digest was checked."""
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
    return check_copy(checks)


def check_copy(checks: dict) -> int:
    for rel, digest in checks["sha256"].items():
        if sha256(COPY / rel) != digest:
            raise SystemExit(f"copy {COPY}: {rel} differs from the clone")
    return len(checks["sha256"])


def clone_head() -> str:
    env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp"), "GIT_OPTIONAL_LOCKS": "0"}
    proc = subprocess.run(["git", "-C", str(CLONE), "rev-parse", "HEAD"], capture_output=True,
                          text=True, env=env, check=True)
    return proc.stdout.strip()


def toolkit_env() -> dict[str, str]:
    """`Context.env` of T/reach/run.py (lines 155-165)."""
    return {
        "PATH": f"{VENV_PYTHON.parent}:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def parent(script: Path, row: int, check_id: str) -> int:
    started = utc()
    srow = sample_row(row)
    if srow["library"] != LIBRARY or srow["check"] != check_id:
        raise SystemExit(f"row {row} of sample.csv is {srow['library']} {srow['check']}, not {check_id}")
    subject = load_json(SUBJECT_PATH)
    checks = load_json(CHECKS_PATH)
    check = next(c for c in checks["checks"] if c["id"] == check_id)
    first_lines = ";".join(str(a) for a, _ in check["lines"])
    if check["file"] != srow["file"] or first_lines != srow["line"]:
        raise SystemExit(f"check {check_id}: checks.json and sample.csv disagree")
    head = clone_head()
    if head != subject["commit"]:
        raise SystemExit(f"clone at {head}, not at {subject['commit']}")
    checked = make_copy(subject, checks)
    out = WORK / f"{row}.child.json"
    log = WORK / f"{row}.child.log"
    for old in (out, log):
        if old.exists():
            old.unlink()
    cmd = [str(VENV_PYTHON), "-I", "-B", str(script), "--child", str(COPY), str(out)]
    child_started = utc()
    proc = subprocess.run(cmd, cwd=WORK, env=toolkit_env(), capture_output=True, text=True, timeout=900)
    child_ended = utc()
    log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0 or not out.exists():
        print(proc.stdout + proc.stderr)
        raise SystemExit(f"child ended with {proc.returncode}; log {log}")
    checked_after = check_copy(checks)
    child = load_json(out)
    result = {
        "library": LIBRARY,
        "row": row,
        "check": check_id,
        "check_file": check["file"],
        "check_function": check["function"],
        "check_class": check["class"],
        "check_template": check["template"],
        "raise_lines": check["lines"],
        "started": started,
        "child_started": child_started,
        "child_ended": child_ended,
        "parent_python": platform.python_version(),
        "clone": str(CLONE.relative_to(X.parent.parent)),
        "clone_head": head,
        "copy": str(COPY.relative_to(X)),
        "subject_files_checked_before": checked,
        "subject_files_checked_after": checked_after,
        "checks_json_sha256": sha256(CHECKS_PATH),
        "command": ["T/work/venvs/google-auth/bin/python", "-I", "-B", script.name, "--child",
                    "work/reach/google-auth/copy", f"work/reach/google-auth/{row}.child.json"],
        "child_returncode": proc.returncode,
        **child,
    }
    reached = [i["label"] for i in child["inputs"] if i["raise_line_executed"] or check_id in i["fired"]]
    result["inputs_that_reach_the_check"] = reached
    result["functions_entered_by_the_inputs"] = sorted(
        {f for i in child["inputs"] for f in i["entered"]})
    result["check_function_entered_by_an_input"] = any(i["check_function_entered"] for i in child["inputs"])
    path = script.with_suffix(".json")
    path.write_text(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"row {row} {check_id}: {len(child['inputs'])} inputs; "
          f"reach the check: {len(reached)}; check function entered: "
          f"{result['check_function_entered_by_an_input']}; control fired: "
          f"{child['control']['fired_the_check'] if child['control'] else None}; written {path.name}")
    for i in child["inputs"] + ([dict(child["control"], label="control: " + child["control"]["label"])]
                                if child["control"] else []):
        print(f"  {i['label']}: {outcome(i)}; fired {i['fired']}")
    return 0


def outcome(record: dict) -> str:
    """1 line: what reaches the caller, and where it was raised."""
    exc = record["exception"]
    if exc is None:
        return f"returned {record['returned']}"
    site = exc["site"]
    if site is None:
        return f"{exc['class']}, raised outside the package"
    where = site["check"] or site["kind"]
    return f"{exc['class']} at {site['file']}:{site['line']} ({where})"


# -- child mode: the artifacts --------------------------------------------------------

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def dumps(obj) -> bytes:
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


class Artifacts:
    """Keys, certificates and tokens. Keys and certificates are the files of
    the copy's tests/data/; signing uses the `cryptography` package of the
    environment directly."""

    def __init__(self, copy: Path) -> None:
        from cryptography.hazmat.primitives import serialization
        data = copy / "tests" / "data"
        self.data = data
        self.serialization = serialization

        def text(name: str) -> str:
            return (data / name).read_text(encoding="utf-8")

        self.rsa_private_pem = text("privatekey.pem")
        self.rsa_key = serialization.load_pem_private_key(self.rsa_private_pem.encode(), password=None)
        self.rsa_cert = text("public_cert.pem")
        self.rsa_public = text("privatekey.pub")
        self.other_cert = text("other_cert.pem")
        self.es256_key = serialization.load_pem_private_key(text("es256_privatekey.pem").encode(), None)
        self.es256_cert = text("es256_public_cert.pem")
        self.es256_public = text("es256_publickey.pem")
        self.es384_key = serialization.load_pem_private_key(text("es384_privatekey.pem").encode(), None)
        self.es384_public = text("es384_publickey.pem")

    def claims(self, **extra) -> dict:
        now = int(time.time())
        payload = {"iss": "issuer@example.com", "aud": "audience", "iat": now, "exp": now + 300}
        payload.update(extra)
        return {k: v for k, v in payload.items() if v is not None}

    def sign(self, alg: str, signing_input: bytes) -> bytes:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec, padding
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
        if alg == "RS256":
            return self.rsa_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        key, size, digest = {"ES256": (self.es256_key, 32, hashes.SHA256()),
                             "ES384": (self.es384_key, 48, hashes.SHA384())}[alg]
        r, s = decode_dss_signature(key.sign(signing_input, ec.ECDSA(digest)))
        return r.to_bytes(size, "big") + s.to_bytes(size, "big")

    def token(self, alg: str = "RS256", payload: dict | None = None, kid=None, header: dict | None = None,
              sign_as: str | None = None, signature: bytes | None = None) -> str:
        head = {"alg": alg, "typ": "JWT"}
        if kid is not None:
            head["kid"] = kid
        if header:
            head.update(header)
        body = self.claims() if payload is None else payload
        signing_input = f"{b64url(dumps(head))}.{b64url(dumps(body))}".encode("ascii")
        sig = signature if signature is not None else self.sign(sign_as or alg, signing_input)
        return f"{signing_input.decode('ascii')}.{b64url(sig)}"

    def pkcs8_private_key_pem(self, trailing: bytes = b"") -> str:
        """The RSA key of tests/data/privatekey.pem as PKCS #8, with `trailing`
        bytes after the DER structure, in a PEM block BEGIN PRIVATE KEY."""
        der = self.rsa_key.private_bytes(self.serialization.Encoding.DER,
                                         self.serialization.PrivateFormat.PKCS8,
                                         self.serialization.NoEncryption()) + trailing
        body = base64.encodebytes(der).decode("ascii")
        return f"-----BEGIN PRIVATE KEY-----\n{body}-----END PRIVATE KEY-----\n"


class Input:
    def __init__(self, label: str, entry: str, func, args: tuple, kwargs: dict, artifact: str,
                 settings: str = "") -> None:
        self.label, self.entry, self.func = label, entry, func
        self.args, self.kwargs = args, kwargs
        self.artifact, self.settings = artifact, settings


def census(art: Artifacts, jwt, jwt_async) -> list[Input]:
    """Inputs that give every condition of decode in google/auth/jwt.py (lines
    260-330), and of the functions of that file that it calls (lines 121-171
    and 191-231), both of its outcomes, except the true outcome of line 273,
    which this environment does not admit (`es` is imported, lines 63-75),
    through both functions named decode."""
    d, a = "google.auth.jwt.decode", "google.auth._jwt_async.decode"
    now = int(time.time())
    good = art.token()
    h, p, s = good.split(".")
    bad_sig = h + "." + p + "." + b64url(b"0" * 256)
    not_utf8 = b64url(bytes([0xFF, 0xFE]))
    array = b64url(b"[]")
    string = b64url(b'"x"')
    return [
        Input("C01 valid RS256, certificate", d, jwt.decode, (good,), {"certs": art.rsa_cert},
              "RS256 token signed with tests/data/privatekey.pem", "certs: tests/data/public_cert.pem (str)"),
        Input("C02 valid RS256 as bytes, kid in a mapping", d, jwt.decode, (art.token(kid="1").encode(),),
              {"certs": {"1": art.rsa_cert.encode()}}, "RS256 token with kid 1, as bytes",
              "certs: {'1': public_cert.pem (bytes)}"),
        Input("C03 valid RS256 without kid, 2 certificates", d, jwt.decode, (good,),
              {"certs": {"a": art.other_cert, "b": art.rsa_cert}}, "RS256 token without kid",
              "certs: {'a': other_cert.pem, 'b': public_cert.pem}"),
        Input("C04 valid RS256, RSA public key", d, jwt.decode, (good,), {"certs": art.rsa_public},
              "RS256 token", "certs: tests/data/privatekey.pub (BEGIN RSA PUBLIC KEY)"),
        Input("C05 valid ES256, certificate", d, jwt.decode, (art.token("ES256"),),
              {"certs": art.es256_cert}, "ES256 token signed with es256_privatekey.pem",
              "certs: es256_public_cert.pem"),
        Input("C06 valid ES384, public key", d, jwt.decode, (art.token("ES384"),),
              {"certs": art.es384_public}, "ES384 token signed with es384_privatekey.pem",
              "certs: es384_publickey.pem"),
        Input("C07 verify=False", d, jwt.decode, (art.token(signature=b"x"),), {"verify": False},
              "RS256 token with a wrong signature", "verify=False"),
        Input("C08 2 segments", d, jwt.decode, (h + "." + p,), {"certs": art.rsa_cert},
              "header.payload without signature", "certs: public_cert.pem"),
        Input("C09 header not base64url", d, jwt.decode, ("A." + p + "." + s,), {"certs": art.rsa_cert},
              "header segment 'A'", "certs: public_cert.pem"),
        Input("C10 header not UTF-8", d, jwt.decode, (not_utf8 + "." + p + "." + s,),
              {"certs": art.rsa_cert}, "header segment of bytes ff fe", "certs: public_cert.pem"),
        Input("C11 header a JSON array", d, jwt.decode, (array + "." + p + "." + s,),
              {"certs": art.rsa_cert}, "header []", "certs: public_cert.pem"),
        Input("C12 payload a JSON string", d, jwt.decode, (h + "." + string + "." + s,),
              {"certs": art.rsa_cert}, "payload \"x\"", "certs: public_cert.pem"),
        Input("C13 alg HS256", d, jwt.decode, (art.token("HS256", signature=b"x"),),
              {"certs": art.rsa_cert}, "header alg HS256", "certs: public_cert.pem"),
        Input("C14 alg a JSON array", d, jwt.decode, (art.token(["RS256"], signature=b"x"),),
              {"certs": art.rsa_cert}, "header alg [\"RS256\"]", "certs: public_cert.pem"),
        Input("C15 kid not in the mapping", d, jwt.decode, (art.token(kid="2"),),
              {"certs": {"1": art.rsa_cert}}, "RS256 token with kid 2", "certs: {'1': public_cert.pem}"),
        Input("C16 no certs", d, jwt.decode, (good,), {}, "RS256 token", "none (certs=None)"),
        Input("C17 RS256 token, EC public key", d, jwt.decode, (good,), {"certs": art.es256_public},
              "RS256 token", "certs: es256_publickey.pem"),
        Input("C18 ES256 token, RSA certificate", d, jwt.decode, (art.token("ES256"),),
              {"certs": art.rsa_cert}, "ES256 token", "certs: public_cert.pem"),
        Input("C19 RS256, wrong signature", d, jwt.decode, (bad_sig,), {"certs": art.rsa_cert},
              "RS256 token with a signature of 256 bytes 0x30", "certs: public_cert.pem"),
        Input("C20 ES256, signature of wrong length", d, jwt.decode,
              (art.token("ES256", signature=b"\x01" * 10),), {"certs": art.es256_public},
              "ES256 token with a signature of 10 bytes", "certs: es256_publickey.pem"),
        Input("C21 certs not PEM", d, jwt.decode, (good,), {"certs": "not a key"}, "RS256 token",
              "certs: 'not a key'"),
        Input("C22 no iat", d, jwt.decode, (art.token(payload=art.claims(iat=None)),),
              {"certs": art.rsa_cert}, "RS256 token without iat", "certs: public_cert.pem"),
        Input("C23 iat in the future", d, jwt.decode,
              (art.token(payload=art.claims(iat=now + 3600, exp=now + 7200)),), {"certs": art.rsa_cert},
              "RS256 token issued 3600 s ahead", "certs: public_cert.pem"),
        Input("C24 expired", d, jwt.decode,
              (art.token(payload=art.claims(iat=now - 7200, exp=now - 3600)),), {"certs": art.rsa_cert},
              "RS256 token expired 3600 s ago", "certs: public_cert.pem"),
        Input("C25 expired within the clock skew", d, jwt.decode,
              (art.token(payload=art.claims(iat=now - 700, exp=now - 100)),),
              {"certs": art.rsa_cert, "clock_skew_in_seconds": 600}, "RS256 token expired 100 s ago",
              "certs: public_cert.pem; clock_skew_in_seconds=600"),
        Input("C26 wrong audience", d, jwt.decode, (good,), {"certs": art.rsa_cert, "audience": "other"},
              "RS256 token with aud 'audience'", "certs: public_cert.pem; audience='other'"),
        Input("C27 audience in a list", d, jwt.decode, (good,),
              {"certs": art.rsa_cert, "audience": ["x", "audience"]}, "RS256 token with aud 'audience'",
              "certs: public_cert.pem; audience=['x', 'audience']"),
        Input("C28 async entry point, valid", a, jwt_async.decode, (good,), {"certs": art.rsa_cert},
              "RS256 token", "certs: public_cert.pem"),
        Input("C29 async entry point, wrong audience", a, jwt_async.decode, (good,),
              {"certs": art.rsa_cert, "audience": "other"}, "RS256 token",
              "certs: public_cert.pem; audience='other'"),
    ]


# -- child mode: the tracer -----------------------------------------------------------

class Tracer:
    def __init__(self, copy: Path, checks: dict, watch_file: str, watch_lines: set[int],
                 check_function: tuple[str, str]) -> None:
        self.pkg_dir = os.path.realpath(copy / "google")
        self.src_root = os.path.realpath(copy)
        self.watch_file, self.watch_lines = watch_file, watch_lines
        self.check_function = check_function
        self.lines: dict[str, dict[int, str]] = {}
        self.check_class: dict[str, str] = {}
        for c in checks["checks"]:
            self.check_class[c["id"]] = c.get("class_name", c["class"])
            for a, z in c["lines"]:
                for line in range(a, z + 1):
                    self.lines.setdefault(c["file"], {})[line] = c["id"]
        self.other_lines: dict[str, set[int]] = {}
        for o in checks["other_raises"]:
            for line in range(o["line"], o["end_line"] + 1):
                self.other_lines.setdefault(o["file"], set()).add(line)
        self.rels: dict[str, str | None] = {}
        self.active = False
        self.reset()
        mon = sys.monitoring
        self.tool = None
        for tool in (4, 3):
            try:
                mon.use_tool_id(tool, "reach-reading")
            except ValueError:
                continue
            self.tool = tool
            break
        if self.tool is None:
            raise SystemExit("no free sys.monitoring tool id")
        ev = mon.events
        mon.register_callback(self.tool, ev.LINE, self.on_line)
        mon.register_callback(self.tool, ev.PY_START, self.on_start)
        mon.register_callback(self.tool, ev.RAISE, self.on_raise)
        mon.set_events(self.tool, ev.LINE | ev.PY_START | ev.RAISE)

    def close(self) -> None:
        mon = sys.monitoring
        mon.set_events(self.tool, 0)
        for e in (mon.events.LINE, mon.events.PY_START, mon.events.RAISE):
            mon.register_callback(self.tool, e, None)
        mon.free_tool_id(self.tool)

    def reset(self) -> None:
        self.line_hits: dict[int, int] = {}
        self.entered: set[str] = set()
        self.fired: list[str] = []
        self.raises: list[dict] = []
        self.check_function_entered = False

    def rel(self, filename: str) -> str | None:
        if filename not in self.rels:
            path = os.path.realpath(filename)
            self.rels[filename] = (os.path.relpath(path, self.src_root).replace(os.sep, "/")
                                   if path.startswith(self.pkg_dir + os.sep) else None)
        return self.rels[filename]

    def on_line(self, code, line):
        if not self.active:
            return sys.monitoring.DISABLE
        if self.rel(code.co_filename) == self.watch_file and line in self.watch_lines:
            self.line_hits[line] = self.line_hits.get(line, 0) + 1
            return None
        return sys.monitoring.DISABLE

    def on_start(self, code, offset):
        if not self.active:
            return sys.monitoring.DISABLE
        rel = self.rel(code.co_filename)
        if rel is not None:
            qual = code.co_qualname.replace(".<locals>", "")
            self.entered.add(f"{rel}:{qual} (line {code.co_firstlineno})")
            if (rel, qual) == self.check_function:
                self.check_function_entered = True
        return sys.monitoring.DISABLE

    def on_raise(self, code, offset, exception):
        if not self.active:
            return None
        rel = self.rel(code.co_filename)
        if rel is None:
            return None
        frame = sys._getframe(1)
        if frame.f_code is not code or code.co_code[offset] != RAISE_VARARGS:
            return None
        line = frame.f_lineno
        check = self.lines.get(rel, {}).get(line)
        if check is not None and type(exception).__name__ == self.check_class[check]:
            if check not in self.fired:
                self.fired.append(check)
        self.raises.append({"file": rel, "line": line, "class": type(exception).__name__,
                            "check": check if check is not None
                            and type(exception).__name__ == self.check_class[check] else None})
        return None

    def site(self, tb) -> dict | None:
        inner = None
        while tb is not None:
            path = os.path.realpath(tb.tb_frame.f_code.co_filename)
            if path.startswith(self.pkg_dir + os.sep):
                inner = (path, tb.tb_frame.f_code, tb.tb_lineno)
            tb = tb.tb_next
        if inner is None:
            return None
        path, code, line = inner
        rel = os.path.relpath(path, self.src_root).replace(os.sep, "/")
        check = self.lines.get(rel, {}).get(line)
        return {"file": rel, "function": code.co_qualname.replace(".<locals>", ""), "line": line,
                "check": check,
                "kind": "check" if check else ("other raise" if line in self.other_lines.get(rel, set())
                                               else "outside checks")}

    def run(self, func, args: tuple, kwargs: dict) -> dict:
        self.reset()
        sys.monitoring.restart_events()
        exc = None
        returned = None
        self.active = True
        try:
            value = func(*args, **kwargs)
            returned = type(value).__name__
        except Exception as e:  # noqa: BLE001 - the exception is the record
            exc = e
        finally:
            self.active = False
        record = {
            "raise_line_executed": bool(self.line_hits),
            "raise_line_hits": {str(k): v for k, v in sorted(self.line_hits.items())},
            "check_function_entered": self.check_function_entered,
            "fired": list(self.fired),
            "raises_in_package": self.raises,
            "entered": sorted(self.entered),
            "returned": returned,
            "exception": None,
        }
        if exc is not None:
            mro = [f"{c.__module__}.{c.__qualname__}" for c in type(exc).__mro__]
            message = str(exc)
            record["exception"] = {
                "class": f"{type(exc).__module__}.{type(exc).__qualname__}",
                "is_ValueError": isinstance(exc, ValueError),
                "mro": mro,
                "message": message if len(message) <= 160 else message[:157] + "...",
                "site": self.site(exc.__traceback__),
                "traceback_tail": [f"{os.path.relpath(f.filename, self.src_root)}:{f.lineno}"
                                   for f in traceback.extract_tb(exc.__traceback__)][-4:],
            }
        return record


def child(copy: Path, out: Path, row: int, check_id: str, inputs_fn, control_fn) -> int:
    sys.path.insert(0, str(copy))
    import google.auth
    import google.auth._jwt_async as jwt_async
    import google.auth.jwt as jwt
    for mod in (google.auth, jwt, jwt_async):
        if not os.path.realpath(mod.__file__).startswith(os.path.realpath(copy) + os.sep):
            raise SystemExit(f"{mod.__name__} imported from {mod.__file__}, not from the copy")
    checks = load_json(CHECKS_PATH)
    check = next(c for c in checks["checks"] if c["id"] == check_id)
    watch = {line for a, z in check["lines"] for line in range(a, z + 1)}
    art = Artifacts(copy)
    own = inputs_fn(art, jwt, jwt_async)
    inputs = own + census(art, jwt, jwt_async)
    tracer = Tracer(copy, checks, check["file"], watch, (check["file"], check["function"]))
    records = []
    try:
        for item in inputs:
            rec = tracer.run(item.func, item.args, item.kwargs)
            records.append({"label": item.label, "entry_point": item.entry,
                            "entry_point_source": ENTRY_POINTS[item.entry],
                            "artifact": item.artifact, "settings": item.settings,
                            "targeted": any(item is o for o in own), **rec})
        modules = sorted(m for m in sys.modules if m == "google" or m.startswith("google."))
        control = None
        if control_fn is not None:
            label, func, args, kwargs = control_fn(art)
            rec = tracer.run(func, args, kwargs)
            control = {"label": label, "fired_the_check": check_id in rec["fired"], **rec}
    finally:
        tracer.close()
    doc = {
        "child_python": platform.python_version(),
        "child_executable": "T/work/venvs/google-auth/bin/python",
        "google_auth_file": os.path.relpath(google.auth.__file__, copy),
        "inputs": records,
        "control": control,
        "google_modules_loaded_after_the_inputs": modules,
    }
    out.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


def main(script: str, row: int, check_id: str, inputs_fn, control_fn) -> int:
    path = Path(script).resolve()
    if len(sys.argv) >= 2 and sys.argv[1] == "--child":
        return child(Path(sys.argv[2]), Path(sys.argv[3]), row, check_id, inputs_fn, control_fn)
    return parent(path, row, check_id)

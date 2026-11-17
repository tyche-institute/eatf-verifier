#!/usr/bin/env python3
"""Row 14 of no-fire/sample.csv: authlib, jose.rfc7517.base_key.Key.check_key_op#1.

    <venv>/bin/python -I -B 14.py [--clone DIR] [--work DIR] [--toolkit DIR] [--only NAME ...]

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

The check: `authlib/jose/rfc7517/base_key.py`, the 2 statements
`raise InvalidUseError()` of `Key.check_key_op`, at line 85 (the operation is
"sign" or "verify", line 83, and the member "use" of the key is not "sig",
line 84) and at line 88 (the operation is "decrypt", "encrypt", "wrapKey" or
"unwrapKey", line 86, and "use" is not "enc", line 87); both need a "use"
member that is not empty (lines 81-82). `OctKey.get_op_key`
(`authlib/jose/rfc7518/oct_key.py`, line 59) and `AsymmetricKey.get_op_key`
(`authlib/jose/rfc7517/asymmetric_key.py`, line 42) call it first.

Inputs:

- `a`: `JsonWebSignature().deserialize_compact(token, jwk)`, with a compact
  JWS, protected header {"alg":"HS256"}, signed with HMAC-SHA-256 under a
  32-byte secret, and as key the JWK {"kty":"oct","k":<that secret>,"use":"enc"}.
  `HMACAlgorithm.verify` calls `key.get_op_key("verify")`
  (`authlib/jose/rfc7518/jws_algs.py`, line 66), reached from
  `authlib/jose/rfc7515/jws.py`, line 113; the raise expected is line 85.
- `b`: `JsonWebEncryption().deserialize_compact(token, jwk)`, with a compact
  JWE, protected header {"alg":"dir","enc":"A128GCM"}, the payload encrypted
  with AES-128-GCM under a 16-byte key, and as key the JWK
  {"kty":"oct","k":<that key>,"use":"sig"}. `DirectAlgorithm.unwrap` calls
  `key.get_op_key("decrypt")` (`authlib/jose/rfc7518/jwe_algs.py`, line 42),
  reached from `authlib/jose/rfc7516/jwe.py`, line 499; the raise expected is
  line 88.
- `c`: `JsonWebEncryption().deserialize_compact(token, jwk)`, with a compact
  JWE, protected header {"alg":"ECDH-ES","enc":"A128GCM","epk":{...,"use":"sig"}}:
  the ephemeral public key of the sender, as the received token carries it,
  holds "use":"sig". The token is encrypted for the recipient's P-256 key by
  ECDH-ES in the direct key agreement mode (RFC 7518, section 4.6, which the
  package cites at `authlib/jose/rfc7518/jwe_algs.py`, line 196), with the
  derivation of `ECDHESAlgorithm` (same file, lines 223-253), and the
  key given is the recipient's private JWK {"kty":"EC","crv":"P-256","x","y","d"},
  with no "use". `ECDHESAlgorithm.unwrap` imports the "epk" of the header and
  calls `epk.get_op_key("wrapKey")` (`authlib/jose/rfc7518/jwe_algs.py`, lines
  302-303); the raise expected is line 88.

The keys are settings of the caller (the key has no default); the EC keys are
fixed scalars, so that each run builds the same tokens. No other setting
differs from the default.
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

ROW = 14
CHECK = "jose.rfc7517.base_key.Key.check_key_op#1"
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


def compact_jws(header: dict, payload: bytes, key: bytes) -> str:
    """A compact JWS signed with HMAC-SHA-256, built with the standard library only."""
    import hmac
    signing_input = f"{b64json(header)}.{b64url(payload)}"
    signature = hmac.new(key, signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{b64url(signature)}"


def compact_jwe_gcm(header: dict, plaintext: bytes, cek: bytes, iv: bytes, ek: bytes = b"") -> str:
    """A compact JWE whose content is encrypted with AES-GCM under `cek` (cryptography only)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    protected = b64json(header)
    sealed = AESGCM(cek).encrypt(iv, plaintext, protected.encode("ascii"))
    ciphertext, tag = sealed[:-16], sealed[-16:]
    return ".".join([protected, b64url(ek), b64url(iv), b64url(ciphertext), b64url(tag)])


P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def p256_key(label: str):
    """A fixed P-256 private key whose scalar is derived from `label`."""
    from cryptography.hazmat.primitives.asymmetric import ec
    scalar = int.from_bytes(hashlib.sha256(label.encode("ascii")).digest(), "big") % (P256_ORDER - 1) + 1
    return ec.derive_private_key(scalar, ec.SECP256R1())


def p256_jwk(private_key, with_private: bool) -> dict:
    numbers = private_key.private_numbers()
    jwk = {"kty": "EC", "crv": "P-256",
           "x": b64url(numbers.public_numbers.x.to_bytes(32, "big")),
           "y": b64url(numbers.public_numbers.y.to_bytes(32, "big"))}
    if with_private:
        jwk["d"] = b64url(numbers.private_value.to_bytes(32, "big"))
    return jwk


def concat_kdf(shared: bytes, algorithm_id: str, bits: int) -> bytes:
    """The Concat KDF of ECDH-ES (RFC 7518, section 4.6), with "apu" and "apv" absent."""
    import struct
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.concatkdf import ConcatKDFHash
    alg_id = algorithm_id.encode("ascii")
    other = (struct.pack(">I", len(alg_id)) + alg_id + struct.pack(">I", 0) + struct.pack(">I", 0)
             + struct.pack(">I", bits))
    return ConcatKDFHash(algorithm=hashes.SHA256(), length=bits // 8, otherinfo=other).derive(shared)


HMAC_KEY = b"row 14 shared secret, 32 bytes!!"
DIR_KEY = b"row 14 dir key!!"
IV = b"row-14-iv-12"
PAYLOAD = b'{"sub":"row-14","iat":1700000000}'


def input_a():
    from authlib.jose import JsonWebSignature
    header = {"alg": "HS256"}
    token = compact_jws(header, PAYLOAD, HMAC_KEY)
    jwk = {"kty": "oct", "k": b64url(HMAC_KEY), "use": "enc"}
    return {
        "entry_point": "authlib.jose.rfc7515.jws.JsonWebSignature.deserialize_compact",
        "settings": 'JsonWebSignature() (the defaults); key: the JWK {"kty":"oct","k":<32-byte secret>,"use":"enc"} (a dict)',
        "input": 'compact JWS, protected header {"alg":"HS256"}, valid HS256 signature under the secret of the key',
        "token": token,
        "call": lambda: JsonWebSignature().deserialize_compact(token, jwk),
    }


def input_b():
    from authlib.jose import JsonWebEncryption
    header = {"alg": "dir", "enc": "A128GCM"}
    token = compact_jwe_gcm(header, PAYLOAD, DIR_KEY, IV)
    jwk = {"kty": "oct", "k": b64url(DIR_KEY), "use": "sig"}
    return {
        "entry_point": "authlib.jose.rfc7516.jwe.JsonWebEncryption.deserialize_compact",
        "settings": 'JsonWebEncryption() (the defaults); key: the JWK {"kty":"oct","k":<16-byte key>,"use":"sig"} (a dict)',
        "input": 'compact JWE, protected header {"alg":"dir","enc":"A128GCM"}, payload encrypted with AES-128-GCM '
                 'under the key',
        "token": token,
        "call": lambda: JsonWebEncryption().deserialize_compact(token, jwk),
    }


def input_c():
    from cryptography.hazmat.primitives.asymmetric import ec
    from authlib.jose import JsonWebEncryption
    recipient = p256_key("row 14 recipient")
    ephemeral = p256_key("row 14 ephemeral")
    epk = {**p256_jwk(ephemeral, with_private=False), "use": "sig"}
    header = {"alg": "ECDH-ES", "enc": "A128GCM", "epk": epk}
    cek = concat_kdf(ephemeral.exchange(ec.ECDH(), recipient.public_key()), "A128GCM", 128)
    token = compact_jwe_gcm(header, PAYLOAD, cek, IV)
    jwk = p256_jwk(recipient, with_private=True)
    return {
        "entry_point": "authlib.jose.rfc7516.jwe.JsonWebEncryption.deserialize_compact",
        "settings": 'JsonWebEncryption() (the defaults); key: the recipient\'s private P-256 JWK '
                    '{"kty":"EC","crv":"P-256","x","y","d"} (a dict, no "use")',
        "input": 'compact JWE, protected header {"alg":"ECDH-ES","enc":"A128GCM","epk":<ephemeral public P-256 JWK '
                 'with "use":"sig">}, encrypted for the recipient key by ECDH-ES (direct key agreement)',
        "token": token,
        "call": lambda: JsonWebEncryption().deserialize_compact(token, jwk),
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
    return {"input": name, "within_4_4": True, **spec,
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
        entry = {"input": name, "start": start, "end": end, "copy_subject_files_checked": files,
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

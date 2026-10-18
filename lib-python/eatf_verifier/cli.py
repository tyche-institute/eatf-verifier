"""Command-line wrapper — Python port of cli/eatf-verify/bin/eatf-verify.js.

Same interface; same exit codes. Installed as `eatf-verify-py`
(distinct from `eatf-verify` so both can coexist on the same path).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

from . import __version__
from .verifier import VerifyOptions, verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="eatf-verify-py",
        description="Offline verifier for EATF .aep evidence packages (Python port).",
    )
    parser.add_argument("paths", nargs="*", help="One or more .aep files.")
    parser.add_argument(
        "--batch",
        metavar="DIR",
        help="Walk DIR recursively for .aep files.",
    )
    parser.add_argument(
        "--conformance",
        metavar="VECTORS_ROOT",
        help=(
            "Walk a test-vectors tree (valid/ + invalid/) and assert "
            "each expected verdict."
        ),
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit one JSON object per .aep on stdout."
    )
    parser.add_argument(
        "--signer-key",
        action="append",
        default=[],
        metavar="PEM",
        help="Require the embedded signer key to match this SPKI PEM. Repeatable.",
    )
    parser.add_argument(
        "--pqc-signer-key",
        action="append",
        default=[],
        metavar="PEM",
        help=(
            "Require the embedded ML-DSA-65 key to match this RFC 9881 SPKI (or legacy "
            "raw) PEM, one key per file. Repeatable; implies --require-pqc."
        ),
    )
    parser.add_argument(
        "--tsa-trust-list",
        action="append",
        default=[],
        metavar="PEM",
        help="Advisory TSA issuer-name pin. Repeatable; not RFC 5280 validation.",
    )
    parser.add_argument(
        "--offline-only",
        action="store_true",
        default=True,
        help="Default. Refuse external lookups.",
    )
    parser.add_argument(
        "--require-pqc",
        action="store_true",
        help=(
            "Reject packages without a complete, valid ML-DSA-65 signature pair. Without "
            "--pqc-signer-key this does not establish whose key signed."
        ),
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"eatf-verify-py {__version__}"
    )
    args = parser.parse_args(argv)

    if not args.paths and not args.batch and not args.conformance:
        parser.print_help(sys.stderr)
        return 2

    signer_pems = _read_files("--signer-key", args.signer_key)
    trusted_pqc_signer_pems = _read_files("--pqc-signer-key", args.pqc_signer_key)
    tsa_pems = _read_files("--tsa-trust-list", args.tsa_trust_list)
    if signer_pems is None or trusted_pqc_signer_pems is None or tsa_pems is None:
        return 2
    if trusted_pqc_signer_pems:
        from .mldsa import mldsa65_public_key_from_pem
    for path, pem in zip(args.pqc_signer_key, trusted_pqc_signer_pems, strict=True):
        try:
            mldsa65_public_key_from_pem(pem)
        except ValueError as exc:
            print(
                f"eatf-verify-py: --pqc-signer-key {path} is not an ML-DSA-65 public key: {exc}",
                file=sys.stderr,
            )
            return 2
    if args.require_pqc and not trusted_pqc_signer_pems:
        print(
            "eatf-verify-py: warning: --require-pqc without --pqc-signer-key\n"
            "  checks that an ML-DSA-65 signature verifies, not whose key made it.",
            file=sys.stderr,
        )

    opts = VerifyOptions(
        offline_only=args.offline_only,
        trusted_signer_pems=signer_pems,
        trusted_pqc_signer_pems=trusted_pqc_signer_pems,
        tsa_trust_list=tsa_pems,
        pqc_policy="required" if args.require_pqc else "if-present",
    )

    if args.conformance:
        return _run_conformance(args.conformance, opts, json_out=args.json)
    if args.batch:
        return _run_batch(args.batch, opts, json_out=args.json)
    return _run_single_files(args.paths, opts, json_out=args.json)


def _read_files(flag: str, paths: list[str]) -> list[bytes] | None:
    out: list[bytes] = []
    for p in paths:
        try:
            out.append(pathlib.Path(p).read_bytes())
        except OSError as exc:
            print(f"eatf-verify-py: cannot read {flag} {p}: {exc.strerror or exc}", file=sys.stderr)
            return None
    return out


def _run_single_files(paths: list[str], opts: VerifyOptions, *, json_out: bool) -> int:
    any_fail = False
    for p in paths:
        if not os.path.exists(p):
            print(f"eatf-verify-py: no such file: {p}", file=sys.stderr)
            return 2
        with open(p, "rb") as f:
            data = f.read()
        result = verify(data, opts)
        _emit(p, result, json_out=json_out)
        if not result.valid:
            any_fail = True
    return 1 if any_fail else 0


def _run_batch(root: str, opts: VerifyOptions, *, json_out: bool) -> int:
    aeps = _find_aeps(root)
    pass_, fail = 0, 0
    for p in aeps:
        with open(p, "rb") as f:
            data = f.read()
        result = verify(data, opts)
        _emit(p, result, json_out=json_out)
        if result.valid:
            pass_ += 1
        else:
            fail += 1
    if not json_out:
        print(f"\nSummary: {pass_} verified, {fail} failed.")
    return 1 if fail else 0


def _run_conformance(root: str, opts: VerifyOptions, *, json_out: bool) -> int:
    if not os.path.isdir(root):
        print(f"eatf-verify-py: --conformance directory missing: {root}", file=sys.stderr)
        return 2
    aeps = _find_aeps(root)
    pass_, fail, mismatch = 0, 0, 0
    for p in aeps:
        expected = _expected_verdict(pathlib.Path(p), pathlib.Path(root))
        if expected is None:
            continue
        with open(p, "rb") as f:
            data = f.read()
        result = verify(data, opts)
        actual = "true" if result.valid else "false"
        ok = actual == expected
        if json_out:
            print(json.dumps({
                "path": p, "expected": expected, "actual": actual,
                "contract_met": ok,
                "failure_reason": result.failure_reason,
                "failure_code": result.failure_code,
            }))
        else:
            tag = "PASS" if ok else "MISMATCH"
            tail = f"  ({result.failure_reason})" if result.failure_reason else ""
            print(f"{tag}  {os.path.basename(p)}  expected={expected}  actual={actual}{tail}")
        if not ok:
            mismatch += 1
        if result.valid:
            pass_ += 1
        else:
            fail += 1
    if pass_ + fail == 0:
        # A run that checked nothing must not read as a pass.
        print(
            f"eatf-verify-py: --conformance found no .aep vectors under valid/ or invalid/ "
            f"in {root}",
            file=sys.stderr,
        )
        return 2
    if not json_out:
        print(f"\nConformance: {pass_} verified, {fail} rejected, {mismatch} contract mismatches.")
    return 1 if mismatch else 0


def _expected_verdict(path: pathlib.PurePath, root: pathlib.PurePath) -> str | None:
    """Expected verdict from the vector's top-level directory under ``root``.

    Compares path components rather than a "valid/" string prefix: os.walk
    joins with the native separator, so on Windows the relative path is
    ``valid\\...`` and a prefix test matches nothing.
    """
    top = path.relative_to(root).parts[0]
    return {"valid": "true", "invalid": "false"}.get(top)


def _emit(path: str, result, *, json_out: bool) -> None:
    if json_out:
        print(json.dumps({
            "path": path,
            "valid": result.valid,
            "failure_reason": result.failure_reason,
            "failure_code": result.failure_code,
            "pqc_valid": result.pqc_valid,
            "tsa_trusted": result.tsa_trusted,
        }))
        return
    lines = [f"VECTOR {path}", f"  verify={str(result.valid).lower()}"]
    if result.failure_reason:
        lines.append(f"  diagnostic={result.failure_reason}")
    if result.pqc_valid is not None:
        lines.append(f"  pqc={result.pqc_valid}")
    print("\n".join(lines))


def _find_aeps(root: str) -> list[str]:
    out: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".aep"):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


if __name__ == "__main__":
    sys.exit(main())

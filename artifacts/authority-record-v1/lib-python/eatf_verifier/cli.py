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
        help="Walk a test-vectors tree (valid/ + invalid/) and assert each vector matches its verify-expected.txt.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit one JSON object per .aep on stdout."
    )
    parser.add_argument(
        "--tsa-trust-list",
        action="append",
        default=[],
        metavar="PEM",
        help="Pin RFC 3161 TSA root certificate(s). Repeatable. Chain-to-root validation lands in a 0.2.x point release; the option is accepted today for CLI parity with the TypeScript reference.",
    )
    parser.add_argument(
        "--offline-only",
        action="store_true",
        default=True,
        help="Default. Refuse external lookups.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"eatf-verify-py {__version__}"
    )
    args = parser.parse_args(argv)

    if not args.paths and not args.batch and not args.conformance:
        parser.print_help(sys.stderr)
        return 2

    opts = VerifyOptions(
        offline_only=args.offline_only,
        tsa_trust_list=[pathlib.Path(p).read_bytes() for p in args.tsa_trust_list],
    )

    if args.conformance:
        return _run_conformance(args.conformance, opts, json_out=args.json)
    if args.batch:
        return _run_batch(args.batch, opts, json_out=args.json)
    return _run_single_files(args.paths, opts, json_out=args.json)


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
    aeps = _find_aeps(root)
    pass_, fail, mismatch = 0, 0, 0
    base = root.rstrip("/")
    for p in aeps:
        rel = p[len(base):].lstrip("/")
        expected = "true" if rel.startswith("valid/") else "false" if rel.startswith("invalid/") else None
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
    if not json_out:
        print(f"\nConformance: {pass_} verified, {fail} rejected, {mismatch} contract mismatches.")
    return 1 if mismatch else 0


def _emit(path: str, result, *, json_out: bool) -> None:
    if json_out:
        print(json.dumps({
            "path": path,
            "valid": result.valid,
            "failure_reason": result.failure_reason,
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

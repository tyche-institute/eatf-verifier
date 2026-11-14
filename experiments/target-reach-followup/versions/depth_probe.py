#!/usr/bin/env python3
"""Deepest nesting of JSON arrays that json.loads accepts on the Python that runs it.

The depth is searched by bisection between 1 and 10**6, once with the C
scanner (the default of json.JSONDecoder when the _json module is present)
and once with the pure-Python scanner (json.scanner.py_make_scanner). A depth
fails when decoding raises RecursionError.

    python3 -I -B depth_probe.py

prints 1 JSON object. The boundary depends on how many frames are already
on the stack when json.loads is called, so every decode, in the search and
in the check, is made by `ok` called from a function called by `main`.

Sentinels, checked after printing (exit status 1 and a message on standard
error when one does not hold):
D1  for each scanner the reported depth d decodes and d + 1 raises
    RecursionError, each checked 3 times, in fresh decoder calls made at the
    same Python call depth as the calls of the search;
D2  the C scanner is the one in use for the "c" probe: its scan_once comes
    from the _json module.
"""
from __future__ import annotations

import json
import json.scanner
import platform
import sys

HIGH = 10 ** 6


def ok(n: int, decoder) -> bool:
    try:
        decoder.decode("[" * n + "]" * n)
        return True
    except RecursionError:
        return False


def deepest(decoder) -> int | None:
    lo, hi = 0, HIGH
    if ok(hi, decoder):
        return None
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if ok(mid, decoder) else (lo, mid)
    return lo


def boundary(d: int, decoder) -> bool:
    """D1: d decodes and d + 1 does not, 3 times; called from main, like deepest."""
    for _ in range(3):
        if not ok(d, decoder) or ok(d + 1, decoder):
            return False
    return True


def main() -> int:
    c = json.JSONDecoder()
    py = json.JSONDecoder()
    py.scan_once = json.scanner.py_make_scanner(py)
    row = {"python": platform.python_version(), "implementation": platform.python_implementation(),
           "recursion_limit": sys.getrecursionlimit(),
           "c_scanner_module": type(c.scan_once).__module__,
           "deepest_c": deepest(c), "deepest_py": deepest(py)}
    print(json.dumps(row), flush=True)
    problems = []
    if row["c_scanner_module"] != "_json":
        problems.append(f"D2: scan_once of the default decoder comes from {row['c_scanner_module']}")
    for key, decoder in (("deepest_c", c), ("deepest_py", py)):
        d = row[key]
        if d is None:
            problems.append(f"D1: {key}: depth {HIGH} decodes")
        elif not boundary(d, decoder):
            problems.append(f"D1: {key}: depth {d} is not the boundary on a repeat")
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Why the toolkit counts each of the 5 sampled checks of authlib as reachable.

    python3 -I -B name-paths.py [--toolkit DIR] [--clone DIR] > name-paths.txt

Reads only: the toolkit's `reach/checks.py` (imported, not changed), the
subject definition `subjects/authlib/subject.json` and `checks.json`, and the
clone of the first study. Writes nothing; the output goes to stdout.

The toolkit marks a function reachable when a chain of names leads to it from
a function that has the name of an entry point: each function refers to the
names of the functions it calls, `f(...)`, and to every attribute `x.f`, and
every function of the package that has such a name is taken as called
(`reachable_functions` and `referenced_names` of `reach/checks.py`). This
script builds the same table of functions with the same code, and prints, for
the function of each sampled check, 1 shortest chain of names from an entry
point (breadth first, names and functions taken in sorted order), with the
line of the caller at which each name is referenced. A chain of names is what
the toolkit read; whether a call at that line can run the next function is a
question of the source, answered in READING.md.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTENSION = HERE.parents[2]
TOOLKIT = EXTENSION.parent / "target-reach"
SAMPLE = EXTENSION / "no-fire" / "sample.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def name_lines(fn: ast.AST, name: str) -> list[int]:
    """Lines at which `fn` refers to `name`, as `referenced_names` counts a reference."""
    out = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name:
            out.add(node.lineno)
        elif isinstance(node, ast.Attribute) and node.attr == name:
            out.add(node.lineno)
    return sorted(out)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--toolkit", default=str(TOOLKIT))
    parser.add_argument("--clone", default=str(TOOLKIT / "work" / "src" / "authlib"))
    args = parser.parse_args(argv)
    toolkit, clone = Path(args.toolkit), Path(args.clone)
    sys.path.insert(0, str(toolkit))
    from reach.checks import (ModuleTable, functions, plain_name, reachable_functions,  # noqa: E402
                              referenced_names, rel_to_source)

    subject_path = toolkit / "subjects" / "authlib" / "subject.json"
    checks_path = toolkit / "subjects" / "authlib" / "checks.json"
    subject = json.loads(subject_path.read_text(encoding="utf-8"))
    checks = {c["id"]: c for c in json.loads(checks_path.read_text(encoding="utf-8"))["checks"]}
    print(f"python {sys.version.split()[0]}")
    for p in (toolkit / "reach" / "checks.py", subject_path, checks_path, SAMPLE):
        print(f"read {p} sha256 {sha256(p)}")
    print(f"clone {clone}")

    import csv
    with SAMPLE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    sampled = [(n, r) for n, r in enumerate(rows, 1) if r["library"] == "authlib"]

    table = ModuleTable(subject, clone)
    files = list(subject["subject_files"]) + list(subject.get("observed_files", []))
    mods = {rel: table.module_for(clone / rel_to_source(subject, rel)) for rel in files}
    fns = {(rel, q): node for rel, mod in mods.items() for q, node in functions(mod.tree).items()}
    reach = reachable_functions(fns, subject["entry_points"])
    by_name: dict[str, list] = {}
    for key in fns:
        by_name.setdefault(plain_name(key[1]), []).append(key)
    starts = sorted(k for k in fns if plain_name(k[1]) in subject["entry_points"])
    print(f"{len(fns)} functions, {len(reach)} reachable by name; entry points {subject['entry_points']}")
    print("functions with the name of an entry point:")
    for rel, q in starts:
        print(f"  {rel}:{fns[(rel, q)].lineno} {q}")

    # breadth first from all entry functions together: 1 shortest chain to every function
    parent: dict[tuple, tuple | None] = {k: None for k in starts}
    via: dict[tuple, str] = {}
    queue = deque(starts)
    while queue:
        key = queue.popleft()
        for name in sorted(referenced_names(fns[key])):
            for other in sorted(by_name.get(name, [])):
                if other not in parent:
                    parent[other] = key
                    via[other] = name
                    queue.append(other)
    if set(parent) != reach:
        print("the breadth-first search and reachable_functions disagree")
        return 1

    for n, row in sampled:
        check = checks[row["check"]]
        target = (check["file"], check["function"])
        print()
        print(f"row {n}: {check['id']}")
        print(f"  raise lines {[a for a, _ in check['lines']]} in {check['file']}; "
              f"reachable in checks.json: {check['reachable']}; reachable here: {target in reach}")
        chain = []
        key = target
        while key is not None:
            chain.append(key)
            key = parent.get(key)
        chain.reverse()
        first = chain[0]
        print(f"  {first[0]}:{fns[first].lineno} {first[1]}  (entry point name)")
        for prev, key in zip(chain, chain[1:]):
            name = via[key]
            lines = name_lines(fns[prev], name)
            print(f"    -> name `{name}` referenced at {prev[0]}:{','.join(map(str, lines))}")
            print(f"  {key[0]}:{fns[key].lineno} {key[1]}")
        callers = sorted(k for k in fns if plain_name(target[1]) in referenced_names(fns[k]))
        print(f"  every function that refers to the name `{plain_name(target[1])}`:")
        for k in callers:
            print(f"    {k[0]}:{','.join(map(str, name_lines(fns[k], plain_name(target[1]))))} {k[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

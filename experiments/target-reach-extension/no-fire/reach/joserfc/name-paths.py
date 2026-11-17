#!/usr/bin/env python3
"""Why the toolkit counts the 5 sampled checks of joserfc as reachable: for the
function of each check, 1 shortest chain of names from a function that has the
name of an entry point.

    python3 -I -B <this file> > <this folder>/name-paths.txt

The toolkit's rule (`reach/checks.py` of the first study, `referenced_names`
and `reachable_functions`, lines 874-898): a function refers to the names it
calls, `f(...)`, and to every attribute name it mentions, `x.f`; every function
of the package with such a name counts as called. This script builds the table
of functions with the toolkit's own code (`ModuleTable`, `functions`,
`plain_name`, imported from the toolkit and not changed; `-B` keeps Python from
writing bytecode there), over the subject files of `subject.json` in the copy
made by the scripts of this folder (its files are checked against `sha256` of
checks.json first), and searches breadth first, in sorted order. Each step
gives the line of the caller at which the name is referenced. A chain of names
is what the toolkit counts; whether a call at that line can run the next
function at run time is a question of the source, answered in READING.md.
Reads only; writes nothing but its output to stdout.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTENSION = HERE.parents[2]
TOOLKIT = EXTENSION.parent / "target-reach"
DEFS = TOOLKIT / "subjects" / "joserfc"
COPY = EXTENSION / "work" / "reach" / "joserfc" / "copy"
SAMPLE = EXTENSION / "no-fire" / "sample.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_lines(fn: ast.AST, name: str) -> list[int]:
    """The lines at which `fn` refers to `name`, as `referenced_names` counts it."""
    found = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name:
            found.add(node.lineno)
        elif isinstance(node, ast.Attribute) and node.attr == name:
            found.add(node.lineno)
    return sorted(found)


def main() -> int:
    sys.dont_write_bytecode = True  # nothing is written into the toolkit, with or without -B
    sys.path.insert(0, str(TOOLKIT))
    from reach.checks import ModuleTable, functions, plain_name, referenced_names, rel_to_source

    subject = json.loads((DEFS / "subject.json").read_text(encoding="utf-8"))
    checks = json.loads((DEFS / "checks.json").read_text(encoding="utf-8"))
    for rel, digest in checks["sha256"].items():
        if sha256(COPY / rel_to_source(subject, rel)) != digest:
            raise SystemExit(f"{rel} of the copy differs from the clone")
    table = ModuleTable(subject, COPY)
    mods = {rel: table.module_for(COPY / rel_to_source(subject, rel)) for rel in subject["subject_files"]}
    fns = {(rel, q): node for rel, mod in mods.items() for q, node in functions(mod.tree).items()}
    by_name: dict[str, list] = {}
    for key in fns:
        by_name.setdefault(plain_name(key[1]), []).append(key)

    starts = sorted(k for k in fns if plain_name(k[1]) in subject["entry_points"])
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

    with SAMPLE.open(encoding="utf-8", newline="") as handle:
        rows = [(i, r) for i, r in enumerate(csv.DictReader(handle), 1) if r["library"] == "joserfc"]
    print(f"subject: {DEFS.relative_to(TOOLKIT.parent.parent)}/subject.json, commit {subject['commit']}")
    print(f"entry points: {', '.join(subject['entry_points'])}")
    print(f"functions in the table: {len(fns)}; reachable by the rule: {len(parent)}")
    listed = {(f["file"], f["function"]) for f in checks["functions"]}
    listed_reachable = {(f["file"], f["function"]) for f in checks["functions"] if f["reachable"]}
    print(f"`functions` of checks.json: {len(listed)}, {len(listed_reachable)} reachable; "
          f"the same sets as here: {listed == set(fns) and listed_reachable == set(parent)}")
    for row, r in rows:
        check = next(c for c in checks["checks"] if c["id"] == r["check"])
        target = (check["file"], check["function"])
        print()
        print(f"row {row}: {check['id']} ({check['file']}:{check['lines'][0][0]}, {check['class_name']})")
        if target not in parent:
            print("  not reachable by the rule")
            continue
        chain = [target]
        while parent[chain[-1]] is not None:
            chain.append(parent[chain[-1]])
        chain.reverse()
        first = chain[0]
        print(f"  {first[0]}:{fns[first].lineno} {first[1]} (entry point name)")
        for caller, callee in zip(chain, chain[1:]):
            name = via[callee]
            lines = reference_lines(fns[caller], name)
            others = [k for k in by_name[name] if k != callee]
            print(f"  -> name '{name}' at {caller[0]}:{','.join(map(str, lines))} -> "
                  f"{callee[0]}:{fns[callee].lineno} {callee[1]}"
                  + (f" (other definitions with this name: {len(others)})" if others else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

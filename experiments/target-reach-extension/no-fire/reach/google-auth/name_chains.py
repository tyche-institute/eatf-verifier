"""The chain of names by which the toolkit counts each sampled check of
google-auth as reachable.

    python3 -I -B name_chains.py > name_chains.txt

Reads the subject files of the clone and applies the toolkit's own reading of
reachability (`../../../../target-reach/reach/checks.py`, functions
`functions`, `referenced_names` and `plain_name`, imported unchanged): a
function refers to every name it calls and to every attribute name it
mentions, and a name stands for every function definition of that name in the
subject files. For each sampled check it prints 1 shortest chain from a
function named `decode` to the function of the check, with the line of each
reference. It runs no code of the library. A chain shows why the toolkit
counts a check as reachable; it does not show that a call follows it.
"""

from __future__ import annotations

import ast
import csv
import json
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
X = HERE.parents[2]                       # experiments/target-reach-extension
T = X.parent / "target-reach"
sys.path.insert(0, str(T))

from reach.checks import functions, plain_name, referenced_names  # noqa: E402

SUBJECT = json.loads((T / "subjects/google-auth/subject.json").read_text(encoding="utf-8"))
CLONE = T / "work/src/google-auth/packages/google-auth"
SAMPLE = X / "no-fire/sample.csv"


def reference_lines(fn: ast.AST, name: str) -> list[int]:
    """The lines where `fn` refers to `name`, as `referenced_names` reads it."""
    lines = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name:
            lines.add(node.lineno)
        elif isinstance(node, ast.Attribute) and node.attr == name:
            lines.add(node.lineno)
    return sorted(lines)


def main() -> int:
    fns = {}
    for rel in SUBJECT["subject_files"]:
        tree = ast.parse((CLONE / rel).read_text(encoding="utf-8"), filename=rel)
        for qual, node in functions(tree).items():
            fns[(rel, qual)] = node
    by_name: dict[str, list] = {}
    for key in fns:
        by_name.setdefault(plain_name(key[1]), []).append(key)
    starts = sorted(k for k in fns if plain_name(k[1]) in SUBJECT["entry_points"])
    parent = {k: None for k in starts}
    todo = deque(starts)
    while todo:                            # breadth first: a shortest chain
        key = todo.popleft()
        for name in sorted(referenced_names(fns[key])):
            for other in sorted(by_name.get(name, [])):
                if other not in parent:
                    parent[other] = (key, name)
                    todo.append(other)
    print(f"entry points: {', '.join(f'{r}:{q} (line {fns[(r, q)].lineno})' for r, q in starts)}")
    print(f"functions in the subject files: {len(fns)}; in the closure of the entry points: {len(parent)}")
    with SAMPLE.open(encoding="utf-8", newline="") as handle:
        rows = [(n, row) for n, row in enumerate(csv.DictReader(handle), 1) if row["library"] == "google-auth"]
    for n, row in rows:
        key = (row["file"], row["function"])
        print()
        print(f"row {n}: {row['check']} ({row['file']}, line {row['line']})")
        if key not in parent:
            print("  not in the closure")
            continue
        chain = []
        while parent[key] is not None:
            prev, name = parent[key]
            chain.append((prev, name, key))
            key = prev
        chain.reverse()
        print(f"  start: {chain[0][0][0]}:{chain[0][0][1]} (line {fns[chain[0][0]].lineno})" if chain else "  start")
        for prev, name, nxt in chain:
            lines = ", ".join(str(x) for x in reference_lines(fns[prev], name))
            print(f"  {prev[0]}:{prev[1]} refers to `{name}` (line {lines})"
                  f" -> {nxt[0]}:{nxt[1]} (def at line {fns[nxt].lineno})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

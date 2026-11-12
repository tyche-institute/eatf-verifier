"""Guard deletion for the Python port, done on the syntax tree.

Every `return _fail(...)` whose code argument (a string literal, or both
branches of a conditional expression) belongs to the guard becomes `pass`. For
1-zip, the `raise` statements inside the guard's own line range become `pass`
as well. The rest of the program is left as it is, so a case whose guard is
deleted runs on into whatever comes next.
"""

from __future__ import annotations

import ast

SUBJECT = "lib-python/eatf_verifier/verifier.py"


def _codes_of(node: ast.expr) -> list[str] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        a, b = _codes_of(node.body), _codes_of(node.orelse)
        return a + b if a is not None and b is not None else None
    return None


def delete_guard(source: str, guard: str, regions: dict) -> tuple[str, list[dict]]:
    codes = set(regions["guards"][guard]["codes"])
    ranges = [(a, b) for a, b, name in regions["files"]["python"][SUBJECT]["regions"] if name == guard]
    tree = ast.parse(source)
    targets: list[tuple[ast.stmt, str]] = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Return) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == "_fail"):
            found = _codes_of(node.value.args[1])
            if found is None:
                raise ValueError(f"_fail() without a literal code at line {node.lineno}")
            mine = [code for code in found if code in codes]
            if len(mine) == len(found):
                targets.append((node, "return _fail"))
            elif mine:
                raise ValueError(f"_fail() mixes guards at line {node.lineno}")
        if (guard == "1-zip" and isinstance(node, ast.Raise)
                and any(a <= node.lineno <= b for a, b in ranges)):
            targets.append((node, "raise"))

    # ast offsets are UTF-8 byte columns, so edit the encoded lines
    lines = source.encode("utf-8").splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    data = source.encode("utf-8")
    for node, _ in sorted(targets, key=lambda t: (t[0].lineno, t[0].col_offset), reverse=True):
        begin = starts[node.lineno - 1] + node.col_offset
        end = starts[node.end_lineno - 1] + node.end_col_offset
        data = data[:begin] + b"pass" + data[end:]
    output = data.decode("utf-8")
    ast.parse(output)  # the deleted program must still be a program
    replaced = sorted(({"line": node.lineno, "kind": kind} for node, kind in targets),
                      key=lambda r: r["line"])
    return output, replaced

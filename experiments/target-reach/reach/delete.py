"""Deletion copies: every raise statement of one check becomes `pass`.

The line count is kept (a multi-line raise becomes `pass` followed by blank
continuation lines), so every line number of the unmodified source stays
valid and raise sites are mapped by line.
"""

from __future__ import annotations

import ast

from .checks import functions, own_nodes


def delete_check(source: str, check: dict) -> tuple[str, list[dict]]:
    tree = ast.parse(source)
    fns = functions(tree)
    fn = fns[check["function"]]
    raises = {(n.lineno, n.end_lineno): n for n in own_nodes(fn, ast.Raise)}
    lines = source.splitlines(keepends=True)
    enc = [line.encode("utf-8") for line in lines]
    changed = []
    for a, z in sorted((tuple(x) for x in check["lines"]), reverse=True):
        node = raises.get((a, z))
        if node is None:
            raise SystemExit(f"{check['id']}: no raise statement on lines {a}-{z}")
        first, last = a - 1, z - 1
        prefix = enc[first][:node.col_offset]
        suffix = enc[last][node.end_col_offset:]
        removed = b"".join(enc[first:last + 1]).decode("utf-8")
        if first == last:
            enc[first] = prefix + b"pass" + suffix
        else:
            enc[first] = prefix + b"pass\n"
            for i in range(first + 1, last):
                enc[i] = b"\n"
            enc[last] = suffix if suffix.strip() else b"\n"
        changed.append({"lines": [a, z], "removed": removed})
    out = b"".join(enc).decode("utf-8")
    new_tree = ast.parse(out)
    compile(out, check["file"], "exec")
    if len(out.splitlines()) != len(source.splitlines()):
        raise SystemExit(f"{check['id']}: the deletion changed the line count")
    new_fns = functions(new_tree)
    left = own_nodes(new_fns[check["function"]], ast.Raise)
    if len(left) != len(raises) - len(check["lines"]):
        raise SystemExit(f"{check['id']}: {len(raises) - len(left)} raises gone, "
                         f"expected {len(check['lines'])}")
    for name, node in fns.items():
        if name == check["function"] or check["function"].startswith(name + "."):
            continue
        if name.startswith(check["function"] + "."):
            continue
        if ast.dump(node) != ast.dump(new_fns[name]):
            raise SystemExit(f"{check['id']}: the deletion also changed {name}")
    return out, sorted(changed, key=lambda c: c["lines"])

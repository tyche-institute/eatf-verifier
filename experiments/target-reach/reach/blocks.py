"""Enumerate the negative-test blocks of a subject's tests (AST only).

A block is a `pytest.raises` or `unittest.TestCase.assertRaises*` use, in its
context-manager or its callable form. See the toolkit README.

The expected classes of a block are resolved in its test module as the raise
statements of the package are (reach/checks.py): `expected` holds their labels
and `expected_kinds` how each was resolved. A test module inside the package
directory is a package module; a test module outside it has its own bindings,
reaches package modules by absolute imports, and its relative imports are
not followed.
"""

from __future__ import annotations

import ast
from pathlib import Path

from .checks import (EXTERNAL, UNKNOWN, ModuleTable, ancestors, is_rejection, last_name, read_source,
                     rel_to_source)

UNITTEST_NAMES = ("assertRaises", "assertRaisesRegex", "assertRaisesRegexp")
VALUE_ATTRS = ("value", "exception")  # ExceptionInfo.value, unittest context .exception


def test_files(subject: dict, root: Path) -> list[Path]:
    out = set()
    for entry in subject["tests"]:
        p = Path(root) / entry
        if p.is_file():
            out.add(p)
        elif p.is_dir():
            out |= {f for f in p.rglob("*.py") if f.name.startswith("test_") or f.name.endswith("_test.py")}
    return sorted(out)


def raises_kind(call: ast.AST, raises_aliases: set[str]) -> str | None:
    """'pytest' or 'unittest' or None, for a Call node."""
    if not isinstance(call, ast.Call):
        return None
    f = call.func
    if isinstance(f, ast.Attribute) and f.attr == "raises" and isinstance(f.value, ast.Name) \
            and f.value.id == "pytest":
        return "pytest"
    if isinstance(f, ast.Name) and f.id in raises_aliases:
        return "pytest"
    if isinstance(f, ast.Attribute) and f.attr in UNITTEST_NAMES:
        return "unittest"
    return None


def test_functions(tree: ast.Module) -> list[tuple[str | None, ast.AST]]:
    """(class qualname or None, function) for module functions and methods.
    When a name is defined twice in one scope, the last definition is kept: it
    is the one Python binds, so the earlier one never runs."""
    found: dict[tuple[str | None, str], ast.AST] = {}

    def walk(node, prefix):
        for child in node.body if hasattr(node, "body") else []:
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[(prefix[:-1] or None, child.name)] = child
    walk(tree, "")
    return sorted(((cls, fn) for (cls, _), fn in found.items()), key=lambda x: x[1].lineno)


def entry_calls(nodes: list[ast.AST], entry_points: list[str], references: bool) -> list[str]:
    """Names of entry points called (or, with references=True, referenced) in nodes."""
    out = []
    for top in nodes:
        for n in ast.walk(top):
            if isinstance(n, ast.Call):
                name = last_name(n.func) if isinstance(n.func, (ast.Name, ast.Attribute)) else None
                if name in entry_points:
                    out.append(name)
            elif references and isinstance(n, (ast.Name, ast.Attribute)):
                name = n.id if isinstance(n, ast.Name) else n.attr
                if name in entry_points:
                    out.append(name)
    return sorted(set(out))


def expected_exprs(node: ast.AST | None) -> list[ast.AST] | None:
    """The class expressions (names and attribute chains) of an
    expected-exception expression, or None if not static."""
    if node is None:
        return None
    if isinstance(node, (ast.Name, ast.Attribute)):
        return [node]
    if isinstance(node, ast.Tuple):
        out = []
        for e in node.elts:
            sub = expected_exprs(e)
            if sub is None:
                return None
            out += sub
        return out
    return None


def expected_names(node: ast.AST | None) -> list[str] | None:
    """Class names of an expected-exception expression, or None if not static."""
    exprs = expected_exprs(node)
    return None if exprs is None else [last_name(e) for e in exprs]


def leaf_exprs(node: ast.AST) -> list[ast.AST] | None:
    """Class expressions that an expression assigned to a local name can
    evaluate to: names, attributes, tuples, conditional expressions and `or`
    chains."""
    if isinstance(node, ast.IfExp):
        a, b = leaf_exprs(node.body), leaf_exprs(node.orelse)
        return None if a is None or b is None else a + b
    if isinstance(node, ast.BoolOp):
        out = []
        for v in node.values:
            sub = leaf_exprs(v)
            if sub is None:
                return None
            out += sub
        return out
    return expected_exprs(node)


def leaf_names(node: ast.AST) -> list[str] | None:
    exprs = leaf_exprs(node)
    return None if exprs is None else [last_name(e) for e in exprs]


def resolve_expected(expr: ast.AST | None, fn: ast.AST, before_line: int, table: ModuleTable,
                     module, scopes: list) -> tuple[list[str] | None, list[str] | None, str | None]:
    """(labels, kinds, how) of an expected-exception expression, resolved in
    the test module: directly, or, when the expression is a name that the
    module and the enclosing functions do not bind, through the local
    assignments of the test function before the block."""
    exprs = expected_exprs(expr)
    if exprs is None:
        return None, None, None

    def direct() -> tuple[list[str], list[str], str]:
        res = [table.resolve(module, e, scopes) for e in exprs]
        return [r.label for r in res], [r.kind for r in res], "direct"

    if isinstance(expr, ast.Name) and table.resolve(module, expr, scopes, fallback=False).kind == UNKNOWN:
        values = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign) and n.lineno < before_line and any(
                    isinstance(t, ast.Name) and t.id == expr.id for t in n.targets):
                values.append(n.value)
        if values:
            leaves = []
            for v in values:
                sub = leaf_exprs(v)
                if sub is None:
                    return direct()
                leaves += sub
            pairs: dict[str, str] = {}
            for r in sorted((table.resolve(module, e, scopes) for e in leaves),
                            key=lambda r: (r.label or "", r.kind)):
                pairs.setdefault(r.label, r.kind)
            return list(pairs), list(pairs.values()), "local assignment"
    return direct()


def literal(node: ast.AST | None):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return node.value if isinstance(node.value, str) else node.value.decode("latin-1")
    return None


# -- post-assertions -------------------------------------------------------------

class PostReader:
    """Reads the assertions on a bound exception after its block."""

    def __init__(self, binding: str):
        self.binding = binding
        self.aliases: set[str] = set()

    def is_value(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name) and node.id in self.aliases:
            return True
        return (isinstance(node, ast.Attribute) and node.attr in VALUE_ATTRS
                and isinstance(node.value, ast.Name) and node.value.id == self.binding)

    def is_str_of_value(self, node: ast.AST) -> bool:
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "str" and len(node.args) == 1 and self.is_value(node.args[0]))

    def mentions(self, node: ast.AST) -> bool:
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and (n.id == self.binding or n.id in self.aliases):
                return True
        return False

    def note_alias(self, node: ast.Assign) -> bool:
        if self.is_value(node.value):
            self.aliases |= {t.id for t in node.targets if isinstance(t, ast.Name)}
            return True
        return False

    def compare(self, left, op, right) -> list | None:
        if isinstance(op, ast.Eq):
            for a, b in ((left, right), (right, left)):
                if self.is_str_of_value(a) and literal(b) is not None:
                    return ["str_eq", literal(b)]
                if isinstance(a, ast.Attribute) and self.is_value(a.value) and isinstance(b, ast.Constant):
                    return ["attr_eq", a.attr, b.value]
        if isinstance(op, ast.In) and self.is_str_of_value(right) and literal(left) is not None:
            return ["str_in", literal(left)]
        return None

    def read(self, stmt: ast.stmt) -> list | None:
        """A spec, or ["unparsed", source] if the statement mentions the
        exception but is not recognised, or None if it does not mention it."""
        if not self.mentions(stmt):
            return None
        spec = None
        if isinstance(stmt, ast.Assert):
            t = stmt.test
            if isinstance(t, ast.Compare) and len(t.ops) == 1:
                spec = self.compare(t.left, t.ops[0], t.comparators[0])
            elif isinstance(t, ast.Call):
                spec = self.match_call(t)
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            c = stmt.value
            spec = self.match_call(c)
            if spec is None and isinstance(c.func, ast.Attribute) and len(c.args) >= 2:
                a, b = c.args[0], c.args[1]
                if c.func.attr == "assertEqual":
                    spec = self.compare(a, ast.Eq(), b)
                elif c.func.attr == "assertIn":
                    spec = self.compare(a, ast.In(), b)
        return spec if spec is not None else ["unparsed", ast.unparse(stmt)]

    def match_call(self, c: ast.Call) -> list | None:
        if (isinstance(c.func, ast.Attribute) and c.func.attr == "match"
                and isinstance(c.func.value, ast.Name) and c.func.value.id == self.binding
                and c.args and literal(c.args[0]) is not None):
            return ["match", literal(c.args[0])]
        return None


def statements_after(fn: ast.AST, after_line: int) -> list[ast.stmt]:
    out = [n for n in ast.walk(fn) if isinstance(n, ast.stmt) and n.lineno > after_line
           and not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    # keep only innermost simple statements (compound statements are walked into)
    simple = [n for n in out if not isinstance(n, (ast.If, ast.For, ast.While, ast.With,
                                                  ast.Try, ast.AsyncFor, ast.AsyncWith))
              and type(n).__name__ != "TryStar"]
    return sorted(simple, key=lambda n: (n.lineno, n.col_offset))


def binds(node: ast.AST, name: str) -> bool:
    if isinstance(node, ast.With):
        return any(isinstance(i.optional_vars, ast.Name) and i.optional_vars.id == name
                   for i in node.items)
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    return False


def post_assertions(fn: ast.AST, end_line: int, binding: str | None) -> tuple[list, list]:
    if binding is None:
        return [], []
    reader = PostReader(binding)
    rebinders = min((n.lineno for n in ast.walk(fn)
                        if isinstance(n, (ast.With, ast.Assign)) and n.lineno > end_line
                        and binds(n, binding)), default=None)
    parsed, unparsed = [], []
    for stmt in statements_after(fn, end_line):
        if rebinders is not None and stmt.lineno >= rebinders:
            break
        if isinstance(stmt, ast.Assign) and reader.note_alias(stmt):
            continue
        spec = reader.read(stmt)
        if spec is None:
            continue
        (unparsed if spec[0] == "unparsed" else parsed).append(spec if spec[0] != "unparsed" else spec[1])
    return parsed, unparsed


# -- blocks ------------------------------------------------------------------------

def find_blocks(fn: ast.AST, aliases: set[str]) -> list[dict]:
    """Raw blocks of one test function in source order."""
    found = []
    parents = {}
    for n in ast.walk(fn):
        for c in ast.iter_child_nodes(n):
            parents[c] = n
    for n in ast.walk(fn):
        if isinstance(n, ast.With):
            for item in n.items:
                kind = raises_kind(item.context_expr, aliases)
                if kind:
                    var = item.optional_vars
                    found.append({"form": "with", "kind": kind, "call": item.context_expr,
                                  "node": n, "binding": var.id if isinstance(var, ast.Name) else None})
    with_calls = {id(b["call"]) for b in found}
    for n in ast.walk(fn):
        kind = raises_kind(n, aliases)
        if not kind or id(n) in with_calls:
            continue
        name = n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
        n_lead = 2 if name.startswith("assertRaisesRegex") else 1
        callable_args = n.args[n_lead:] + ([k.value for k in n.keywords if k.arg == "func"]
                                           if kind == "pytest" else [])
        if not callable_args:
            continue  # a context manager created outside a `with` header: not a block
        par = parents.get(n)
        binding = None
        if isinstance(par, ast.Assign) and par.value is n:
            binding = next((t.id for t in par.targets if isinstance(t, ast.Name)), None)
        found.append({"form": "call", "kind": kind, "call": n, "node": n, "binding": binding})
    return sorted(found, key=lambda b: (b["call"].lineno, b["call"].col_offset))


def enumerate_blocks(subject: dict, root: Path, checks_doc: dict) -> dict:
    root = Path(root)
    classes = checks_doc["classes"]
    bases = ([b["name"] for b in checks_doc["rejection_bases"]] if "rejection_bases" in checks_doc
             else subject["rejection_bases"])
    entry = subject["entry_points"]
    table = ModuleTable(subject, root)
    blocks = []
    files = test_files(subject, root)
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            module = table.module_for(path)
        except SyntaxError:
            continue
        tree = module.tree
        aliases = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                   and n.module == "pytest" for a in n.names if a.name == "raises"}
        for cls, fn in test_functions(tree):
            test = f"{cls}.{fn.name}" if cls else fn.name
            for k, raw in enumerate(find_blocks(fn, aliases)):
                call = raw["call"]
                name = call.func.attr if isinstance(call.func, ast.Attribute) else call.func.id
                regex_form = name.startswith("assertRaisesRegex")
                exp_node = call.args[0] if call.args else next(
                    (kw.value for kw in call.keywords if kw.arg == "expected_exception"), None)
                if raw["form"] == "with":
                    w = raw["node"]
                    header = [w.lineno, call.end_lineno]
                    body = [w.body[0].lineno, w.body[-1].end_lineno]
                    calls = entry_calls(w.body, entry, references=False)
                    end_line = w.end_lineno
                else:
                    header = [call.lineno, call.end_lineno]
                    body = None
                    lead = 2 if regex_form else 1
                    calls = entry_calls(list(call.args[lead:]) + [k2.value for k2 in call.keywords],
                                        entry, references=True)
                    end_line = call.end_lineno
                scopes = [fn] + module.scopes.get(id(fn), ("", []))[1]
                names, kinds, how = resolve_expected(exp_node, fn, header[0], table, module, scopes)
                pattern, pattern_unparsed = None, None
                if regex_form:
                    if len(call.args) > 1:
                        pattern = literal(call.args[1])
                        if pattern is None:
                            pattern_unparsed = ast.unparse(call.args[1])
                else:
                    m = next((kw.value for kw in call.keywords if kw.arg in ("match", "expected_regex")), None)
                    if m is not None:
                        pattern = literal(m)
                        if pattern is None:
                            pattern_unparsed = ast.unparse(m)
                post, post_unparsed = post_assertions(fn, end_line, raw["binding"])
                row = {
                    "key": f"{rel}::{test}#{k}",
                    "file": rel,
                    "test_class": cls,
                    "test": fn.name,
                    "k": k,
                    "form": raw["form"],
                    "api": raw["kind"],
                    "header_span": header,
                    "body_span": body,
                    "expected_source": ast.unparse(exp_node) if exp_node is not None else None,
                    "expected": names,
                    "expected_kinds": kinds,
                    "expected_resolution": how,
                    "match": pattern,
                    "match_unparsed": pattern_unparsed,
                    "binding": raw["binding"],
                    "post": post,
                    "post_unparsed": post_unparsed,
                    "entry_calls": calls,
                }
                reasons = []
                if not calls:
                    reasons.append("no entry-point call")
                if names is None:
                    reasons.append(f"expects {row['expected_source']}")
                else:
                    for n, kind in zip(names, kinds):
                        if kind in (EXTERNAL, UNKNOWN) or not is_rejection(n, classes, bases):
                            reasons.append(f"expects {n}")
                row["included"] = not reasons
                row["exclusion"] = reasons
                blocks.append(row)
    keys = [b["key"] for b in blocks]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate block keys")
    return {
        "test_files": [p.relative_to(root).as_posix() for p in files],
        "blocks": blocks,
        "counts": {"blocks": len(blocks), "included": sum(b["included"] for b in blocks),
                   "entry_point_blocks": sum(bool(b["entry_calls"]) for b in blocks)},
    }


def line_map(blocks_doc: dict) -> dict[tuple[str, int], str]:
    """(file, line) -> block key over each block's header span."""
    out: dict[tuple[str, int], str] = {}
    for b in blocks_doc["blocks"]:
        for line in range(b["header_span"][0], b["header_span"][1] + 1):
            out.setdefault((b["file"], line), b["key"])
    return out


__all__ = ["enumerate_blocks", "line_map", "ancestors"]

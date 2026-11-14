"""Enumerate the checks of a subject's source files (AST only, no import).

A check is the set of `raise` statements in 1 function of a subject or
observed file that construct the same rejection class with the same message
template. The message is the first positional argument of the call or, when
the call has none, the keyword argument named as the first parameter of the
class's `__init__`. A `raise name` counts when the function assigns `name`
exactly once, from a call that constructs a rejection class. See PROTOCOL.md
for the full definition.

A class is known by the module that defines it. A class expression (a name
or an attribute chain) is resolved through the bindings of its module: class
statements, imports (relative ones too), star imports from package modules
and aliases. A class of the package is labelled by its bare name when no other
class statement of the package has that name and no built-in has it, else by
`<module>.<qualified name>`; a built-in class by its name; a class imported
from outside the package by its dotted path. An expression that cannot be
followed resolves to the package class of the same bare name when exactly 1
class statement has that name and no built-in has it (recorded as "unique
name"); otherwise it names no class, and its label is the name as written
after a question mark (`?name`). A class statement of a test module outside
the package directory names no class of the package.
"""

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import re
from pathlib import Path

PLACEHOLDER = "{*}"


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_subject(path: Path) -> dict:
    return load_json(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_source(path: Path) -> str:
    """The text of a Python file, without a leading byte-order mark."""
    return Path(path).read_text(encoding="utf-8-sig")


def package_dir(subject: dict, root: Path) -> Path:
    """The package directory; a dotted package name (a.b) is the directory a/b."""
    return Path(root).joinpath(subject.get("source_root", "."), *subject["package"].split("."))


def rel_to_source(subject: dict, rel: str) -> str:
    """Path of a subject file relative to the clone root."""
    src = subject.get("source_root", ".")
    return rel if src in (".", "") else f"{src.rstrip('/')}/{rel}"


def module_label(subject: dict, rel: str) -> str:
    """Dotted module path of a file: relative to the package directory when the
    file is inside it, and to the source root otherwise. It starts every check
    id of the file, so 2 files with the same name give different ids."""
    parts = Path(rel).with_suffix("").parts
    pkg = tuple(subject["package"].split("."))
    if len(parts) > len(pkg) and parts[:len(pkg)] == pkg:
        parts = parts[len(pkg):]
    return ".".join(parts)


# -- the module table and name resolution -------------------------------------

BUILTIN_NAMES = frozenset(dir(builtins))

# How a class expression was resolved (the values of `class_resolution` and
# `expected_kinds`).
DEFINITION, IMPORT, BUILTIN, UNIQUE, EXTERNAL, UNKNOWN = (
    "definition", "import", "builtin", "unique name", "external", "unknown")


def last_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return last_name(node.func)
    return None


def is_chain(node: ast.AST | None) -> bool:
    """A name or an attribute chain on a name (a.b.c)."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return isinstance(node, ast.Name)


def absolute_module(module: str | None, level: int, modname: str | None, is_pkg: bool) -> str | None:
    """The dotted module an ImportFrom names, or None when a relative import
    cannot be resolved (a module outside the package, or too many levels)."""
    if level == 0:
        return module
    if modname is None:
        return None
    parts = modname.split(".")
    if not is_pkg:
        parts = parts[:-1]
    if level - 1 > 0:
        if level - 1 > len(parts):
            return None
        parts = parts[:len(parts) - (level - 1)]
    if not parts:
        return None
    return ".".join(parts + ([module] if module else []))


def _collect_bindings(stmts: list, modname: str | None, is_pkg: bool, bindings: dict, stars: list,
                      class_prefix: str = "") -> None:
    """Bindings of the statements, with if/try/with bodies walked into; a later
    binding of a name replaces an earlier one. The handlers of a try statement
    are read before its body, so a name bound in both (an import with a
    fallback) keeps the binding of the body."""
    for s in stmts:
        if isinstance(s, ast.ClassDef):
            bindings[s.name] = ("class", modname, class_prefix + s.name)
        elif isinstance(s, ast.Import):
            for a in s.names:
                if a.asname:
                    bindings[a.asname] = ("module", a.name)
                else:
                    head = a.name.split(".")[0]
                    bindings[head] = ("module", head)
        elif isinstance(s, ast.ImportFrom):
            base = absolute_module(s.module, s.level, modname, is_pkg)
            for a in s.names:
                if a.name == "*":
                    stars.append(base)
                else:
                    bindings[a.asname or a.name] = ("from", base, a.name)
        elif isinstance(s, ast.Assign) and is_chain(s.value):
            for t in s.targets:
                if isinstance(t, ast.Name):
                    bindings[t.id] = ("alias", s.value)
        elif isinstance(s, ast.AnnAssign) and is_chain(s.value) and isinstance(s.target, ast.Name):
            bindings[s.target.id] = ("alias", s.value)
        elif isinstance(s, ast.If):
            _collect_bindings(s.body + s.orelse, modname, is_pkg, bindings, stars, class_prefix)
        elif isinstance(s, ast.Try) or type(s).__name__ == "TryStar":
            first = [x for h in s.handlers for x in h.body]
            _collect_bindings(first + s.body + s.orelse + s.finalbody, modname, is_pkg, bindings,
                              stars, class_prefix)
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            _collect_bindings(s.body, modname, is_pkg, bindings, stars, class_prefix)


class Module:
    """1 parsed file: its dotted name (None for a test module outside the
    package directory), its module-level bindings and its star imports."""

    def __init__(self, name: str | None, path: Path, tree: ast.Module, is_pkg: bool) -> None:
        self.name = name
        self.path = path
        self.tree = tree
        self.is_pkg = is_pkg
        self.bindings: dict[str, tuple] = {}
        self.stars: list[str | None] = []
        _collect_bindings(tree.body, name, is_pkg, self.bindings, self.stars)
        self.scopes = enclosing_functions(tree)
        self._local: dict[int, dict] = {}

    def local_bindings(self, fn: ast.AST) -> dict[str, tuple]:
        """Import statements anywhere in the body of a function (nested
        functions and classes aside) and the classes it defines."""
        key = id(fn)
        if key not in self._local:
            out: dict[str, tuple] = {}
            prefix = self.scopes.get(id(fn), ("", []))[0] + fn.name + ".<locals>."
            for node in own_nodes(fn, (ast.Import, ast.ImportFrom)):
                _collect_bindings([node], self.name, self.is_pkg, out, [])
            for node in _own_classes(fn):
                out[node.name] = ("class", self.name, prefix + node.name)
            self._local[key] = out
        return self._local[key]

    def declared_all(self) -> list[str] | None:
        """The names of a literal `__all__`, or None when the module has none."""
        for s in self.tree.body:
            if (isinstance(s, (ast.Assign, ast.AnnAssign))
                    and any(isinstance(t, ast.Name) and t.id == "__all__"
                            for t in (s.targets if isinstance(s, ast.Assign) else [s.target]))
                    and isinstance(s.value, (ast.List, ast.Tuple))
                    and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in s.value.elts)):
                return [e.value for e in s.value.elts]
        return None


def _own_classes(fn: ast.AST) -> list[ast.ClassDef]:
    """Class statements in a function body, not inside nested functions or classes."""
    out: list[ast.ClassDef] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                out.append(child)
            elif not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                visit(child)

    visit(fn)
    return out


def enclosing_functions(tree: ast.Module) -> dict[int, tuple[str, list]]:
    """id(node) -> (qualified-name prefix, enclosing functions innermost first)
    for every function and class statement of a module. The prefix follows
    Python's __qualname__ (a function adds `.<locals>`)."""
    out: dict[int, tuple[str, list]] = {}

    def walk(node: ast.AST, prefix: str, fns: list) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                out[id(child)] = (prefix, fns)
                walk(child, f"{prefix}{child.name}.", fns)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[id(child)] = (prefix, fns)
                walk(child, f"{prefix}{child.name}.<locals>.", [child] + fns)
            else:
                walk(child, prefix, fns)

    walk(tree, "", [])
    return out


class Resolution:
    """The result of resolving a class expression."""

    __slots__ = ("kind", "label", "name")

    def __init__(self, kind: str, label: str | None, name: str | None) -> None:
        self.kind, self.label, self.name = kind, label, name


class ModuleTable:
    """Every module of the package directory, every class statement in them,
    and the resolution of class expressions (names and attribute chains)."""

    def __init__(self, subject: dict, root: Path) -> None:
        root = Path(root)
        self.root = root
        self.src = root / subject.get("source_root", ".")
        self.pkg = package_dir(subject, root)
        self.package = subject["package"]
        self.modules: dict[str, Module] = {}
        self.namespaces: set[str] = set()
        self.by_path: dict[str, Module] = {}
        self.class_list: list[tuple[str, str, ast.ClassDef, list, Module]] = []
        if self.pkg.is_dir():
            for d in [self.pkg] + sorted(p for p in self.pkg.rglob("*") if p.is_dir()):
                if not (d / "__init__.py").is_file():
                    self.namespaces.add(".".join(d.relative_to(self.src).parts))
        for path in sorted(self.pkg.rglob("*.py")):
            parts = list(path.relative_to(self.src).with_suffix("").parts)
            is_pkg = parts[-1] == "__init__"
            if is_pkg:
                parts = parts[:-1]
            name = ".".join(parts)
            if name in self.modules:
                continue
            try:
                tree = ast.parse(read_source(path))
            except (SyntaxError, UnicodeDecodeError, ValueError):
                continue
            mod = Module(name, path, tree, is_pkg)
            self.modules[name] = mod
            self.by_path[str(path.resolve())] = mod
        for name, mod in self.modules.items():
            for node in ast.walk(mod.tree):
                if isinstance(node, ast.ClassDef):
                    prefix, fns = mod.scopes[id(node)]
                    self.class_list.append((name, prefix + node.name, node, fns, mod))
        self.by_key = {(m, q): node for m, q, node, _, _ in self.class_list}
        self.by_bare: dict[str, list[tuple[str, str]]] = {}
        for m, q, node, _, _ in self.class_list:
            self.by_bare.setdefault(node.name, []).append((m, q))
        self.bare_names = frozenset(self.by_bare)
        self._exports: dict[str, frozenset[str]] = {}

    # -- modules --------------------------------------------------------------------

    def exports(self, name: str) -> frozenset[str]:
        """The names `from module import *` binds: a literal `__all__`, else the
        names the module binds that do not start with an underscore, those it
        gets through its own star imports from package modules included."""
        if name not in self._exports:
            self._exports[name] = frozenset(self._export_names(name, set()))
        return self._exports[name]

    def _export_names(self, name: str, visited: set) -> set[str]:
        mod = self.modules.get(name)
        if mod is None or name in visited:
            return set()
        visited.add(name)
        declared = mod.declared_all()
        if declared is not None:
            return set(declared)
        out = {n for n in mod.bindings if not n.startswith("_")}
        for star in mod.stars:
            if star is not None:
                out |= {n for n in self._export_names(star, visited) if not n.startswith("_")}
        return out

    def is_package_module(self, name: str | None) -> bool:
        return name is not None and (name in self.modules or name in self.namespaces)

    def module_for(self, path: Path, tree: ast.Module | None = None) -> Module:
        """The module of a file: a package module, or a module outside the
        package directory with its own bindings and no relative imports."""
        found = self.by_path.get(str(Path(path).resolve()))
        if found is not None:
            return found
        if tree is None:
            tree = ast.parse(read_source(path))
        return Module(None, Path(path), tree, False)

    # -- labels -----------------------------------------------------------------------

    def label(self, module: str, qualname: str) -> str:
        """The bare name when no other class statement of the package and no
        built-in has it, else `<module>.<qualified name>`: a package class
        named like a built-in never takes the built-in's label."""
        bare = qualname.rsplit(".", 1)[-1]
        if len(self.by_bare.get(bare, [])) == 1 and bare not in BUILTIN_NAMES:
            return bare
        return f"{module}.{qualname}"

    # -- resolution -------------------------------------------------------------------

    def resolve(self, mod: Module, expr: ast.AST | None, scopes: list | None = None,
                fallback: bool = True) -> Resolution:
        """Resolve a class expression in a module, inside the given enclosing
        functions (innermost first). Kinds: definition, import, builtin,
        external, unique name (the fallback) and unknown. The fallback is not
        used for a class statement of a module outside the package, nor for a
        name that a built-in has; an unknown expression is labelled `?name`."""
        scopes = scopes or []
        bare = last_name(expr) if expr is not None else None
        res, hop = (("unknown", None), False)
        if is_chain(expr):
            res, hop = self._expr(mod, expr, scopes, set())
        if res[0] == "class":
            m, q = res[1]
            return Resolution(IMPORT if hop else DEFINITION, self.label(m, q), q.rsplit(".", 1)[-1])
        if res[0] == "builtin":
            return Resolution(BUILTIN, res[1], res[1])
        if res[0] == "external":
            return Resolution(EXTERNAL, res[1], res[1].rsplit(".", 1)[-1])
        if (fallback and res[0] != "foreign" and bare is not None and bare not in BUILTIN_NAMES
                and len(self.by_bare.get(bare, [])) == 1):
            m, q = self.by_bare[bare][0]
            return Resolution(UNIQUE, self.label(m, q), bare)
        return Resolution(UNKNOWN, f"?{bare}" if bare is not None else None, bare)

    def _module_value(self, dotted: str) -> tuple:
        if self.is_package_module(dotted):
            return ("module", dotted)
        return ("external", dotted)

    def _expr(self, mod: Module, expr: ast.AST, scopes: list, seen: set) -> tuple[tuple, bool]:
        if isinstance(expr, ast.Name):
            return self._name(mod, expr.id, scopes, seen)
        if isinstance(expr, ast.Attribute):
            base, hop = self._expr(mod, expr.value, scopes, seen)
            value, hop2 = self._attr(base, expr.attr, seen)
            return value, hop or hop2
        return ("unknown", None), False

    def _name(self, mod: Module, name: str, scopes: list, seen: set) -> tuple[tuple, bool]:
        for fn in scopes:
            b = mod.local_bindings(fn).get(name)
            if b is not None:
                key = (mod.name, id(fn), name)
                if key in seen:
                    return ("unknown", None), False
                seen.add(key)
                return self._binding(mod, b, seen)
        key = (mod.name, id(mod), name)
        if key in seen:
            return ("unknown", None), False
        seen.add(key)
        b = mod.bindings.get(name)
        if b is not None:
            return self._binding(mod, b, seen)
        for star in reversed(mod.stars):
            if star in self.modules and name in self.exports(star):
                value, _ = self._attr(("module", star), name, seen)
                return value, True
        if name in BUILTIN_NAMES:
            return ("builtin", name), False
        return ("unknown", None), False

    def _binding(self, mod: Module, b: tuple, seen: set) -> tuple[tuple, bool]:
        if b[0] == "class":
            if b[1] is None:  # a class statement of a module outside the package
                return ("foreign", None), False
            return ("class", (b[1], b[2])), False
        if b[0] == "module":
            return self._module_value(b[1]), True
        if b[0] == "from":
            if b[1] is None:
                return ("unknown", None), True
            value, _ = self._attr(self._module_value(b[1]), b[2], seen)
            return value, True
        if b[0] == "alias":
            value, _ = self._expr(mod, b[1], [], seen)
            return value, True
        return ("unknown", None), False

    def _attr(self, base: tuple, attr: str, seen: set) -> tuple[tuple, bool]:
        kind = base[0]
        if kind == "module":
            name = base[1]
            m = self.modules.get(name)
            sub = f"{name}.{attr}"
            key = (name, id(m), attr)
            # a binding that leads back to itself (`from . import x` in the
            # package's own __init__.py) falls through to the submodule
            if m is not None and key not in seen:
                if attr in m.bindings:
                    seen.add(key)
                    value, hop = self._binding(m, m.bindings[attr], seen)
                    if value[0] != "unknown" or not self.is_package_module(sub):
                        return value, hop
                else:
                    for star in reversed(m.stars):
                        if star in self.modules and attr in self.exports(star):
                            seen.add(key)
                            value, _ = self._attr(("module", star), attr, seen)
                            return value, True
            if self.is_package_module(sub):
                return ("module", sub), False
            return ("unknown", None), False
        if kind == "external":
            sub = f"{base[1]}.{attr}"
            if self.is_package_module(sub):
                return ("module", sub), False
            if base[1] == "builtins" and attr in BUILTIN_NAMES:
                return ("builtin", attr), False
            return ("external", sub), False
        if kind == "class":
            m, q = base[1]
            if (m, f"{q}.{attr}") in self.by_key:
                return ("class", (m, f"{q}.{attr}")), False
            return ("unknown", None), False
        if kind == "foreign":  # an attribute of a class of a module outside the package
            return ("foreign", None), False
        return ("unknown", None), False

    # -- the class table ----------------------------------------------------------------

    def classes(self) -> dict[str, dict]:
        """Label -> entry for every class statement of the package; see class_info."""
        out: dict[str, dict] = {}
        for m, q, node, fns, mod in self.class_list:
            declared: list[str] = []
            for b in node.bases:
                if is_chain(b):
                    lab = self.resolve(mod, b, fns).label
                else:
                    lab = last_name(b)
                    lab = f"?{lab}" if lab else None
                if lab and lab not in declared:
                    declared.append(lab)
            entry = {"module": m, "qualname": q, "name": node.name, "bases": sorted(declared),
                     "bases_declared": declared, "defines": [], "init_attrs": {},
                     "init_params": None}
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name not in entry["defines"]:
                        entry["defines"].append(item.name)
                    if item.name == "__init__":
                        params = [a.arg for a in item.args.posonlyargs + item.args.args][1:]
                        entry["init_params"] = params
                        for sub in ast.walk(item):
                            if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                                    and isinstance(sub.targets[0], ast.Attribute)
                                    and isinstance(sub.targets[0].value, ast.Name)
                                    and sub.targets[0].value.id == "self"
                                    and isinstance(sub.value, ast.Name)
                                    and sub.value.id in params):
                                entry["init_attrs"][sub.targets[0].attr] = params.index(sub.value.id)
            entry["defines"].sort()
            out[self.label(m, q)] = entry
        return dict(sorted(out.items()))

    def rejection_bases(self, names: list[str], classes: dict) -> list[dict]:
        """The rejection bases of subject.json, each a package class (by its
        label) or a built-in class; anything else stops the step."""
        out = []
        for name in names:
            if name in classes:
                e = classes[name]
                out.append({"name": name, "kind": "package", "module": e["module"],
                            "qualname": e["qualname"]})
            elif name in BUILTIN_NAMES and isinstance(getattr(builtins, name), type):
                out.append({"name": name, "kind": "builtin", "module": "builtins", "qualname": name})
            else:
                same = sorted(lab for lab, e in classes.items() if e["name"] == name.rsplit(".", 1)[-1])
                hint = (f"; the package classes of this bare name are labelled {', '.join(same)}"
                        if same else "")
                raise SystemExit(f"rejection base {name!r} is neither the label of exactly 1 package "
                                 f"class nor a built-in class{hint}")
        return out


def class_info(pkg: Path) -> dict[str, dict]:
    """Label -> {"module", "qualname", "name" (bare), "bases" (labels, sorted),
    "bases_declared" (labels, in declaration order), "defines": [...],
    "init_params": [...] or None when the class has no __init__, "init_attrs":
    {attr: param index}} for every class statement in the package directory
    `pkg`, 1 entry per statement. A class is labelled by its bare name when no
    other class statement of the package has that name, else by
    `<module>.<qualified name>`."""
    pkg = Path(pkg).resolve()
    return ModuleTable({"package": pkg.name, "source_root": str(pkg.parent)}, Path("/")).classes()


def mro(name: str, classes: dict, _stack: tuple = ()) -> list[str]:
    """Method-resolution order of a class known by label: C3 over the declared
    bases; depth first, left to right, when C3 fails. A class outside
    `classes` is its own order."""
    entry = classes.get(name)
    if entry is None or name in _stack:
        return [name]
    bases = list(entry.get("bases_declared", entry.get("bases", [])))
    seqs = [mro(b, classes, _stack + (name,)) for b in bases] + [list(bases)]
    out = [name]
    while True:
        seqs = [s for s in seqs if s]
        if not seqs:
            return out
        head = None
        for s in seqs:
            if not any(s[0] in t[1:] for t in seqs):
                head = s[0]
                break
        if head is None:
            return _depth_first(name, classes)
        out.append(head)
        seqs = [s[1:] if s[0] == head else s for s in seqs]


def _depth_first(name: str, classes: dict) -> list[str]:
    out: list[str] = []

    def visit(n: str) -> None:
        if n in out:
            return
        out.append(n)
        entry = classes.get(n, {})
        for b in entry.get("bases_declared", entry.get("bases", [])):
            visit(b)

    visit(name)
    return out


def builtin_class(name: str | None) -> type | None:
    """The built-in class of that name, or None."""
    obj = getattr(builtins, name, None) if name in BUILTIN_NAMES else None
    return obj if isinstance(obj, type) else None


def ancestors(name: str, classes: dict[str, dict]) -> list[str]:
    """The class and its ancestors known by label, breadth first, no repeats:
    the declared bases of a class of the package and the bases of a built-in
    class. A label of the package is never the name of a built-in."""
    seen, queue = [], [name]
    while queue:
        n = queue.pop(0)
        if n in seen:
            continue
        seen.append(n)
        if n in classes:
            queue += classes[n].get("bases", [])
        else:
            obj = builtin_class(n)
            if obj is not None:
                queue += [b.__name__ for b in obj.__bases__]
    return seen


def is_rejection(name: str | None, classes: dict, bases: list[str]) -> bool:
    """A rejection base, a class of the package that inherits from one, or a
    built-in class that inherits from a built-in rejection base. A class from
    outside the package and an expression that names no class are not."""
    if not name:
        return False
    return any(b in ancestors(name, classes) for b in bases)


def is_subclass(name: str, of: str, classes: dict) -> bool:
    return of in ancestors(name, classes)


# -- functions and raise statements -------------------------------------------

def functions(tree: ast.Module) -> dict[str, ast.AST]:
    """Qualified name -> definition: module functions, methods (nested classes
    too), functions nested in functions, and definitions under `if`/`try`.
    Every definition is kept: the first definition of a qualified name keeps
    the name, the k-th (k >= 2) in the same scope is `<qualified name>~k` (a
    property getter and its setter, `@overload` stubs and the implementation)."""
    found: dict[str, ast.AST] = {}
    count: dict[str, int] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = prefix + child.name
                count[qual] = count.get(qual, 0) + 1
                if count[qual] > 1:
                    qual = f"{qual}~{count[qual]}"
                found[qual] = child
                walk(child, f"{qual}.")
            elif isinstance(child, (ast.If, ast.Try, ast.With)) or type(child).__name__ == "TryStar":
                walk(child, prefix)

    walk(tree, "")
    return found


def plain_name(qual: str) -> str:
    """The bare function name of a qualified name, without a `~k` suffix."""
    return qual.rsplit(".", 1)[-1].split("~", 1)[0]


def own_nodes(fn: ast.AST, kind) -> list[ast.AST]:
    """Nodes of `kind` in a function, not inside nested functions, classes or lambdas."""
    out: list[ast.AST] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(child, kind):
                out.append(child)
            visit(child)

    visit(fn)
    return sorted(out, key=lambda n: (n.lineno, n.col_offset))


def parents_of(fn: ast.AST) -> dict[ast.AST, ast.AST]:
    out = {}
    for node in ast.walk(fn):
        for child in ast.iter_child_nodes(node):
            out[child] = node
    return out


def except_names(fn: ast.AST) -> set[str]:
    return {h.name for h in ast.walk(fn) if isinstance(h, ast.ExceptHandler) and h.name}


_PERCENT = re.compile(r"%(?:\([^)]*\))?[-#0 +]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[hlL]?[diouxXeEfFgGcrsa%]")


def _split_percent(text: str) -> list:
    parts: list = []
    pos = 0
    for m in _PERCENT.finditer(text):
        parts.append(text[pos:m.start()])
        parts.append("%" if m.group() == "%%" else None)
        pos = m.end()
    parts.append(text[pos:])
    return parts


def _split_format(text: str) -> list:
    parts: list = []
    buf, i = "", 0
    while i < len(text):
        c = text[i]
        if c in "{}" and text[i:i + 2] in ("{{", "}}"):
            buf += c
            i += 2
            continue
        if c == "{":
            j = text.find("}", i)
            if j < 0:
                buf += text[i:]
                break
            parts += [buf, None]
            buf, i = "", j + 1
            continue
        buf += c
        i += 1
    parts.append(buf)
    return parts


def template_parts(node: ast.AST | None) -> list:
    """Literal strings and None (a placeholder), in order."""
    if node is None:
        return []
    if isinstance(node, ast.Constant):
        return [node.value if isinstance(node.value, str) else repr(node.value)]
    if isinstance(node, ast.JoinedStr):
        out: list = []
        for v in node.values:
            out += [v.value] if isinstance(v, ast.Constant) else [None]
        return out
    if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)
            and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)):
        return _split_percent(node.left.value)
    if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
        return template_parts(node.left) + template_parts(node.right)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format" and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)):
        return _split_format(node.func.value.value)
    return [None]


def normalise_parts(parts: list) -> list:
    out: list = []
    for p in parts:
        if p == "":
            continue
        if out and isinstance(p, str) and isinstance(out[-1], str):
            out[-1] += p
        elif out and p is None and out[-1] is None:
            continue
        else:
            out.append(p)
    return out


def template_text(parts: list) -> str:
    return "".join(PLACEHOLDER if p is None else p for p in parts)


def guard_of(node: ast.AST, parents: dict, fn: ast.AST) -> ast.AST | None:
    cur = node
    while cur is not fn and cur in parents:
        par = parents[cur]
        if isinstance(par, ast.If) and cur is not par.test:
            return par
        if isinstance(par, ast.ExceptHandler):
            return par
        cur = par
    return None


def guard_text(g: ast.AST | None) -> str | None:
    if g is None:
        return None
    if isinstance(g, ast.If):
        return ast.unparse(g.test)
    head = "except"
    if g.type is not None:
        head += " " + ast.unparse(g.type)
    if g.name:
        head += " as " + g.name
    return head


def words_of(node: ast.AST | None) -> list[str]:
    """Identifiers and string literals of an expression (or an except header)."""
    if node is None:
        return []
    if isinstance(node, ast.If):
        node = node.test
    out: list[str] = []
    if isinstance(node, ast.ExceptHandler):
        if node.name:
            out.append(node.name)
        node = node.type
        if node is None:
            return out
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            out.append(sub.id)
        elif isinstance(sub, ast.Attribute):
            out.append(sub.attr)
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append(sub.value)
    return out


def raise_call(node: ast.Raise) -> ast.Call | None:
    return node.exc if isinstance(node.exc, ast.Call) else None


def raised_class(node: ast.Raise) -> str | None:
    if node.exc is None:
        return None
    return last_name(node.exc)


def constructed_names(fn: ast.AST) -> dict[str, ast.Call]:
    """Local names the function binds exactly once, by an assignment from a call."""
    count: dict[str, int] = {}
    value: dict[str, ast.Call] = {}
    for node in own_nodes(fn, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr, ast.For,
                               ast.AsyncFor, ast.With, ast.AsyncWith)):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            targets = [i.optional_vars for i in node.items if i.optional_vars is not None]
        else:
            targets = [node.target]
        for t in targets:
            for sub in ast.walk(t):
                if isinstance(sub, ast.Name):
                    count[sub.id] = count.get(sub.id, 0) + 1
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call)):
            value[node.targets[0].id] = node.value
    return {name: call for name, call in value.items() if count.get(name) == 1}


def message_argument(call: ast.Call | None, cls: str | None, classes: dict) -> ast.AST | None:
    """The argument that carries the message: the first positional argument, or,
    when the call has none, the keyword argument named as the first parameter
    of the nearest __init__ in the class's method-resolution order."""
    if call is None:
        return None
    if call.args:
        return call.args[0]
    for name in mro(cls, classes) if cls else []:
        params = classes.get(name, {}).get("init_params")
        if params is not None:
            for k in call.keywords:
                if params and k.arg == params[0]:
                    return k.value
            return None
    return None


def other_literals(call: ast.Call | None) -> list[str]:
    if call is None:
        return []
    out = []
    rest = list(call.args[1:]) + [k.value for k in call.keywords]
    for arg in rest:
        for sub in ast.walk(arg):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                out.append(sub.value)
    return out


def literal_args(call: ast.Call | None) -> dict:
    """Literal arguments of the raise call: {"pos": {index: value}, "kw": {name: value}}."""
    pos, kw = {}, {}
    if call is not None:
        for i, a in enumerate(call.args):
            if isinstance(a, ast.Constant):
                pos[str(i)] = a.value
        for k in call.keywords:
            if k.arg and isinstance(k.value, ast.Constant):
                kw[k.arg] = k.value.value
    return {"pos": pos, "kw": kw}


# -- reachability -------------------------------------------------------------

def referenced_names(fn: ast.AST) -> set[str]:
    """Names a function refers to: f(...) and every attribute reference x.f."""
    out = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            out.add(node.func.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
    return out


def reachable_functions(fns: dict[tuple[str, str], ast.AST], entry_points: list[str]) -> set:
    by_name: dict[str, list] = {}
    for key in fns:
        by_name.setdefault(plain_name(key[1]), []).append(key)
    todo = sorted(k for k in fns if plain_name(k[1]) in entry_points)
    seen = set(todo)
    while todo:
        key = todo.pop()
        for name in sorted(referenced_names(fns[key])):
            for other in by_name.get(name, []):
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
    return seen


# -- checks ---------------------------------------------------------------------

def raised_expression(node: ast.Raise) -> ast.AST | None:
    """The expression that names the class a raise statement constructs."""
    if node.exc is None:
        return None
    return node.exc.func if isinstance(node.exc, ast.Call) else node.exc


def enumerate_checks(subject: dict, root: Path) -> dict:
    root = Path(root)
    table = ModuleTable(subject, root)
    classes = table.classes()
    bases_doc = table.rejection_bases(subject["rejection_bases"], classes)
    bases = [b["name"] for b in bases_doc]
    files = list(subject["subject_files"]) + list(subject.get("observed_files", []))
    mods = {rel: table.module_for(root / rel_to_source(subject, rel)) for rel in files}
    fns = {(rel, q): node for rel, mod in mods.items() for q, node in functions(mod.tree).items()}
    reach = reachable_functions(fns, subject["entry_points"])

    checks, others = [], []
    for (rel, qual), fn in sorted(fns.items(), key=lambda kv: (kv[0][0], kv[1].lineno, kv[0][1])):
        mod = mods[rel]
        scopes = [fn] + mod.scopes.get(id(fn), ("", []))[1]
        parents = parents_of(fn)
        bound = except_names(fn)
        constructed = constructed_names(fn)
        groups: dict[tuple, dict] = {}
        order: list[tuple] = []
        for k, node in enumerate(own_nodes(fn, ast.Raise), 1):
            cls = raised_class(node)
            call = raise_call(node)
            expr = raised_expression(node)
            via = None
            if (isinstance(node.exc, ast.Name) and node.exc.id in constructed
                    and node.exc.id not in bound and node.exc.id not in table.bare_names):
                via = node.exc.id  # raise name, where name = Class(...) once in this function
                call = constructed[via]
                cls = last_name(call.func)
                expr = call.func
            res = table.resolve(mod, expr, scopes) if expr is not None else None
            guard = guard_of(node, parents, fn)
            base = {"line": node.lineno, "end_line": node.end_lineno, "raise_number": k,
                    "guard": guard_text(guard), "via": via}
            kind = None
            if node.exc is None:
                kind = "bare raise"
            elif (isinstance(node.exc, ast.Name) and node.exc.id in bound
                  and node.exc.id not in table.bare_names):
                kind = "re-raise of a bound exception"
            elif (res is None or res.kind in (EXTERNAL, UNKNOWN)
                  or not is_rejection(res.label, classes, bases)):
                kind = "not a rejection class"
            if kind is not None:
                others.append({"file": rel, "function": qual, "class": cls,
                               "class_resolved": res.label if res is not None else None,
                               "reason": kind, "source": ast.unparse(node), **base})
                continue
            label = res.label
            parts = normalise_parts(template_parts(message_argument(call, label, classes)))
            text = template_text(parts)
            gkey = (label, text)
            if gkey not in groups:
                order.append(gkey)
                groups[gkey] = {"class": label, "class_name": res.name, "template": text,
                                "template_parts": parts, "raises": [], "guard_words": [],
                                "other_literals": [], "literal_args": [], "n_positional": [],
                                "has_keywords": False, "resolution": set()}
            g = groups[gkey]
            g["raises"].append(base)
            g["resolution"].add(res.kind)
            g["guard_words"] += words_of(guard)
            g["other_literals"] += other_literals(call)
            g["literal_args"].append(literal_args(call))
            g["n_positional"].append(len(call.args) if call is not None else 0)
            g["has_keywords"] = g["has_keywords"] or bool(call is not None and call.keywords)
        stem = module_label(subject, rel)
        for n, gkey in enumerate(order, 1):
            g = groups[gkey]
            cls_name = qual.rsplit(".", 1)[0] if "." in qual else None
            checks.append({
                "id": f"{stem}.{qual}#{n}",
                "file": rel,
                "role": "subject" if rel in subject["subject_files"] else "observed",
                "function": qual,
                "function_name": plain_name(qual),
                "owner_class": cls_name,
                "class": g["class"],
                "class_name": g["class_name"],
                "class_resolution": sorted(g["resolution"]),
                "template": g["template"],
                "template_parts": g["template_parts"],
                "has_placeholder": any(p is None for p in g["template_parts"]),
                "raise_numbers": [r["raise_number"] for r in g["raises"]],
                "lines": [[r["line"], r["end_line"]] for r in g["raises"]],
                "guards": [r["guard"] for r in g["raises"]],
                "via_variable": [r["via"] for r in g["raises"]],
                "guard_words": sorted(set(g["guard_words"])),
                "other_literals": sorted(set(g["other_literals"])),
                "literal_args": g["literal_args"],
                "n_positional": g["n_positional"],
                "has_keywords": g["has_keywords"],
                "reachable": (rel, qual) in reach,
            })
    return {
        "subject": {k: subject[k] for k in sorted(subject)},
        "sha256": {rel: sha256(root / rel_to_source(subject, rel)) for rel in sorted(files)},
        "classes": classes,
        "rejection_bases": bases_doc,
        "rejection_classes": sorted(n for n in classes if is_rejection(n, classes, bases)),
        "functions": [{"file": rel, "function": q, "reachable": (rel, q) in reach}
                      for rel, q in sorted(fns)],
        "checks": checks,
        "other_raises": others,
    }


def line_index(checks_doc: dict) -> dict[str, dict[int, dict]]:
    """file -> line -> {"check": id or None, "raise": raise number, "function": ...}
    for every raise statement line of every check and other raise."""
    out: dict[str, dict[int, dict]] = {}
    for c in checks_doc["checks"]:
        for (a, b), k in zip(c["lines"], c["raise_numbers"]):
            for line in range(a, b + 1):
                out.setdefault(c["file"], {})[line] = {"check": c["id"], "raise": k,
                                                       "function": c["function"]}
    for o in checks_doc["other_raises"]:
        for line in range(o["line"], o["end_line"] + 1):
            out.setdefault(o["file"], {})[line] = {"check": None, "raise": o["raise_number"],
                                                   "function": o["function"]}
    return out

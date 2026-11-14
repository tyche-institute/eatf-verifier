"""What materialize.py, run_mutants.py and analyse_mutants.py share.

The toolkit of `../target-reach/` is imported, not copied: its folder is put
on `sys.path` and its modules are imported as the package `reach`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # mutants/
EXPERIMENT = HERE.parent                           # target-reach-followup/
TOOLKIT = EXPERIMENT.parent / "target-reach"       # the toolkit, read only
REFERENCE = EXPERIMENT.parent / "mutation-adequacy-pyjwt"
if str(TOOLKIT) not in sys.path:
    sys.path.insert(0, str(TOOLKIT))

from reach import run as reach_run  # noqa: E402
from reach.checks import functions, load_json, rel_to_source, sha256  # noqa: E402

WORKERS = 10
DELETION = "check_deletion"     # the operator of a deletion mutant in mutants.csv


def subject_paths(subject: str) -> tuple[Path, dict]:
    """subject.json of a subject of the toolkit, given its path or its name."""
    path = Path(subject)
    if not path.suffix == ".json":
        path = TOOLKIT / "subjects" / subject / "subject.json"
    path = path.resolve()
    return path, load_json(path)


def default_work(name: str) -> Path:
    return EXPERIMENT / "work" / "mutants" / name


def default_out(name: str) -> Path:
    return EXPERIMENT / "generated" / "mutants" / name


def local_settings(name: str, clone: str | None, python: str | None) -> tuple[Path, Path]:
    """The clone and the interpreter of a subject: given, or as the toolkit's
    work/<name>/local.json names them."""
    local_path = TOOLKIT / "work" / name / "local.json"
    local = load_json(local_path) if local_path.exists() else {}
    clone = clone or local.get("clone")
    python = python or local.get("python")
    if not clone or not python:
        raise SystemExit(f"no clone or interpreter for {name}: give --clone and --python")
    return Path(clone), Path(python)


def context(subject_path: Path, work: Path, clone: Path, python: Path, workers: int = WORKERS):
    """A reach.run.Context whose work directory is `work` (records, copies and
    logs go there) and whose definitions are those beside subject.json."""
    args = argparse.Namespace(subject=str(subject_path), clone=str(clone), python=str(python),
                              work=str(work), defs=None, workers=workers, out=None, witnesses=None)
    return reach_run.Context(args)


def split_lines(text: str) -> list[str]:
    """Lines with their ends; only "\\n" ends a line (a form feed does not)."""
    return re.findall(r"[^\n]*\n|[^\n]+$", text)


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


PACKED = ("cases.csv", "runs.jsonl")     # outputs of analyse_mutants.py that are kept as <name>.xz


def write_packed(path: Path, text: str) -> str:
    """Write `text` as <path>.xz; the digest of the text itself is returned."""
    data = text.encode("utf-8")
    Path(str(path) + ".xz").write_bytes(lzma.compress(data, preset=9))
    if path.exists():
        path.unlink()
    return hashlib.sha256(data).hexdigest()


def read_packed(path: Path) -> str:
    """The text of <path>.xz."""
    return lzma.decompress(Path(str(path) + ".xz").read_bytes()).decode("utf-8")


def junit_key(nodeid: str, run_name: str) -> str:
    """The key that reach.run.junit_outcomes gives a test, from its pytest node
    id: `<run>|<module path with dots>[.<class>...]::<name>`. The parameters in
    brackets stay with the name."""
    head, bracket, params = nodeid.partition("[")
    parts = head.split("::")
    module = parts[0][:-3] if parts[0].endswith(".py") else parts[0]
    classname = ".".join([module.replace("/", ".")] + parts[1:-1])
    return f"{run_name}|{classname}::{parts[-1]}{bracket}{params}"


def owners(tree) -> list:
    """The functions mutmut mutates, in its order: module-level functions and the
    methods of module-level classes."""
    import ast
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((node, None))
        elif isinstance(node, ast.ClassDef):
            out += [(m, node.name) for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return out


def span(node) -> tuple[int, int]:
    """First and last line of a function definition, its decorators included."""
    first = min([node.lineno] + [d.lineno for d in node.decorator_list])
    return first, node.end_lineno


def qualified_names(tree) -> dict[int, str]:
    """Line of a `def` -> the qualified name the toolkit gives that function
    (reach.checks.functions: `Class.method`, `outer.inner`, `name~k`)."""
    return {node.lineno: name for name, node in functions(tree).items()}


def innermost_function(tree, lines: list[int]) -> str | None:
    """The qualified name of the innermost function whose span holds every line
    of `lines`, or None."""
    best = None
    for name, node in functions(tree).items():
        a, z = span(node)
        if all(a <= x <= z for x in lines):
            if best is None or (a, -z) > best[0]:
                best = ((a, -z), name)
    return best[1] if best else None


def need_python_312() -> None:
    if sys.version_info < (3, 12):
        raise SystemExit("Python 3.12 or later is needed")

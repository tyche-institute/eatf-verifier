"""Re-create the mutants of mutmut 3.8.1 for some source files, with mutmut's own generator.

Runs in an environment where mutmut 3.8.1 is importable, from a directory whose
pyproject.toml holds a [tool.mutmut] section (materialize.py writes it):

    <mutmut python> -I -B mutmut_generate.py --root ROOT --out OUT.jsonl FILE [FILE ...]

FILE is a path relative to ROOT, the directory that mutmut would treat as the
project root (the source root of the subject). For each FILE, 1 JSON line:

    {"file", "sha256", "mutmut_names": the names mutmut's own file generator
     (mutate_file_contents) yields, in its order,
     "mutants": [{"name", "function" (Class.method or function), "number",
                  "owner": the position of the function among the module-level
                           functions and the methods of module-level classes,
                  "operator", "original", "mutated",
                  "module_code": the whole file with this 1 mutation applied
                                 to mutmut's parsed module and rendered,
                  "mutmut_function": the function that mutmut writes for this
                                     mutant in its mutated file, renamed to
                                     the original name and rendered}]}

The mutants are enumerated as mutmut enumerates them when it writes a mutated
file: the mutations of each module-level function, and of each method of a
module-level class with an indented body, numbered from 1 in the order of
mutmut's visitor. Each mutation operator is wrapped so that it tags what it
yields with its own name (without the prefix `operator_`); the tags change
nothing that mutmut generates. Nothing is written except OUT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args(argv)

    import libcst as cst
    import mutmut
    import mutmut.mutation.file_mutation as fm
    from mutmut.mutation.diff_apply import read_mutant_function
    from mutmut.mutation.trampoline_templates import mangle_function_name
    from mutmut.utils.format_utils import get_mutant_name

    version = getattr(mutmut, "__version__", None)
    if version is None:
        import importlib.metadata as md
        version = md.version("mutmut")
    if version != "3.8.1":
        raise SystemExit(f"mutmut {version} is importable, not 3.8.1")

    tags: dict[int, str] = {}

    def tagged(name, fn):
        def wrapper(node):
            for out in fn(node):
                tags[id(out)] = name
                yield out
        return wrapper

    saved = fm.mutation_operators
    fm.mutation_operators = [(t, tagged(fn.__name__.removeprefix("operator_"), fn)) for t, fn in saved]
    root = Path(args.root)
    lines = []
    try:
        for rel in args.files:
            raw = (root / rel).read_bytes()
            code = raw.decode("utf-8")
            if code.startswith("﻿"):
                raise SystemExit(f"{rel}: a byte-order mark is not supported")
            mutated_file = fm.mutate_file_contents(rel, code)
            trampolined = cst.parse_module(mutated_file.code)
            module, mutations, _, _ = fm.create_mutations(rel, code, None, None)
            grouped = fm.group_by_top_level_node(mutations)
            owners = []
            for statement in module.body:
                if isinstance(statement, cst.FunctionDef):
                    owners.append((statement, None))
                elif isinstance(statement, cst.ClassDef) and isinstance(statement.body, cst.IndentedBlock):
                    owners += [(m, statement.name.value) for m in statement.body.body
                               if isinstance(m, cst.FunctionDef)]
            render = module.code_for_node
            mutants = []
            for owner, (fn, class_name) in enumerate(owners):
                mangled = mangle_function_name(name=fn.name.value, class_name=class_name) + "__mutmut"
                for i, mutation in enumerate(grouped.get(fn, ()), start=1):
                    name = get_mutant_name(Path(rel), f"{mangled}_{i}")
                    whole = fm.deep_replace(module, mutation.original_node, mutation.mutated_node)
                    theirs = read_mutant_function(trampolined, name)
                    mutants.append({
                        "name": name,
                        "function": f"{class_name}.{fn.name.value}" if class_name else fn.name.value,
                        "number": i,
                        "owner": owner,
                        "operator": tags[id(mutation.mutated_node)],
                        "original": render(mutation.original_node),
                        "mutated": render(mutation.mutated_node),
                        "module_code": whole.code,
                        "mutmut_function": trampolined.code_for_node(theirs.with_changes(leading_lines=[])),
                    })
            lines.append({"file": rel, "sha256": hashlib.sha256(raw).hexdigest(),
                          "mutmut_names": [get_mutant_name(Path(rel), n) for n in mutated_file.mutant_names],
                          "mutants": mutants, "mutmut_version": version})
    finally:
        fm.mutation_operators = saved
    out = Path(args.out)
    out.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in lines),
                   encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

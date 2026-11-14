"""Create the mutants of source files of a subject, 1 modified file each: the mutants of
mutmut 3.8.1, and the deletion of each check of those files.

    python3 -I -B mutants/materialize.py --subject NAME_OR_SUBJECT_JSON --files FILE [FILE ...]
        --mutmut-python PYTHON [--clone DIR] [--work DIR] [--out DIR]

FILE is a subject file as `checks.json` names it (relative to the source root).
PYTHON is an interpreter in whose environment mutmut 3.8.1 is importable; it
runs `mutmut_generate.py`, which re-creates every mutant with mutmut's own
generator and default operators (see that file). This program uses the
standard library only.

For each mutant, the modified file is the unmodified file in which the
function that mutmut mutated is replaced by the mutant function, and every
line keeps its number. The mutated function comes from mutmut's parsed module
with this 1 mutation applied (all other text is the file's own). Where the
mutation takes k lines fewer than the text it replaces, k blank lines follow
the new text; where the last line of the new text ends in a backslash that
continues the statement, the k lines hold a backslash each, so that the
statement goes on. A mutation that takes more lines than the text it replaces
cannot keep the line numbers and fails sentinel S1.

A deletion mutant is the unmodified file in which every raise statement of 1
check is replaced by `pass`. The toolkit's own function makes it
(reach.delete.delete_check, which keeps every line number): it is the copy
that the toolkit's step `deletions` runs for the check. Every check that
`checks.json` lists in a mutated file gets 1, reachable or not. The mutants of
mutmut are M00001 ..., the deletions D00001 ... (in the order of the files,
then of the first raise line of the check, then of the check's id), with the
operator `check_deletion` and the check's id in the column `check`.

Writes:
    <work>/mutated/<id>.py      the modified file of each mutant
    <work>/manifest.json        id -> file, function, sha256, path of the modified file, check
    <work>/generator.jsonl      the raw output of mutmut_generate.py
    <out>/mutants.csv           1 row per mutant
    <out>/materialize.json      counts per file and operator, and sentinels S1 and S2

Sentinels (the program writes its outputs, then exits 1 when 1 does not hold):
    S1  each modified file (of a mutant of mutmut or of a deletion) differs
        from the unmodified file only inside the span of the mutated function
        (for a deletion: the function of the check), has the same number of
        lines, compiles, and is not the unmodified file; a deletion changes
        the lines of the check's raise statements and no other line
    S2  the mutated function of each modified file of a mutant of mutmut has
        the same syntax tree as the function mutmut writes for that mutant
        (names set equal), and the number of such mutants of each file equals
        the number mutmut's own file generator yields for it, with the same
        names in the same order
"""

from __future__ import annotations

import argparse
import ast
import csv
import difflib
import hashlib
import io
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (DELETION, default_out, default_work, digest_text, dump, functions, load_json,  # noqa: E402
                    local_settings, need_python_312, owners, qualified_names, rel_to_source, span,
                    split_lines, subject_paths)
from reach.delete import delete_check  # noqa: E402

GENERATOR = Path(__file__).resolve().parent / "mutmut_generate.py"
MUTANTS_HEADER = ["mutant", "file", "function", "mutmut_function", "function_lines", "changed_lines",
                  "operator", "mutmut_name", "sha256", "original", "mutated", "check"]


class Problem(Exception):
    pass


def place(original: str, module_code: str, first: int, last: int) -> tuple[str, list[int], int]:
    """The modified file: `original` with lines first..last (1-based, the span of
    the mutated function) replaced by the corresponding lines of `module_code`,
    padded so that every line keeps its number. Returns the text, the changed
    line numbers and the number of blank lines added."""
    old, new = split_lines(original), split_lines(module_code)
    delta = len(new) - len(old)
    if new[:first - 1] != old[:first - 1] or new[last + delta:] != old[last:]:
        raise Problem("mutmut's module differs from the file outside the mutated function")
    a, b = old[first - 1:last], new[first - 1:last + delta]
    out: list[str] = []
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out += a[i1:i2]
            continue
        p, q = i2 - i1, j2 - j1
        if q > p:
            raise Problem(f"the mutation takes {q} lines where the function had {p}")
        new = b[j1:j2]
        # a line that ends in a backslash continues on the next line: the padding
        # then continues it too, with lines that hold only a backslash
        last_line = new[-1] if new else (out[-1] if out else "")
        pad = "\\\n" if last_line.rstrip("\r\n").endswith("\\") else "\n"
        out += new + [pad] * (p - q)
    if len(out) != len(a):
        raise Problem("the placed function does not have the number of lines of the original")
    text = "".join(old[:first - 1] + out + old[last:])
    lines = split_lines(text)
    changed = [i + 1 for i, (x, y) in enumerate(zip(old, lines)) if x != y]
    return text, changed, -delta


def function_dump(node: ast.AST, name: str) -> str:
    node.name = name
    return ast.dump(node)


def mutmut_function_dump(code: str, name: str) -> str:
    tree = ast.parse(code)
    if len(tree.body) != 1 or not isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise Problem("mutmut's mutant function does not parse as 1 function")
    return function_dump(tree.body[0], name)


def ranges(lines: list[int]) -> str:
    """[3, 4, 5, 9] -> '3-5;9'."""
    out, start, prev = [], None, None
    for x in lines:
        if start is None:
            start = prev = x
        elif x == prev + 1:
            prev = x
        else:
            out.append(f"{start}-{prev}" if prev != start else str(start))
            start = prev = x
    if start is not None:
        out.append(f"{start}-{prev}" if prev != start else str(start))
    return ";".join(out)


def materialize(generated: list[dict], root: Path, files: list[str], subject: dict
                ) -> tuple[list[dict], dict[str, str], dict]:
    """(rows of mutants.csv, id -> modified text, report with sentinels)."""
    rows, texts = [], {}
    s1, s2, per_file, padded = [], [], {}, {}
    by_file = {g["file"]: g for g in generated}
    n = 0
    for rel in files:
        g = by_file[rel_to_source(subject, rel)]
        raw = (root / g["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != g["sha256"]:
            raise SystemExit(f"{rel}: the file changed while the mutants were generated")
        original = raw.decode("utf-8")
        tree = ast.parse(original)
        mine = owners(tree)
        quals = qualified_names(tree)
        names = [m["name"] for m in g["mutants"]]
        if names != g["mutmut_names"]:
            s2.append(f"{rel}: {len(names)} mutants re-created, mutmut's file generator yields "
                      f"{len(g['mutmut_names'])}, or in another order")
        operators = Counter()
        for m in g["mutants"]:
            n += 1
            mid = f"M{n:05d}"
            node, class_name = mine[m["owner"]]
            plain = f"{class_name}.{node.name}" if class_name else node.name
            if plain != m["function"]:
                raise SystemExit(f"{m['name']}: function {m['function']} is {plain} in the file")
            first, last = span(node)
            row = {"mutant": mid, "file": rel, "function": quals[node.lineno], "mutmut_function": plain,
                   "function_lines": f"{first}-{last}", "changed_lines": "", "operator": m["operator"],
                   "mutmut_name": m["name"], "sha256": "", "original": m["original"], "mutated": m["mutated"],
                   "check": ""}
            operators[m["operator"]] += 1
            try:
                text, changed, padding = place(original, m["module_code"], first, last)
            except Problem as e:
                s1.append(f"{mid} {m['name']}: {e}")
                rows.append(row)
                continue
            row["changed_lines"] = ranges(changed)
            padded[mid] = padding
            row["sha256"] = digest_text(text)
            texts[mid] = text
            problems = s1_problems(original, text, changed, first, last, g["file"])
            s1 += [f"{mid} {m['name']}: {p}" for p in problems]
            if problems:
                rows.append(row)
                continue
            new_tree = ast.parse(text)
            new_node = owners(new_tree)[m["owner"]][0]
            if new_node.lineno != node.lineno:
                s1.append(f"{mid} {m['name']}: the def line moved")
                rows.append(row)
                continue
            try:
                same = function_dump(new_node, node.name) == mutmut_function_dump(m["mutmut_function"], node.name)
            except (Problem, SyntaxError) as e:
                same = False
                s2.append(f"{mid} {m['name']}: {e}")
            if not same:
                s2.append(f"{mid} {m['name']}: the placed function differs from mutmut's mutant function")
            rows.append(row)
        per_file[rel] = {"mutants": len(g["mutants"]), "mutmut_names": len(g["mutmut_names"]),
                         "sha256": g["sha256"], "by_operator": dict(sorted(operators.items()))}
    report = {
        "mutmut_version": generated[0]["mutmut_version"] if generated else None,
        "files": per_file,
        "mutants": len(rows),
        "by_operator": dict(sorted(Counter(r["operator"] for r in rows).items())),
        "mutants_padded_with_blank_lines": sum(1 for v in padded.values() if v),
        "blank_lines_added": sum(padded.values()),
        "sentinels": [
            {"name": "S1", "text": "each modified file differs from the unmodified file only inside the span "
                                   "of the mutated function, keeps its number of lines, compiles, and is not "
                                   "the unmodified file", "pass": not s1, "detail": s1[:50],
             "failures": len(s1)},
            {"name": "S2", "text": "each mutated function has the syntax tree of the function mutmut writes "
                                   "for the mutant, and each file has as many mutants as mutmut's file "
                                   "generator yields, with the same names in the same order",
             "pass": not s2, "detail": s2[:50], "failures": len(s2)},
        ],
    }
    return rows, texts, report


def deletion_mutants(root: Path, files: list[str], subject: dict, checks: list[dict]
                     ) -> tuple[list[dict], dict[str, str], list[str], dict[str, int]]:
    """The deletion of each check of `files`: (rows of mutants.csv, id -> modified
    text, problems for sentinel S1, number of checks per file)."""
    rows, texts, problems, per_file = [], {}, [], {}
    n = 0
    for rel in files:
        original = (root / rel_to_source(subject, rel)).read_bytes().decode("utf-8")
        fns = functions(ast.parse(original))
        mine = sorted((c for c in checks if c["file"] == rel),
                      key=lambda c: (min(a for a, _ in c["lines"]), c["id"]))
        per_file[rel] = len(mine)
        for c in mine:
            n += 1
            mid = f"D{n:05d}"
            first, last = span(fns[c["function"]])
            row = {"mutant": mid, "file": rel, "function": c["function"], "mutmut_function": "",
                   "function_lines": f"{first}-{last}", "changed_lines": "", "operator": DELETION,
                   "mutmut_name": "", "sha256": "", "original": "", "mutated": "pass", "check": c["id"]}
            rows.append(row)
            try:
                text, removed = delete_check(original, c)
            except SystemExit as e:
                problems.append(f"{mid} {c['id']}: {e}")
                continue
            old, new = split_lines(original), split_lines(text)
            changed = [i + 1 for i, (x, y) in enumerate(zip(old, new)) if x != y]
            row["changed_lines"] = ranges(changed)
            row["original"] = " | ".join(" ".join(r["removed"].split()) for r in removed)
            row["sha256"] = digest_text(text)
            texts[mid] = text
            raise_lines = {x for a, z in c["lines"] for x in range(a, z + 1)}
            found = s1_problems(original, text, changed, first, last, rel)
            if not set(changed) <= raise_lines:
                found.append(f"lines outside the raise statements changed: {sorted(set(changed) - raise_lines)[:5]}")
            if not all(any(a <= x <= z for x in changed) for a, z in c["lines"]):
                found.append("a raise statement of the check did not change")
            problems += [f"{mid} {c['id']}: {p}" for p in found]
    return rows, texts, problems, per_file


def s1_problems(original: str, text: str, changed: list[int], first: int, last: int, label: str) -> list[str]:
    out = []
    if text == original:
        out.append("the modified file is the unmodified file")
    if len(split_lines(text)) != len(split_lines(original)) or \
            len(text.splitlines()) != len(original.splitlines()):
        out.append("the number of lines changed")
    outside = [x for x in changed if not first <= x <= last]
    if outside:
        out.append(f"lines outside the function changed: {outside[:5]}")
    try:
        compile(text, label, "exec", dont_inherit=True)
    except SyntaxError as e:
        out.append(f"does not compile: {e.msg} at line {e.lineno}")
    return out


def csv_text(header: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def write_sums(out: Path) -> None:
    sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
            for p in sorted(out.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    need_python_312()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--subject", required=True)
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--mutmut-python", required=True)
    parser.add_argument("--clone")
    parser.add_argument("--work")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    subject_path, subject = subject_paths(args.subject)
    name = subject["name"]
    clone, _ = local_settings(name, args.clone, "unused")
    work = Path(args.work).resolve() if args.work else default_work(name)
    out = Path(args.out).resolve() if args.out else default_out(name)
    unknown = [f for f in args.files if f not in subject["subject_files"]]
    if unknown:
        raise SystemExit(f"not subject files of {name}: {unknown}")
    files = sorted(args.files)
    work.mkdir(parents=True, exist_ok=True)
    # mutmut reads its settings from the current directory: a pyproject.toml of
    # this folder names the package and nothing else
    config = work / "generator"
    config.mkdir(exist_ok=True)
    (config / "pyproject.toml").write_text(
        f'[tool.mutmut]\nsource_paths = ["{subject["package"].replace(".", "/")}"]\n', encoding="utf-8")
    raw = work / "generator.jsonl"
    # the path is made absolute without following links: the interpreter of an
    # environment is a link, and the environment is found from the link's place
    proc = subprocess.run([os.path.abspath(args.mutmut_python), "-I", "-B", str(GENERATOR), "--root", str(clone),
                           "--out", str(raw)] + [rel_to_source(subject, f) for f in files],
                          cwd=config, capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
                               "PYTHONHASHSEED": "0", "HOME": str(config)})
    if proc.returncode != 0:
        raise SystemExit(f"mutmut_generate.py failed:\n{proc.stdout[-2000:]}{proc.stderr[-2000:]}")
    generated = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
    rows, texts, report = materialize(generated, clone, files, subject)
    checks_path = subject_path.parent / "checks.json"
    checks_doc = load_json(checks_path)
    for rel in files:
        digest = hashlib.sha256((clone / rel_to_source(subject, rel)).read_bytes()).hexdigest()
        if checks_doc["sha256"].get(rel) != digest:
            raise SystemExit(f"{rel}: the file of the clone is not the file checks.json was made from")
    d_rows, d_texts, d_problems, d_per_file = deletion_mutants(clone, files, subject, checks_doc["checks"])
    rows += d_rows
    texts.update(d_texts)
    report["check_deletions"] = len(d_rows)
    report["checks_json_sha256"] = hashlib.sha256(checks_path.read_bytes()).hexdigest()
    for rel, k in d_per_file.items():
        report["files"][rel]["check_deletions"] = k
    s1 = next(s for s in report["sentinels"] if s["name"] == "S1")
    s1["pass"] = s1["pass"] and not d_problems
    s1["failures"] += len(d_problems)
    s1["detail"] = (s1["detail"] + d_problems)[:50]
    s1["text"] += "; a deletion changes the lines of the check's raise statements and no other line"
    report["subject"] = {k: subject.get(k) for k in ("name", "version", "commit")}
    report["generator_sha256"] = hashlib.sha256(GENERATOR.read_bytes()).hexdigest()
    mutated = work / "mutated"
    mutated.mkdir(exist_ok=True)
    for stale in list(mutated.glob("M*.py")) + list(mutated.glob("D*.py")):
        if stale.stem not in texts:
            stale.unlink()
    manifest = {}
    for r in rows:
        if r["mutant"] in texts:
            path = mutated / f"{r['mutant']}.py"
            data = texts[r["mutant"]].encode("utf-8")
            if not path.exists() or path.read_bytes() != data:
                path.write_bytes(data)
        manifest[r["mutant"]] = {"file": r["file"], "function": r["function"], "sha256": r["sha256"],
                                 "mutmut_name": r["mutmut_name"], "check": r["check"],
                                 "path": f"mutated/{r['mutant']}.py" if r["mutant"] in texts else None}
    dump(work / "manifest.json", {"subject": name, "files": files, "mutants": manifest})
    out.mkdir(parents=True, exist_ok=True)
    (out / "mutants.csv").write_text(csv_text(MUTANTS_HEADER, rows), encoding="utf-8")
    (out / "materialize.json").write_text(json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False)
                                          + "\n", encoding="utf-8")
    write_sums(out)
    failed = [s["name"] for s in report["sentinels"] if not s["pass"]]
    print(f"materialize: {name}: {report['mutants']} mutants of mutmut in {len(files)} files "
          f"{json.dumps({f: v['mutants'] for f, v in report['files'].items()})} and "
          f"{len(d_rows)} deletions of checks {json.dumps(d_per_file)}; "
          f"sentinels that do not hold: {failed or 'none'}")
    for s in report["sentinels"]:
        for d in s["detail"][:10]:
            print(f"  {s['name']}: {d}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

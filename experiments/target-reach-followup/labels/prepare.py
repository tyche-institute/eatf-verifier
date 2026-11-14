"""Build a reading pack for 1 subject.

    python3 -I -B labels/prepare.py --subject ../target-reach/subjects/<name>/subject.json \
        --clone <clone> --instruction <instruction file> --out <empty folder outside the deposit>

The pack holds:

- src/: the files of the paths that subject.json copies (`copy`), read from
  the clone's object store at the commit of subject.json (`git ls-tree` and
  `git cat-file`; the working tree of the clone is not read and nothing in
  the clone changes). Where subject.json names a `repository_directory`,
  `--clone` is that directory inside the clone, as for the runs of the
  toolkit, and the paths are relative to it;
- checks.tsv: 1 row per check of checks.json, all of them, with id, file,
  function, class, lines, message template and guard conditions, and without
  the reachable field;
- classes.tsv: the classes of checks.json with their module, qualified name
  and declared bases, so that a labels file can be checked for subclasses
  inside the pack;
- blocks.tsv: 1 row per included block of blocks.json, with key, file, line
  span, test name, expected classes and the assertions of the block as text;
- labels.tsv: an empty labels template (block, label, basis, quote, note),
  1 row per included block with only the block filled in;
- the instruction file, copied under its own name;
- MANIFEST.txt: the path and SHA-256 of every other file of the pack.

Nothing else is written: no target, no generated output, no reading, no
record and no file of the toolkits. The program fails, and removes nothing,
when a file name of the pack is on the forbidden list, or when a file of the
pack other than the instruction file has the same bytes as a file of the
experiment directories (target-reach, mutation-adequacy-pyjwt,
target-reach-followup, outside their work/ folders).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from labelslib import (BLOCK_COLUMNS, CHECK_COLUMNS, CLASS_COLUMNS, LABEL_COLUMNS,  # noqa: E402
                       LIST_SEP, load_json, sha256_file, write_tsv)

FOLLOWUP = HERE.parent
EXPERIMENTS = FOLLOWUP.parent
DEPOSIT_DIRS = [EXPERIMENTS / "target-reach", EXPERIMENTS / "mutation-adequacy-pyjwt", FOLLOWUP]

# Names that no file of a pack may carry: the definitions, outputs, readings
# and records of the toolkits, and the outputs of this tooling.
FORBIDDEN_NAMES = frozenset("""
targets.json checks.json blocks.json subject.json draft.json local.json scope_counts.json
cases.csv checks.csv deletions.csv flags.csv pinning.csv undetected.csv
summary.json SUMMARY.md REPORT.md report.json VALIDATION.md SHA256SUMS records.tar.xz
FLAGS.md UNDETECTED.md DEVIATIONS.md PROTOCOL.md SELECTION.md NOTES.md second.json
base-1.json base-2.json suite.json manifest.json no-record.json repeated.json refused.json
timeout.json witnesses.json _control.json
agreement.csv outcomes.csv rule-vs-label.csv rule-vs-label-blocks.csv first-reading.csv
counts.json COUNTS.md
""".split())
FORBIDDEN_PARTS = frozenset({"generated", "readings", "records", "witnesses", "recompute", "first"})
PACK_FILES = {"checks.tsv", "classes.tsv", "blocks.tsv", "labels.tsv", "MANIFEST.txt"}


def git(clone: Path, *args: str, data: bytes | None = None) -> bytes:
    res = subprocess.run(["git", "-C", str(clone), *args], input=data, capture_output=True)
    if res.returncode != 0:
        raise SystemExit(f"prepare: git {' '.join(args[:2])} failed: {res.stderr.decode(errors='replace')}")
    return res.stdout


def tracked_files(clone: Path, commit: str, paths: list[str]) -> list[tuple[str, str]]:
    """(path relative to --clone, blob id) of every file under `paths` at the commit."""
    prefix = git(clone, "rev-parse", "--show-prefix").decode().strip()
    out = git(clone, "ls-tree", "-r", "-z", "--full-name", commit, "--", *paths)
    files = []
    for entry in out.split(b"\0"):
        if not entry:
            continue
        meta, _, path = entry.decode("utf-8").partition("\t")
        mode, kind, oid = meta.split()
        if kind != "blob" or mode == "120000":
            continue                       # submodules and symbolic links are not copied
        if prefix and not path.startswith(prefix):
            raise SystemExit(f"prepare: {path} lies outside {prefix}")
        files.append((path[len(prefix):], oid))
    return sorted(files)


def read_blobs(clone: Path, oids: list[str]) -> dict[str, bytes]:
    data = git(clone, "cat-file", "--batch", data="".join(o + "\n" for o in oids).encode())
    out, pos = {}, 0
    for oid in oids:
        nl = data.index(b"\n", pos)
        head = data[pos:nl].decode().split()
        if len(head) != 3 or head[0] != oid:
            raise SystemExit(f"prepare: unexpected answer of git cat-file for {oid}: {head}")
        size = int(head[2])
        out[oid] = data[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
    return out


def lines_text(spans: list) -> str:
    return LIST_SEP.join(f"{a}-{b}" if a != b else f"{a}" for a, b in spans)


def assertion_texts(b: dict) -> list[str]:
    out = []
    if b.get("match") is not None:
        out.append(f"match: {b['match']}")
    elif b.get("match_unparsed"):
        out.append(f"match (an expression): {b['match_unparsed']}")
    for p in b.get("post") or []:
        kind = p[0]
        if kind == "str_eq":
            out.append(f"after the block: str(exception) == {p[1]!r}")
        elif kind == "str_in":
            out.append(f"after the block: {p[1]!r} in str(exception)")
        elif kind == "attr_eq":
            out.append(f"after the block: exception.{p[1]} == {p[2]!r}")
        elif kind == "match":
            out.append(f"after the block: re.match {p[1]!r} on the exception")
        elif kind == "unparsed":
            out.append(f"after the block: {p[1]}")
        else:
            out.append(f"after the block: {p!r}")
    for src in b.get("post_unparsed") or []:
        out.append(f"after the block: {src}")
    return out


def block_lines(b: dict) -> str:
    start = b["header_span"][0]
    end = (b.get("body_span") or b["header_span"])[1]
    return f"{start}-{end}"


def deposit_digests(skip: Path) -> dict[str, str]:
    """sha256 -> path, for every non-empty file of the experiment directories
    outside their work/ folders and outside `skip`."""
    out = {}
    for root in DEPOSIT_DIRS:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            rel = p.relative_to(root)
            if not p.is_file() or "work" in rel.parts[:1] or "__pycache__" in rel.parts:
                continue
            if skip == p or skip in p.parents:
                continue
            if p.stat().st_size == 0:
                continue
            out.setdefault(sha256_file(p), str(p.relative_to(EXPERIMENTS)))
    return out


def forbidden(rel: Path, instruction_name: str) -> str | None:
    if rel.name == instruction_name and len(rel.parts) == 1:
        return None
    if rel.name in FORBIDDEN_NAMES:
        return f"forbidden file name {rel.name}"
    if rel.parts[0] == "src":
        return None
    if len(rel.parts) != 1 or rel.name not in PACK_FILES:
        return "not a file of a pack"
    return None


def check_pack(out: Path, instruction_name: str, digests: dict[str, str]) -> list[str]:
    problems = []
    for p in sorted(out.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(out)
        why = forbidden(rel, instruction_name)
        if why:
            problems.append(f"{rel}: {why}")
        if rel.parts[0] != "src" and set(rel.parts[:-1]) & FORBIDDEN_PARTS:
            problems.append(f"{rel}: forbidden folder")
        if rel.name in (instruction_name, "MANIFEST.txt") and len(rel.parts) == 1:
            continue
        if p.stat().st_size and (d := sha256_file(p)) in digests:
            problems.append(f"{rel}: same bytes as {digests[d]}")
    return problems


def write_manifest(out: Path) -> int:
    rows = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.relative_to(out).as_posix() != "MANIFEST.txt":
            rows.append(f"{sha256_file(p)}  {p.relative_to(out).as_posix()}")
    (out / "MANIFEST.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(rows)


def verify_manifest(pack: Path) -> list[str]:
    """Problems of a pack against its MANIFEST.txt: changed, missing or extra files."""
    problems = []
    listed = {}
    man = pack / "MANIFEST.txt"
    if not man.is_file():
        return ["MANIFEST.txt is missing"]
    for line in man.read_text(encoding="utf-8").splitlines():
        digest, _, rel = line.partition("  ")
        listed[rel] = digest
    present = {p.relative_to(pack).as_posix() for p in pack.rglob("*") if p.is_file()} - {"MANIFEST.txt"}
    for rel in sorted(set(listed) - present):
        problems.append(f"{rel}: listed and missing")
    for rel in sorted(present - set(listed)):
        problems.append(f"{rel}: present and not listed")
    for rel in sorted(set(listed) & present):
        if sha256_file(pack / rel) != listed[rel]:
            problems.append(f"{rel}: changed")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", required=True, type=Path)
    ap.add_argument("--clone", required=True, type=Path)
    ap.add_argument("--instruction", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)

    subject_path = a.subject.resolve()
    defs = subject_path.parent
    subject = load_json(subject_path)
    checks_doc = load_json(defs / "checks.json")
    blocks_doc = load_json(defs / "blocks.json")
    out = a.out.resolve()
    work = FOLLOWUP / "work"
    for root in DEPOSIT_DIRS:
        if (out == root or root in out.parents) and not (work in out.parents):
            raise SystemExit(f"prepare: the pack must lie outside the deposit ({out})")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"prepare: {out} exists and is not empty")
    instruction = a.instruction.resolve()
    if not instruction.is_file():
        raise SystemExit(f"prepare: no instruction file {instruction}")
    if instruction.name in PACK_FILES or instruction.name in FORBIDDEN_NAMES or instruction.name == "src":
        raise SystemExit(f"prepare: the instruction file may not be named {instruction.name}")

    files = tracked_files(a.clone, subject["commit"], subject["copy"])
    if not files:
        raise SystemExit("prepare: the copied paths hold no file at the commit")
    blobs = read_blobs(a.clone, [oid for _, oid in files])

    out.mkdir(parents=True, exist_ok=True)
    for rel, oid in files:
        dest = out / "src" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blobs[oid])

    write_tsv(out / "checks.tsv", CHECK_COLUMNS, [
        [c["id"], c["file"], c["function"], c["class"], lines_text(c["lines"]), c["template"],
         LIST_SEP.join(g if g is not None else "(none)" for g in c["guards"])]
        for c in sorted(checks_doc["checks"], key=lambda c: c["id"])])
    write_tsv(out / "classes.tsv", CLASS_COLUMNS, [
        [label, v.get("module", ""), v.get("qualname", ""), LIST_SEP.join(v.get("bases") or [])]
        for label, v in sorted(checks_doc["classes"].items())])
    included = sorted((b for b in blocks_doc["blocks"] if b["included"]), key=lambda b: b["key"])
    write_tsv(out / "blocks.tsv", BLOCK_COLUMNS, [
        [b["key"], b["file"], block_lines(b),
         f"{b['test_class']}.{b['test']}" if b.get("test_class") else b["test"],
         LIST_SEP.join(b["expected"]), LIST_SEP.join(assertion_texts(b))]
        for b in included])
    write_tsv(out / "labels.tsv", LABEL_COLUMNS, [[b["key"], "", "", "", ""] for b in included])
    (out / instruction.name).write_bytes(instruction.read_bytes())

    problems = check_pack(out, instruction.name, deposit_digests(skip=out))
    n = write_manifest(out)
    if problems:
        print("prepare: the pack is refused:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print(f"prepare: {subject['name']} at {subject['commit'][:12]}: {len(files)} source files, "
          f"{len(checks_doc['checks'])} checks, {len(checks_doc['classes'])} classes, "
          f"{len(included)} included blocks; MANIFEST.txt lists {n} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

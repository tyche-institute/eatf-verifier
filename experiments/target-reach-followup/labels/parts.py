"""Split the blocks of a reading pack into parts, and join labels files made in parts.

    python3 -I -B labels/parts.py split --pack <pack> --max-blocks N --out <parts.tsv>
    python3 -I -B labels/parts.py join --pack <pack> --parts <parts.tsv> \
        --labels <labels of part 1> <labels of part 2> ... --out <labels.tsv>

`split` reads blocks.tsv of the pack. The number of parts is the smallest k
with k * N at least the number of included blocks. The test files are taken
in sorted order, and a part ends after the first file with which the running
number of blocks reaches i/k of all blocks (i = 1, ..., k), so that a test
file is never divided; a part that would hold no file is dropped and the
parts are numbered from 1 without a gap. parts.tsv holds 1 row per test file:
file, part and the number of its blocks. The result depends on
blocks.tsv and N only.

`join` takes 1 labels file per part, in the order of the parts. Each row of
the joined file is the row of its block in the labels file of the part that
holds the block's test file; the rows keep the order of labels.tsv of the
pack. A row of another part in a labels file is not read; when it carries a
label, the block is listed in the message. The program fails when a labels
file lacks a block of its part, names a block twice, or has another header.
It does not check the labels themselves (`check_labels.py` does).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from labelslib import LABEL_COLUMNS, read_tsv, write_tsv  # noqa: E402

PART_COLUMNS = ["file", "part", "blocks"]


def split(files_of_blocks: list[str], max_blocks: int) -> list[tuple[str, int, int]]:
    """(file, part, blocks) per test file, for the test file of each block."""
    if max_blocks < 1:
        raise ValueError("max-blocks is at least 1")
    total = len(files_of_blocks)
    counts: dict[str, int] = {}
    for f in files_of_blocks:
        counts[f] = counts.get(f, 0) + 1
    k = max(1, -(-total // max_blocks))
    rows, part, running = [], 1, 0
    for f in sorted(counts):
        rows.append((f, part, counts[f]))
        running += counts[f]
        while part < k and running * k >= part * total:
            part += 1
    number = {old: new for new, old in enumerate(sorted({r[1] for r in rows}), start=1)}
    return [(f, number[part], n) for f, part, n in rows]


def join(order: list[str], file_of: dict[str, str], part_of: dict[str, int],
         labels: list[tuple[list[str], list[dict]]]) -> tuple[list[list[str]], list[str], list[str]]:
    """(rows of the joined file, errors, blocks labeled outside their part)."""
    errors, outside = [], []
    per_part: list[dict[str, dict]] = []
    for i, (header, rows) in enumerate(labels, start=1):
        if header != LABEL_COLUMNS:
            errors.append(f"part {i}: the header is {header}, not {LABEL_COLUMNS}")
        seen: dict[str, dict] = {}
        for r in rows:
            b = r.get("block", "")
            if b in seen:
                errors.append(f"part {i}: block {b} twice")
            seen[b] = r
            if b in file_of and part_of[file_of[b]] != i and (r.get("label") or "").strip():
                outside.append(f"part {i}: {b}")
        per_part.append(seen)
    if len(labels) != max(part_of.values(), default=0):
        errors.append(f"{len(labels)} labels files for {max(part_of.values(), default=0)} parts")
        return [], errors, outside
    out = []
    for b in order:
        i = part_of[file_of[b]]
        r = per_part[i - 1].get(b)
        if r is None:
            errors.append(f"part {i}: block {b} is missing")
            continue
        out.append([r.get(c, "") for c in LABEL_COLUMNS])
    return out, errors, outside


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("split")
    s.add_argument("--pack", required=True, type=Path)
    s.add_argument("--max-blocks", required=True, type=int)
    s.add_argument("--out", required=True, type=Path)
    j = sub.add_parser("join")
    j.add_argument("--pack", required=True, type=Path)
    j.add_argument("--parts", required=True, type=Path)
    j.add_argument("--labels", required=True, nargs="+", type=Path)
    j.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)

    _, blocks = read_tsv(a.pack / "blocks.tsv")
    file_of = {b["block"]: b["file"] for b in blocks}
    if a.command == "split":
        rows = split([b["file"] for b in blocks], a.max_blocks)
        write_tsv(a.out, PART_COLUMNS, [list(r) for r in rows])
        sizes: dict[int, int] = {}
        for _, part, n in rows:
            sizes[part] = sizes.get(part, 0) + n
        print(f"parts: {len(blocks)} blocks in {len(rows)} test files, {len(sizes)} parts of "
              + ", ".join(str(sizes[p]) for p in sorted(sizes)) + " blocks")
        return 0

    _, part_rows = read_tsv(a.parts)
    part_of = {r["file"]: int(r["part"]) for r in part_rows}
    missing = sorted(set(file_of.values()) - set(part_of))
    if missing:
        print(f"parts: test files without a part: {missing}", file=sys.stderr)
        return 1
    _, template = read_tsv(a.pack / "labels.tsv")
    order = [r["block"] for r in template]
    rows, errors, outside = join(order, file_of, part_of, [read_tsv(p) for p in a.labels])
    if errors:
        print("parts: not joined:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    write_tsv(a.out, LABEL_COLUMNS, rows)
    print(f"parts: {len(rows)} rows joined from {len(a.labels)} labels files"
          + (f"; labeled outside their part and not read: {outside}" if outside else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

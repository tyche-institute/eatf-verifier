"""Shared definitions of the label tooling: the labels file, its validation,
the class hierarchy and the tab-separated files of a reading pack.

Standard library only. Used by prepare.py, check_labels.py,
analyse_labels.py, convert_reference.py and check_first.py.
"""

from __future__ import annotations

import builtins
import csv
import hashlib
import io
import json
import re
from pathlib import Path

LABEL_COLUMNS = ["block", "label", "basis", "quote", "note"]
CHECK_COLUMNS = ["id", "file", "function", "class", "lines", "template", "guards"]
CLASS_COLUMNS = ["class", "module", "qualname", "bases"]
BLOCK_COLUMNS = ["block", "file", "lines", "test", "expected", "assertions"]

BASIS_WORDS = ("class", "assert", "name")   # the order of a canonical combination
NONE = "none"
PARAM_PREFIX = "by-param "
LIST_SEP = " | "                             # joins several values in 1 cell


# -- tab-separated files -----------------------------------------------------------

def write_tsv(path: Path, header: list[str], rows: list[list]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, dialect="excel-tab", lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else str(v) for v in r])
    path.write_text(buf.getvalue(), encoding="utf-8")


def read_tsv(path: Path) -> tuple[list[str], list[dict]]:
    """(header, rows). A row is a dict of the header's columns; a row with
    more or fewer cells than the header is kept with the key '__cells__'
    holding the number of its cells, so that a validator can report it."""
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.reader(io.StringIO(text), dialect="excel-tab")
    rows = list(reader)
    if not rows:
        return [], []
    header = rows[0]
    out = []
    for i, cells in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in cells):
            continue
        row = {h: (cells[j] if j < len(cells) else "") for j, h in enumerate(header)}
        row["__line__"] = i
        if len(cells) != len(header):
            row["__cells__"] = len(cells)
        out.append(row)
    return header, out


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_text(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# -- labels ------------------------------------------------------------------------

class LabelError(ValueError):
    pass


def parse_label(cell: str) -> tuple:
    """('none',) | ('check', id) | ('param', name, ((value, id or None), ...)).

    A label is a check id, the word `none`, or, for a block whose described
    check depends on a parameter of the test, `by-param <name>: <value>=<id or
    none>; <value>=<id or none>`."""
    cell = (cell or "").strip()
    if not cell:
        raise LabelError("empty label")
    if cell == NONE:
        return (NONE,)
    if cell.startswith(PARAM_PREFIX):
        head, sep, rest = cell[len(PARAM_PREFIX):].partition(":")
        name = head.strip()
        if not sep or not name or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise LabelError(f"by-param label without a parameter name: {cell!r}")
        values = []
        for part in rest.split(";"):
            part = part.strip()
            if not part:
                continue
            v, eq, cid = part.partition("=")
            v, cid = v.strip(), cid.strip()
            if not eq or not v or not cid:
                raise LabelError(f"by-param value without '=': {part!r}")
            values.append((v, None if cid == NONE else cid))
        if len(values) < 2:
            raise LabelError(f"by-param label with fewer than 2 values: {cell!r}")
        if len({v for v, _ in values}) != len(values):
            raise LabelError(f"by-param label names a value twice: {cell!r}")
        return ("param", name, tuple(sorted(values)))
    if any(ch.isspace() for ch in cell):
        raise LabelError(f"a check id holds no white space: {cell!r}")
    return ("check", cell)


def label_text(label: tuple) -> str:
    """The canonical text of a parsed label; 2 labels are equal when their texts are."""
    if label[0] == NONE:
        return NONE
    if label[0] == "check":
        return label[1]
    return f"{PARAM_PREFIX}{label[1]}: " + "; ".join(f"{v}={c or NONE}" for v, c in label[2])


def label_checks(label: tuple) -> list[str]:
    if label[0] == "check":
        return [label[1]]
    if label[0] == "param":
        return sorted({c for _, c in label[2] if c})
    return []


def parse_basis(cell: str) -> tuple[str, ...]:
    """('none',) or a combination of class, assert and name, joined by '+'."""
    cell = (cell or "").strip()
    if cell == NONE:
        return (NONE,)
    parts = [p.strip() for p in cell.split("+")]
    if not cell or any(p not in BASIS_WORDS for p in parts):
        raise LabelError(f"basis must be none or a combination of {', '.join(BASIS_WORDS)} "
                         f"joined by '+': {cell!r}")
    if len(set(parts)) != len(parts):
        raise LabelError(f"basis names a word twice: {cell!r}")
    return tuple(w for w in BASIS_WORDS if w in parts)


def param_value_of(label: tuple, test_node: str) -> tuple[str | None, list[str]]:
    """For a by-param label: (the check id or None, the values found) for 1
    case, read from the parametrization id of its test node, the part in
    brackets, split at '-'. Exactly 1 value of the label must occur there."""
    m = re.search(r"\[(.*)\]$", test_node or "")
    parts = set(m.group(1).split("-")) if m else set()
    found = [v for v, _ in label[2] if v in parts]
    if len(found) != 1:
        return None, found
    return dict(label[2])[found[0]], found


# -- the class hierarchy -----------------------------------------------------------

def builtin_class(name: str):
    obj = getattr(builtins, name, None)
    return obj if isinstance(obj, type) else None


def ancestors(label: str, classes: dict[str, list[str]]) -> list[str]:
    """The class and its ancestors, by label. `classes` maps a label of the
    package to the labels of its declared bases; a built-in class gives the
    bases of the interpreter; any other label ends the walk."""
    out, todo = [], [label]
    while todo:
        c = todo.pop(0)
        if c in out:
            continue
        out.append(c)
        if c in classes:
            todo.extend(classes[c])
        elif (b := builtin_class(c)) is not None:
            todo.extend(k.__name__ for k in b.__mro__[1:])
    return out


def is_expected(check_class: str, expected: list[str], classes: dict) -> bool:
    anc = ancestors(check_class, classes)
    return any(e in anc for e in expected)


# -- the subject as the validator sees it ------------------------------------------

class Universe:
    """What a labels file is validated against: the included blocks with
    their expected classes, the checks with their classes, and the class
    hierarchy. Built from a reading pack or from the subject's definitions."""

    def __init__(self, blocks: dict[str, list[str]], checks: dict[str, str],
                 classes: dict[str, list[str]]) -> None:
        self.blocks = blocks          # included block key -> expected class labels
        self.checks = checks          # check id -> class label
        self.classes = classes        # class label -> base labels

    @classmethod
    def from_pack(cls, pack: Path) -> "Universe":
        _, brows = read_tsv(pack / "blocks.tsv")
        _, crows = read_tsv(pack / "checks.tsv")
        _, krows = read_tsv(pack / "classes.tsv")
        blocks = {r["block"]: [x for x in r["expected"].split(LIST_SEP) if x] for r in brows}
        checks = {r["id"]: r["class"] for r in crows}
        classes = {r["class"]: [x for x in r["bases"].split(LIST_SEP) if x] for r in krows}
        return cls(blocks, checks, classes)

    @classmethod
    def from_defs(cls, checks_doc: dict, blocks_doc: dict) -> "Universe":
        blocks = {b["key"]: list(b["expected"]) for b in blocks_doc["blocks"] if b["included"]}
        checks = {c["id"]: c["class"] for c in checks_doc["checks"]}
        classes = {k: list(v.get("bases") or []) for k, v in checks_doc["classes"].items()}
        return cls(blocks, checks, classes)


def validate_labels(header: list[str], rows: list[dict], uni: Universe) -> dict:
    """Errors make the file invalid. Warnings do not. `class_outside` lists the
    labels whose check's class is not an expected class of the block nor a
    subclass of one: allowed, and listed."""
    errors, warnings, class_outside = [], [], []
    labels: dict[str, tuple] = {}
    bases: dict[str, tuple] = {}
    if header[:len(LABEL_COLUMNS)] != LABEL_COLUMNS or len(header) != len(LABEL_COLUMNS):
        errors.append(f"header must be exactly {LABEL_COLUMNS}, found {header}")
        return {"errors": errors, "warnings": warnings, "class_outside": class_outside,
                "labels": labels, "bases": bases}
    seen: dict[str, int] = {}
    for r in rows:
        line = r["__line__"]
        if "__cells__" in r:
            errors.append(f"line {line}: {r['__cells__']} cells, expected {len(LABEL_COLUMNS)}")
            continue
        key = r["block"].strip()
        if key not in uni.blocks:
            errors.append(f"line {line}: block {key!r} is not an included block of the pack")
            continue
        if key in seen:
            errors.append(f"line {line}: block {key!r} labeled again (first at line {seen[key]})")
            continue
        seen[key] = line
        try:
            label = parse_label(r["label"])
        except LabelError as exc:
            errors.append(f"line {line}: {exc}")
            continue
        try:
            basis = parse_basis(r["basis"])
        except LabelError as exc:
            errors.append(f"line {line}: {exc}")
            continue
        unknown = [c for c in label_checks(label) if c not in uni.checks]
        if unknown:
            errors.append(f"line {line}: {', '.join(unknown)} is not a check id of checks.tsv")
            continue
        if label[0] == NONE and basis != (NONE,):
            errors.append(f"line {line}: label none needs basis none")
            continue
        if label[0] != NONE and basis == (NONE,):
            errors.append(f"line {line}: a label that names a check needs a basis other than none")
            continue
        if basis == (NONE,) and not r["note"].strip():
            errors.append(f"line {line}: basis none needs the reason in the note")
            continue
        if basis != (NONE,) and not r["quote"].strip():
            warnings.append(f"line {line}: no quote for basis {'+'.join(basis)}")
        for cid in label_checks(label):
            cls_ = uni.checks[cid]
            if not is_expected(cls_, uni.blocks[key], uni.classes):
                class_outside.append({"block": key, "label": cid, "class": cls_,
                                      "expected": uni.blocks[key]})
        labels[key] = label
        bases[key] = basis
    missing = sorted(set(uni.blocks) - set(seen))
    for key in missing:
        errors.append(f"block {key!r} has no label")
    return {"errors": errors, "warnings": warnings, "class_outside": class_outside,
            "labels": labels, "bases": bases}


def report_text(result: dict, name: str) -> str:
    lines = [f"{name}: {len(result['labels'])} blocks labeled, {len(result['errors'])} errors, "
             f"{len(result['warnings'])} warnings, {len(result['class_outside'])} labels whose class "
             f"is not an expected class or a subclass of one"]
    lines += [f"  error: {e}" for e in result["errors"]]
    lines += [f"  warning: {w}" for w in result["warnings"]]
    lines += [f"  class outside: {c['block']}: {c['label']} ({c['class']}; expected "
              f"{', '.join(c['expected'])})" for c in result["class_outside"]]
    return "\n".join(lines) + "\n"

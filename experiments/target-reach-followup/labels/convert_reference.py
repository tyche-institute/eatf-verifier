"""Convert the labels of the PyJWT reference study into a labels file.

    python3 -I -B labels/convert_reference.py --out <labels.tsv> \
        [--reference ../mutation-adequacy-pyjwt] [--subject ../target-reach/subjects/pyjwt/subject.json]

The reference study (`../mutation-adequacy-pyjwt/cases.json`, section
"Targets" of its PROTOCOL.md) labels each included block with 1 target or
none. Its files are only read.

Blocks. A reference block key is `<file name>::<test>#<k>`; a key of the
toolkit is `<path>::<test class>.<test>#<k>`. A reference block maps to the
toolkit block with the same file name (the last part of the path), the same
test name and the same k; each of the 79 included reference blocks must map
to exactly 1 included toolkit block, and no 2 of them to the same one.

Checks. A reference check maps to the toolkit check with the same function
and the same raise statements; the reference numbers raise statements from 0
and the toolkit from 1 (as `../target-reach/validate_pyjwt.py` does). The
reference splits the check `PyJWS._decode_base64url_segment` by segment;
the toolkit does not, so the segment is dropped and named in the note.

Bases. The reference writes the basis of a label as text, in parts separated
by ';'. A part that starts with `class` gives `class`; one that starts with
`match`, `message` or `claim` gives `assert`; one that starts with `name`
gives `name`. Any other part stops the conversion. The text of the basis
goes into the quote column. A block without a target gets label and basis
`none` and the reason of the reference in the note.

The block with 1 label per value of its parameter `claim` gets a by-param
label (`by-param claim: exp=<id>; iat=<id>; nbf=<id>`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from labelslib import LABEL_COLUMNS, PARAM_PREFIX, load_json, write_tsv  # noqa: E402

BASIS_STARTS = {"class": "class", "match": "assert", "message": "assert", "claim": "assert", "name": "name"}


def basis_of(text: str) -> str:
    words = set()
    for part in text.split(";"):
        part = part.strip()
        word = next((w for s, w in BASIS_STARTS.items() if part.startswith(s)), None)
        if word is None:
            raise SystemExit(f"convert_reference: basis part not recognised: {part!r}")
        words.add(word)
    return "+".join(w for w in ("class", "assert", "name") if w in words)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reference", type=Path, default=EXPERIMENTS / "mutation-adequacy-pyjwt")
    ap.add_argument("--subject", type=Path, default=EXPERIMENTS / "target-reach" / "subjects" / "pyjwt" / "subject.json")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    ref_cases = load_json(a.reference / "cases.json")
    ref_checks = load_json(a.reference / "checks.json")
    defs = a.subject.resolve().parent
    checks = load_json(defs / "checks.json")
    blocks = load_json(defs / "blocks.json")

    ours = {(c["function"], tuple(c["raise_numbers"])): c["id"] for c in checks["checks"]}
    check_map = {}
    for c in ref_checks["checks"]:
        sig = (c["function"], tuple(k + 1 for k in c["raises"]))
        if sig in ours:
            check_map[c["id"]] = ours[sig]

    by_sig: dict[tuple, list[str]] = {}
    for b in blocks["blocks"]:
        if b["included"]:
            by_sig.setdefault((Path(b["file"]).name, b["test"], b["k"]), []).append(b["key"])

    rows, used, problems = [], {}, []
    ref_included = [b for b in ref_cases["blocks"] if b["included"]]
    for b in ref_included:
        hits = by_sig.get((Path(b["file"]).name, b["test"], b["k"]), [])
        if len(hits) != 1:
            problems.append(f"{b['key']}: {len(hits)} included toolkit blocks")
            continue
        key = hits[0]
        if key in used:
            problems.append(f"{b['key']} and {used[key]} map to {key}")
            continue
        used[key] = b["key"]
        label = b["label"]
        note = f"reference block {b['key']}"
        if "by_param" in label:
            parts, quotes, words = [], [], set()
            for value, x in sorted(label["values"].items()):
                cid = check_map.get(x["target"])
                if cid is None:
                    problems.append(f"{b['key']}: check {x['target']} has no toolkit check")
                    continue
                parts.append(f"{value}={cid}")
                quotes.append(f"{value}: {x['basis']}")
                words |= set(basis_of(x["basis"]).split("+"))
            rows.append([key, f"{PARAM_PREFIX}{label['by_param']}: " + "; ".join(parts),
                         "+".join(w for w in ("class", "assert", "name") if w in words),
                         " / ".join(quotes), note])
        elif label.get("target"):
            cid = check_map.get(label["target"])
            if cid is None:
                problems.append(f"{b['key']}: check {label['target']} has no toolkit check")
                continue
            if label.get("segment"):
                note += f"; segment {label['segment']} of the reference not represented"
            rows.append([key, cid, basis_of(label["basis"]), label["basis"], note])
        else:
            rows.append([key, "none", "none", "", f"{note}; reason: {label.get('reason') or ''}"])
    if problems:
        print("convert_reference: not converted:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    rows.sort()
    write_tsv(a.out, LABEL_COLUMNS, rows)
    print(f"convert_reference: {len(rows)} blocks: "
          f"{sum(1 for r in rows if r[1] not in ('none',) and not r[1].startswith(PARAM_PREFIX))} with a check, "
          f"{sum(1 for r in rows if r[1].startswith(PARAM_PREFIX))} by parameter, "
          f"{sum(1 for r in rows if r[1] == 'none')} none")
    return 0


if __name__ == "__main__":
    sys.exit(main())

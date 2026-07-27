#!/usr/bin/env python3
"""JCS boundary experiment: the decision-path method applied to third-party code.

Runs the frozen boundary corpus through two independently authored RFC 8785
implementations that this project depends on but did not write, and compares
each against the class declared in oracle.json before execution.

The comparison unit is the outcome class (output vs terminate), which is the
RFC-8785 analogue of the first-failure code used by the AEP decision-path
experiment: the specification states, for each case, whether an implementation
is obliged to terminate. Agreement on "both produced something" is not enough.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RESULTS = HERE / "generated"


def load_oracle() -> dict:
    return json.loads((HERE / "oracle.json").read_text(encoding="utf-8"))


def run_python(cases: list[dict]) -> list[dict]:
    import rfc8785

    rows = []
    for case in cases:
        try:
            value = json.loads(case["input"])
        except Exception as exc:  # pragma: no cover - corpus is well-formed JSON
            rows.append({"id": case["id"], "outcome": "error", "stage": "parse",
                         "error": type(exc).__name__})
            continue
        # Python's json keeps integers exact (arbitrary precision) and strings
        # as unpaired-surrogate-capable str, so no value is changed before
        # canonicalization.
        try:
            out = rfc8785.dumps(value)
        except Exception as exc:
            rows.append({"id": case["id"], "outcome": "error", "stage": "canonicalize",
                         "error": type(exc).__name__})
            continue
        rows.append({"id": case["id"], "outcome": "output",
                     "bytes_hex": out.hex(),
                     "text": out.decode("utf-8", "replace")})
    return rows


def run_js() -> list[dict]:
    proc = subprocess.run(
        ["node", str(HERE / "run_js.mjs")],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return json.loads(proc.stdout)["rows"]


def host_changed_the_number(case: dict, js_row: dict) -> bool:
    """True when JavaScript's parser produced a different NUMBER than the exact
    value written in the input text. Formatting normalisation (-0 -> 0, escape
    -> character) is not a value change and is not counted."""
    reported = js_row.get("host_number")
    if reported is None:
        return False
    try:
        exact = json.loads(case["input"])["a"]
    except Exception:
        return False
    if not isinstance(exact, (int, float)) or isinstance(exact, bool):
        return False
    if reported in ("Infinity", "-Infinity", "NaN"):
        return True
    try:
        return float(reported) != exact and int(float(reported)) != exact
    except (ValueError, OverflowError):
        return True


def classify(row: dict) -> str:
    return "terminate" if row["outcome"] == "error" else "output"


def conforms(expected_class: str, observed: str) -> bool | None:
    """Does the observed outcome satisfy the declared obligation?

    Returns None when the specification imposes no obligation, so neither
    outcome can be scored.
    """
    if expected_class == "must_terminate":
        return observed == "terminate"
    if expected_class == "permitted":
        return observed == "output"
    return None  # "undefined": the RFC assigns no implementation behaviour


def main() -> int:
    oracle = load_oracle()
    cases = oracle["cases"]
    by_id = {c["id"]: c for c in cases}

    js = {r["id"]: r for r in run_js()}
    py = {r["id"]: r for r in run_python(cases)}

    rows = []
    for case in cases:
        cid = case["id"]
        j, p = js[cid], py[cid]
        jc, pc = classify(j), classify(p)
        rows.append({
            "id": cid,
            "expected_class": case["expected_class"],
            "js_outcome": jc,
            "py_outcome": pc,
            "js_detail": j.get("text") or j.get("error"),
            "py_detail": p.get("text") or p.get("error"),
            "js_host_changed_number": host_changed_the_number(case, j),
            "js_host_number": j.get("host_number"),
            "agree": jc == pc and j.get("bytes_hex") == p.get("bytes_hex"),
            "js_conforms": conforms(case["expected_class"], jc),
            "py_conforms": conforms(case["expected_class"], pc),
        })

    scored = [r for r in rows if r["js_conforms"] is not None]
    summary = {
        "cases": len(rows),
        "cases_with_a_declared_obligation": len(scored),
        "cases_the_rfc_leaves_undefined": len(rows) - len(scored),
        "outcome_agreements": sum(1 for r in rows if r["agree"]),
        "outcome_divergences": sum(1 for r in rows if not r["agree"]),
        "js_conformance": f"{sum(1 for r in scored if r['js_conforms'])}/{len(scored)}",
        "py_conformance": f"{sum(1 for r in scored if r['py_conforms'])}/{len(scored)}",
        "js_nonconforming": [r["id"] for r in scored if not r["js_conforms"]],
        "py_nonconforming": [r["id"] for r in scored if not r["py_conforms"]],
        "cases_where_the_js_parser_changed_the_number_before_canonicalization":
            [r["id"] for r in rows if r["js_host_changed_number"]],
    }

    RESULTS.mkdir(exist_ok=True)
    payload = {
        "schema": "urn:eatf:experiment:jcs-boundary-results:1",
        "environment": {
            "python": platform.python_version(),
            "node": subprocess.run(["node", "-v"], capture_output=True, text=True).stdout.strip(),
            "canonicalize": oracle["software_under_test"][0]["version"],
            "rfc8785": oracle["software_under_test"][1]["version"],
        },
        "summary": summary,
        "rows": rows,
    }
    (RESULTS / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = ["case,expected_class,js_outcome,py_outcome,agree,js_conforms,py_conforms"]
    for r in rows:
        lines.append(",".join([
            r["id"], r["expected_class"], r["js_outcome"], r["py_outcome"],
            str(r["agree"]).lower(),
            "n/a" if r["js_conforms"] is None else str(r["js_conforms"]).lower(),
            "n/a" if r["py_conforms"] is None else str(r["py_conforms"]).lower(),
        ]))
    (RESULTS / "results.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    digest = hashlib.sha256(
        (RESULTS / "results.csv").read_bytes()
    ).hexdigest()
    (RESULTS / "SHA256SUMS").write_text(
        f"{digest}  generated/results.csv\n"
        f"{hashlib.sha256((HERE / 'oracle.json').read_bytes()).hexdigest()}  oracle.json\n",
        encoding="utf-8",
    )

    print("# JCS boundary experiment")
    for key, value in summary.items():
        print(f"- {key}: {value}")
    print(f"- results.csv digest: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
demo-bkt-session.py — Generate a synthetic 5-event BKT session and sign it
as an EATF .aep evidence package using the eatf-sign CLI.

Usage:
    python examples/05-bkt-edu-demo/demo-bkt-session.py [--eatf-root PATH] [--out session.aep]

Defaults:
    --eatf-root  auto-detected as the eatf repo root (two levels up from this script)
    --out        session-demo.aep

What it produces:
    A signed .aep file containing a JSON payload of 5 BKT events
    (4 correct + 1 incorrect with teacher override), using a freshly
    generated DEV RSA keypair and a recycled RFC 3161 timestamp token
    from the EATF test-vector suite.  Suitable for the AIED 2026 demo.

Requirements:
    - Python 3.11+
    - Node.js 20+ (for eatf-sign CLI)
    - The eatf repo must have been set up:
        cd <eatf-root>/lib && npm install && npm run build && cd ..
        cd <eatf-root>/cli/eatf-sign && npm install && cd ../..

BKT parameters used (Corbett & Anderson defaults):
    p_init    = 0.20
    p_transit = 0.10
    p_slip    = 0.10
    p_guess   = 0.20
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# BKT implementation (mirrors engine/src/adaptive/bkt.py)
# ---------------------------------------------------------------------------

def bkt_update(p_l: float, correct: bool,
               p_slip: float = 0.1, p_guess: float = 0.2,
               p_transit: float = 0.1) -> float:
    if correct:
        cond = (p_l * (1 - p_slip)) / (p_l * (1 - p_slip) + (1 - p_l) * p_guess)
    else:
        cond = (p_l * p_slip) / (p_l * p_slip + (1 - p_l) * (1 - p_guess))
    return cond + (1 - cond) * p_transit


# ---------------------------------------------------------------------------
# Session definition
# ---------------------------------------------------------------------------

SKILL_ID = "fractions.add"
P_INIT   = 0.20
BKT_PARAMS = {"p_init": P_INIT, "p_transit": 0.1, "p_slip": 0.1, "p_guess": 0.2}

# (task_id, correct, optional teacher_override)
TASK_SEQUENCE = [
    ("task-2026-001", True,  None),
    ("task-2026-002", True,  None),
    ("task-2026-003", True,  None),
    ("task-2026-004", False, {
        "action":    "continue",
        "reason":    "Student appeared distracted; skip automatic difficulty adjustment.",
        "timestamp": "2026-05-26T10:15:00Z",
    }),
    ("task-2026-005", True,  None),
]

EXPLANATIONS = [
    "Correct. You found the common denominator — next we practice mixed fractions.",
    "Correct. Solid pattern on equivalent fractions. Raising difficulty.",
    "Correct. You are nearing mastery threshold (0.90). One more step.",
    "Incorrect — likely a slip, not a gap. Teacher review requested.",
    "Correct. Mastery confirmed above 0.90. Moving to the next micro-skill.",
]


def build_session() -> dict:
    events = []
    p_l = P_INIT
    for i, ((task_id, correct, override), explanation) in enumerate(
        zip(TASK_SEQUENCE, EXPLANATIONS), start=1
    ):
        prior = round(p_l, 4)
        p_l = bkt_update(p_l, correct,
                         p_slip=BKT_PARAMS["p_slip"],
                         p_guess=BKT_PARAMS["p_guess"],
                         p_transit=BKT_PARAMS["p_transit"])
        posterior = round(p_l, 4)
        event = {
            "event_id":   i,
            "task_id":    task_id,
            "correct":    correct,
            "prior":      prior,
            "posterior":  posterior,
            "explanation": explanation,
        }
        if override:
            event["teacher_override"] = override
        events.append(event)

    return {
        "session_id":  "session-2026-05-26-001",
        "skill_id":    SKILL_ID,
        "bkt_params":  BKT_PARAMS,
        "events":      events,
    }


# ---------------------------------------------------------------------------
# Metadata for eatf-sign
# ---------------------------------------------------------------------------

def build_metadata() -> dict:
    return {
        "schema":           "urn:eatf:spec:aep:metadata:1.0",
        "attestation_id":   "att_matx_demo_2026_001",
        "created_at":       "2026-05-26T10:20:00Z",
        "agent_id":         "urn:eatf:tenant:matx:agent:bkt-tutor",
        "action_type":      "matx.bkt-session",
        "policy_id":        "matx-eu-ai-act-hri",
        "policy_version":   "1.0",
        "policy_coverage":  1.0,
        "policy_decision":  "allow",
        "format_version":   "ATAP-1.0",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    # Default: two levels up from examples/05-bkt-edu-demo/ = eatf repo root
    _auto_root = str(Path(__file__).resolve().parents[2])
    p.add_argument("--eatf-root", default=_auto_root,
                   help="Path to the EATF repository root (default: auto-detected)")
    p.add_argument("--out", default="session-2026-05-26-001.aep",
                   help="Output .aep file path (default: session-2026-05-26-001.aep)")
    args = p.parse_args()

    eatf_root = Path(args.eatf_root).resolve()
    sign_cli  = eatf_root / "cli" / "eatf-sign" / "bin" / "eatf-sign.js"
    tsa_src   = eatf_root / "test-vectors" / "valid" / "valid-overt-profile" / "package.aep"

    for required in [sign_cli, tsa_src]:
        if not required.exists():
            print(f"ERROR: not found: {required}", file=sys.stderr)
            print("Run: cd <eatf-root>/lib && npm install && npm run build", file=sys.stderr)
            print("     cd <eatf-root>/cli/eatf-sign && npm install", file=sys.stderr)
            return 1

    session  = build_session()
    metadata = build_metadata()

    print("\n=== BKT session generated ===")
    for ev in session["events"]:
        override_tag = "  [TEACHER OVERRIDE]" if "teacher_override" in ev else ""
        print(f"  event {ev['event_id']}: {'✓' if ev['correct'] else '✗'}  "
              f"{ev['skill_id'] if 'skill_id' in ev else SKILL_ID}  "
              f"{ev['prior']:.4f} → {ev['posterior']:.4f}{override_tag}")

    with tempfile.TemporaryDirectory() as tmp:
        payload_path  = os.path.join(tmp, "payload.json")
        meta_path     = os.path.join(tmp, "metadata.json")
        key_stem      = os.path.join(tmp, "demo-key")

        with open(payload_path,  "w") as f:
            json.dump(session,  f, indent=2)
        with open(meta_path,    "w") as f:
            json.dump(metadata, f, indent=2)

        # Generate a DEV RSA keypair
        print("\n=== Generating DEV keypair ===")
        r = subprocess.run(
            ["node", str(sign_cli), "--gen-rsa", key_stem],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print("ERROR generating keypair:", r.stderr, file=sys.stderr)
            return 1
        print(r.stdout.strip() or "  keypair written")

        # Sign
        print("\n=== Signing .aep ===")
        r = subprocess.run(
            [
                "node", str(sign_cli),
                "--payload",    payload_path,
                "--key",        key_stem + ".key",
                "--public-key", key_stem + ".pem",
                "--metadata",   meta_path,
                "--scope",      "foundational:aep-response",
                "--timestamp",  f"{tsa_src}:timestamp.tsr",
                "--out",        args.out,
            ],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print("ERROR signing:", r.stderr, file=sys.stderr)
            return 1
        print(r.stdout.strip() or f"  wrote {args.out}")

    print(f"\nDone. Evidence package: {args.out}")
    print("Verify with:")
    print(f"  eatf-verify-py {args.out}")
    print(f"  node {sign_cli.parent.parent / 'eatf-verify' / 'bin' / 'eatf-verify.js'} {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

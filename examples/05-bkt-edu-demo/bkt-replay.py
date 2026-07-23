#!/usr/bin/env python3
"""
bkt-replay.py — Extract a BKT session from a .aep evidence package and
independently replay the BKT calculations to confirm integrity.

This script does NOT check the cryptographic signatures — that is the job of
the EATF verifier.  It checks the *content* layer: given the recorded events
(task sequence, correct/incorrect answers, BKT parameters), can we re-derive
every recorded prior and posterior from scratch?

Usage:
    python scripts/bkt-replay.py session-2026-05-26-001.aep

Exit codes:
    0   All events replay correctly.
    1   One or more BKT posteriors do not match recorded values.
    2   File not found or payload not a valid BKT session JSON.
"""

import argparse
import json
import sys
import zipfile


TOLERANCE = 1e-3   # allow rounding differences up to 0.001


def bkt_update(p_l: float, correct: bool,
               p_slip: float = 0.1, p_guess: float = 0.2,
               p_transit: float = 0.1) -> float:
    """Bayesian Knowledge Tracing posterior update (mirrors bkt.py)."""
    if correct:
        cond = (p_l * (1 - p_slip)) / (p_l * (1 - p_slip) + (1 - p_l) * p_guess)
    else:
        cond = (p_l * p_slip) / (p_l * p_slip + (1 - p_l) * (1 - p_guess))
    return cond + (1 - cond) * p_transit


def replay(session: dict) -> bool:
    params   = session.get("bkt_params", {})
    p_slip   = params.get("p_slip",   0.1)
    p_guess  = params.get("p_guess",  0.2)
    p_transit= params.get("p_transit",0.1)
    events   = session.get("events",  [])

    if not events:
        print("ERROR: no events found in session payload", file=sys.stderr)
        return False

    skill_id = session.get("skill_id", "unknown")
    p_l      = params.get("p_init", 0.2)
    all_ok   = True

    print(f"\nBKT replay — skill: {skill_id}")
    print(f"  params: p_init={p_l}, p_slip={p_slip}, "
          f"p_guess={p_guess}, p_transit={p_transit}")
    print()

    for ev in events:
        eid        = ev["event_id"]
        correct    = ev["correct"]
        rec_prior  = ev["prior"]
        rec_post   = ev["posterior"]
        override   = ev.get("teacher_override")

        # Prior check
        prior_ok = abs(p_l - rec_prior) <= TOLERANCE
        # Compute expected posterior
        expected_post = bkt_update(p_l, correct, p_slip, p_guess, p_transit)
        post_ok  = abs(expected_post - rec_post) <= TOLERANCE

        status   = "OK" if (prior_ok and post_ok) else "MISMATCH"
        mark     = "✓" if correct else "✗"
        override_tag = "  ← TEACHER OVERRIDE" if override else ""
        print(
            f"  event {eid}: {mark}  "
            f"prior {rec_prior:.4f} (expected {p_l:.4f}) {'✓' if prior_ok else '✗'}  "
            f"posterior {rec_post:.4f} (expected {expected_post:.4f}) {'✓' if post_ok else '✗'}  "
            f"[{status}]{override_tag}"
        )

        if not (prior_ok and post_ok):
            all_ok = False

        p_l = expected_post   # advance state using re-computed value

    print()
    if all_ok:
        print(f"BKT trace reconstructed: {len(events)}/{len(events)} events match recorded posteriors.")
        if any("teacher_override" in e for e in events):
            for ev in events:
                if "teacher_override" in ev:
                    ov = ev["teacher_override"]
                    print(f"Teacher override at event {ev['event_id']}: "
                          f"action={ov.get('action')}, timestamp={ov.get('timestamp')}")
    else:
        fails = [e["event_id"] for e in events
                 if abs(bkt_update(
                     e["prior"], e["correct"], p_slip, p_guess, p_transit
                 ) - e["posterior"]) > TOLERANCE]
        print(f"BKT MISMATCH at event(s): {fails}")
        print("Recorded posteriors do not match re-derived values.")
        print("The session payload may have been tampered with.")

    return all_ok


def main() -> int:
    p = argparse.ArgumentParser(
        description="Replay BKT trace from a .aep session payload.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("aep", help=".aep evidence package to inspect")
    args = p.parse_args()

    if not __import__("os").path.exists(args.aep):
        print(f"ERROR: file not found: {args.aep}", file=sys.stderr)
        return 2

    try:
        with zipfile.ZipFile(args.aep, "r") as z:
            payload_bytes = z.read("response.txt")
    except KeyError:
        print("ERROR: response.txt not found in .aep archive", file=sys.stderr)
        return 2
    except zipfile.BadZipFile as e:
        print(f"ERROR: not a valid .aep archive: {e}", file=sys.stderr)
        return 2

    try:
        session = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"ERROR: payload is not valid JSON: {e}", file=sys.stderr)
        return 2

    if "events" not in session:
        print("ERROR: payload does not look like a BKT session (missing 'events' key)",
              file=sys.stderr)
        return 2

    ok = replay(session)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
tamper.py — silently modify a .aep evidence package for demo purposes.

Two modes:

  --flip-posterior-event-3  (DEFAULT DEMO MODE)
      Edits the BKT session JSON inside response.txt to add 0.05 to
      the recorded posterior at event 3.  This simulates a gradebook
      administrator quietly inflating a mastery score after the lesson.
      The EATF verifier catches it at step 4 (canonical re-derivation
      mismatch) and bkt-replay.py catches it independently (re-computed
      posterior does not match recorded value).

  --flip-canonical-bin
      Flips one byte in canonical.bin at the given offset.  Lower-level
      tamper: verifier catches it at step 4 but bkt-replay.py will still
      show the payload as intact (because response.txt was not touched).
      Useful for showing "any change is detected" without payload surgery.

Usage:
    python scripts/tamper.py session-2026-05-26-001.aep --flip-posterior-event-3
    python scripts/tamper.py session-2026-05-26-001.aep --flip-canonical-bin --flip-offset 128

Exit codes:
    0   Tampered package written.
    1   Input not found / structural error.
    2   Bad arguments.
"""

import argparse
import json
import os
import sys
import zipfile


def _write_zip(output_path: str, entries: dict[str, bytes], names_order: list[str]) -> None:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_STORED) as zout:
        for name in sorted(names_order):
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_STORED
            zout.writestr(info, entries[name])


def tamper_payload(input_path: str, output_path: str, event_id: int, delta: float) -> int:
    """Modify response.txt: add `delta` to event `event_id`'s posterior."""
    if not os.path.exists(input_path):
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(input_path, "r") as zin:
        names   = zin.namelist()
        entries = {n: zin.read(n) for n in names}

    if "response.txt" not in entries:
        print("ERROR: response.txt not found in .aep archive", file=sys.stderr)
        return 1

    try:
        session = json.loads(entries["response.txt"].decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"ERROR: response.txt is not valid JSON: {e}", file=sys.stderr)
        return 1

    if "events" not in session:
        print("ERROR: response.txt does not look like a BKT session "
              "(missing 'events' key)", file=sys.stderr)
        return 1

    target = next((e for e in session["events"] if e["event_id"] == event_id), None)
    if target is None:
        print(f"ERROR: event_id {event_id} not found in session", file=sys.stderr)
        return 1

    original_posterior = target["posterior"]
    target["posterior"] = round(target["posterior"] + delta, 4)

    entries["response.txt"] = json.dumps(session, indent=2).encode("utf-8")

    _write_zip(output_path, entries, names)

    print(f"\nTampered {input_path}")
    print(f"  Mode:      payload surgery (response.txt → event {event_id} posterior)")
    print(f"  Change:    {original_posterior:.4f} → {target['posterior']:.4f} "
          f"(+{delta:.2f})")
    print(f"  Output:    {output_path}")
    print()
    print("Expected verifier behaviour:")
    print("  eatf-verify-py: verify=false  (canonical.bin no longer matches "
          "re-derived form)")
    print("  bkt-replay.py:  event 3 MISMATCH (recorded posterior does not "
          "match re-computed value)")
    return 0


def tamper_canonical_bin(input_path: str, output_path: str, offset: int) -> int:
    """Flip one byte in canonical.bin."""
    if not os.path.exists(input_path):
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(input_path, "r") as zin:
        names   = zin.namelist()
        entries = {n: zin.read(n) for n in names}

    if "canonical.bin" not in entries:
        print("ERROR: canonical.bin not found in .aep archive", file=sys.stderr)
        return 1

    data = bytearray(entries["canonical.bin"])
    if offset >= len(data):
        print(f"ERROR: offset {offset} is out of range "
              f"(canonical.bin is {len(data)} bytes)", file=sys.stderr)
        return 1

    original       = data[offset]
    data[offset]   = (data[offset] + 1) % 256
    entries["canonical.bin"] = bytes(data)

    _write_zip(output_path, entries, names)

    print(f"\nTampered {input_path}")
    print(f"  Mode:     canonical.bin byte flip")
    print(f"  Offset:   {offset}")
    print(f"  Change:   0x{original:02x} → 0x{data[offset]:02x}")
    print(f"  Output:   {output_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Silently modify a .aep evidence package (demo tamper tool).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("input", help=".aep input file")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--flip-posterior-event-3",
        action="store_true",
        default=True,
        help="(Default) Inflate BKT posterior at event 3 by +0.05 in response.txt.",
    )
    mode.add_argument(
        "--flip-canonical-bin",
        action="store_true",
        help="Flip one byte in canonical.bin at --flip-offset.",
    )

    p.add_argument(
        "--flip-offset", type=int, default=128,
        help="Byte offset for --flip-canonical-bin (default: 128).",
    )
    p.add_argument(
        "--event-id", type=int, default=3,
        help="Event ID to tamper for --flip-posterior-event-3 (default: 3).",
    )
    p.add_argument(
        "--delta", type=float, default=0.05,
        help="Posterior inflation for --flip-posterior-event-3 (default: +0.05).",
    )
    args = p.parse_args()

    base, ext = os.path.splitext(args.input)
    output    = f"{base}-tampered{ext}"

    if args.flip_canonical_bin:
        return tamper_canonical_bin(args.input, output, args.flip_offset)
    else:
        return tamper_payload(args.input, output, args.event_id, args.delta)


if __name__ == "__main__":
    sys.exit(main())

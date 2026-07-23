# Example 05 — BKT Education Demo

End-to-end demonstration for the AIED 2026 Interactive Events submission:
*"MATx Evidence Replayer: cryptographic attestation for a Bayesian Knowledge Tracing tutor
under EU AI Act evidence requirements."*

This example shows how to package a synthetic BKT (Bayesian Knowledge Tracing) learner
session as an EATF `.aep` evidence package, verify it with two independent verifiers, and
detect silent tampering at both the cryptographic and content layers.

---

## Scripts

| Script | Purpose |
|--------|---------|
| `demo-bkt-session.py` | Generate a 5-event BKT session JSON and sign it as a `.aep` using `eatf-sign` |
| `tamper.py` | Inflate event 3 posterior in `response.txt` (+0.05) — triggers canonical mismatch |
| `bkt-replay.py` | Re-derive BKT posteriors from `.aep` payload and compare to recorded values |

All scripts are self-contained Python 3.11+. No MATx installation required.

---

## Quick start

```bash
# From the eatf repo root:

# 1. Build the verifier and sign CLI (one-off)
cd lib && npm install && npm run build && cd ..
cd cli/eatf-sign && npm install && cd ../..
cd cli/eatf-verify && npm install && cd ../..

# 2. Install the Python verifier
pip install -e lib-python/

# 3. Generate the demo .aep
python examples/05-bkt-edu-demo/demo-bkt-session.py
# → session-2026-05-26-001.aep

# 4. Verify (two independent verifiers)
eatf-verify-py session-2026-05-26-001.aep
node cli/eatf-verify/bin/eatf-verify.js session-2026-05-26-001.aep

# 5. Replay the BKT trace
python examples/05-bkt-edu-demo/bkt-replay.py session-2026-05-26-001.aep

# 6. Tamper and re-verify
python examples/05-bkt-edu-demo/tamper.py session-2026-05-26-001.aep --flip-posterior-event-3
eatf-verify-py session-2026-05-26-001-tampered.aep
python examples/05-bkt-edu-demo/bkt-replay.py session-2026-05-26-001-tampered.aep
```

---

## BKT session (fractions.add, default params)

| Event | Correct? | Prior  | Posterior | Note |
|-------|----------|--------|-----------|------|
| 1     | ✓        | 0.2000 | 0.5765    | |
| 2     | ✓        | 0.5765 | 0.8737    | |
| 3     | ✓        | 0.8737 | 0.9720    | tamper target: inflated to 1.0220 |
| 4     | ✗        | 0.9720 | 0.8314    | TEACHER OVERRIDE |
| 5     | ✓        | 0.8314 | 0.9612    | |

BKT parameters (Corbett & Anderson 1995 defaults):
`p_init=0.20, p_transit=0.10, p_slip=0.10, p_guess=0.20`

---

## What the tamper demo shows

When `tamper.py --flip-posterior-event-3` runs, it edits `response.txt` inside the `.aep`
(the BKT session JSON) to add `+0.05` to event 3's recorded posterior. The `.aep` file
is a ZIP; we repack it without updating `canonical.bin` (which was computed from the
original `response.txt`).

Two tools independently detect this:

1. **`eatf-verify-py`** — fails at step 4 (canonical re-derivation):
   `canonical.bin does not match a supported canonical form.`

2. **`bkt-replay.py`** — fails at event 3 content check:
   `BKT MISMATCH at event(s): [3]`

Neither tool requires the other. This is the integrity layer described in the paper.

---

## EU AI Act mapping

| EATF element | EU AI Act article |
|---|---|
| Signed canonical record per event | Art. 12 — logging |
| Explanation field in session JSON | Art. 13 — transparency |
| `teacher_override` field, signed | Art. 14 — human oversight |

---

## License

MIT (same as the eatf repository root).

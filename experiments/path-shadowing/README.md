# Path shadowing, demonstrated on shipped code

A negative control can be well formed, be correctly rejected by every
implementation, and still fail to exercise the decision state it was written to
test. A boolean pass/fail suite records that as a success.

This experiment shows the phenomenon on the shipped verifiers, from one valid
seed package, with the expected outcome for each case declared in `oracle.json`
**before** the run.

Four cases, in two matched pairs. The naive and refined members of each pair
differ only in whether the OVERT receipt's witness reference to the mutated
entry is cleared, and the receipt re-signed, before the entry is altered.

| case | targets | observed in both implementations | outcome |
|---|---|---|---|
| `naive-remove-receipt-signature` | `OVERT_SIGNATURE_REQUIRED` | `OVERT_INVALID` | shadowed |
| `refined-remove-receipt-signature` | `OVERT_SIGNATURE_REQUIRED` | `OVERT_SIGNATURE_REQUIRED` | reaches target |
| `naive-empty-timestamp` | `TSA_MISSING_OR_INVALID` | `OVERT_INVALID` | shadowed |
| `refined-empty-timestamp` | `TSA_MISSING_OR_INVALID` | `TSA_MISSING_OR_INVALID` | reaches target |

All four packages are rejected by both implementations, and TypeScript and
Python agree on all four. Only the declared-first-state comparison separates
the two rows that tested what they meant to test from the two that did not.

## Relation to the calibration pilot

`../decision-path/PILOT.md` records that the same two operators shadowed during
the project's first calibration run, and that a cross-language difference in
the witness-reference check was found and fixed at that time (commit
`1a73f19`). **That pilot's raw per-case output was never deposited**, and the
Python check has since been aligned, so the historical cross-language
divergence cannot be reproduced from any public commit — the fix commit's diff
is the evidence that it existed. This experiment therefore demonstrates the
shadowing phenomenon rather than replaying the pilot, and its numbers are the
ones to cite.

## Run it

```sh
python experiments/path-shadowing/run_experiment.py
```

Offline after dependency installation. Deterministic: two consecutive runs
produce a byte-identical `generated/SHA256SUMS`.

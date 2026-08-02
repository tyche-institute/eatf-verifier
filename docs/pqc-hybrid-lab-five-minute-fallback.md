# Five-minute no-network fallback for the PQC hybrid lab

This facilitator overlay is used when participant setup fails, no live terminal
is available, or the remaining session time is reduced to five minutes. It
uses the immutable v0.6.1 prepared results; it does not replace or modify the
released workshop ZIP.

Keep local copies of:

- the [v0.6.1 conference ZIP](https://github.com/tyche-institute/eatf-verifier/releases/download/v0.6.1/eatf-pqc-hybrid-lab-v0.6.1.zip);
- its [published SHA-256 file](https://github.com/tyche-institute/eatf-verifier/releases/download/v0.6.1/eatf-pqc-hybrid-lab-v0.6.1.zip.sha256);
- the released [annotated transcript](https://github.com/tyche-institute/eatf-verifier/blob/v0.6.1/workshops/pqc-hybrid-lab/EXPECTED-TRANSCRIPT.md).

Display the transcript rather than improvising terminal output.

| Time | Display or say | Required result |
|---:|---|---|
| 0:00–0:30 | State that both signatures cover the same canonical bytes and every displayed row is a prepared offline result. | The audience knows this is a replay, not a live-service claim. |
| 0:30–1:10 | Define `transitional` as “verify PQC if present” and `required` as “reject evidence without PQC.” | The two relying-party policies are distinct. |
| 1:10–1:45 | Highlight `01-valid-hybrid.aep` under `required`. | Both verifiers accept, establishing the positive cross-implementation baseline. |
| 1:45–2:25 | Highlight `02-pqc-signature-tampered.aep`. | Both reach `PQC_SIGNATURE_INVALID`; RSA does not mask a bad ML-DSA signature. |
| 2:25–3:10 | Highlight `03-pqc-pair-stripped.aep` under `transitional`. | Signed witness binding rejects stripping with `OVERT_INVALID`. |
| 3:10–4:10 | Contrast both `04-classical-transition.aep` rows. | The legitimate classical package passes transition policy and fails only when PQC is required. |
| 4:10–4:35 | Point to the incomplete-pair and changed-payload controls. | Structural and canonical failures occur before policy can make invalid evidence acceptable. |
| 4:35–5:00 | Ask attendees to write one evidence class or cut-over date after which their relying party must select `required`. | The fallback still produces an actionable acceptance rule. |

Close on the transcript's final line:

```text
Cross-language policy mismatches: 0
```

Do not claim that the table was generated live. The public release is
independently reproducible, and its published ZIP is continuously downloaded,
checksum-verified, extracted, and replayed on Ubuntu, macOS, and Windows by the
repository's CI workflow.

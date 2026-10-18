# Five-minute no-network fallback for the PQC hybrid lab

This facilitator overlay is used when participant setup fails, no live terminal
is available, or the remaining session time is reduced to five minutes. It
uses the immutable v0.7.0 prepared results; it does not replace or modify the
released workshop ZIP.

The v0.6.1 results (six packages, two policies, 24 observations) remain
published in the
[v0.6.1 conference ZIP](https://github.com/tyche-institute/eatf-verifier/releases/download/v0.6.1/eatf-pqc-hybrid-lab-v0.6.1.zip).
They predate the ML-DSA-65 signer-key pin, so they contain neither package 07
nor the `pinned` policy. `required` alone has never been enough: a package can
carry any ML-DSA-65 key.

Keep local copies of:

- the [v0.7.0 conference ZIP](https://github.com/tyche-institute/eatf-verifier/releases/download/v0.7.0/eatf-pqc-hybrid-lab-v0.7.0.zip);
- its [published SHA-256 file](https://github.com/tyche-institute/eatf-verifier/releases/download/v0.7.0/eatf-pqc-hybrid-lab-v0.7.0.zip.sha256);
- the released [annotated transcript](https://github.com/tyche-institute/eatf-verifier/blob/v0.7.0/workshops/pqc-hybrid-lab/EXPECTED-TRANSCRIPT.md).

Display the transcript rather than improvising terminal output.

| Time | Display or say | Required result |
|---:|---|---|
| 0:00–0:25 | State that both signatures cover the same canonical bytes and every displayed row is a prepared offline result. | The audience knows this is a replay, not a live-service claim. |
| 0:25–1:00 | Define `transitional` as “verify PQC if present”, `required` as “reject evidence without PQC”, and `pinned` as `required` plus the expected RSA and ML-DSA-65 keys. | The three relying-party policies are distinct. |
| 1:00–1:30 | Highlight `01-valid-hybrid.aep` under `required` and `pinned`. | Both verifiers accept, establishing the positive cross-implementation baseline. |
| 1:30–2:00 | Highlight `02-pqc-signature-tampered.aep`. | Both reach `PQC_SIGNATURE_INVALID`; RSA does not mask a bad ML-DSA signature. |
| 2:00–2:30 | Highlight `03-pqc-pair-stripped.aep` under `transitional`. | Signed witness binding rejects stripping with `OVERT_INVALID`. |
| 2:30–3:15 | Contrast the `04-classical-transition.aep` rows. | The legitimate classical package passes transition policy and fails once PQC is required. |
| 3:15–4:15 | Contrast the three `07-foreign-mldsa-key.aep` rows. | A foreign ML-DSA-65 key over the same bytes passes `required`; only `pinned` rejects it, with `PQC_SIGNER_NOT_TRUSTED`. `required` proves that an ML-DSA signature exists, not whose key made it. |
| 4:15–4:35 | Point to the incomplete-pair and changed-payload controls. | Structural and canonical failures occur before policy can make invalid evidence acceptable. |
| 4:35–5:00 | Ask attendees to write one evidence class or cut-over date after which their relying party must select `required` and pin the expected ML-DSA-65 key. | The fallback still produces an actionable acceptance rule. |

Close on the transcript's final line:

```text
Cross-language policy mismatches: 0
```

Do not claim that the table was generated live. The public release is
independently reproducible, and its published ZIP is continuously downloaded,
checksum-verified, extracted, and replayed on Ubuntu, macOS, and Windows by the
repository's CI workflow.

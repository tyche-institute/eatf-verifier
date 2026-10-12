# `eatf-verify`

Offline TypeScript CLI over [`@eatf/verifier`](../../lib).

```bash
eatf-verify [--signer-key expected.pem] action.aep
eatf-verify --batch received-packages/
eatf-verify --conformance test-vectors/
eatf-verify --json action.aep
eatf-verify --require-pqc hybrid.aep
eatf-verify --require-pqc --signer-key expected.pem \
  --pqc-signer-key expected-mldsa65.pem hybrid.aep
```

Important options:

- `--signer-key PEM` requires the embedded SPKI public key to match one of
  the caller-supplied keys. Repeat it for key rotation.
- `--tsa-trust-list PEM` performs only the documented advisory issuer-name
  pin. It is not RFC 5280 path validation.
- `--pqc-signer-key PEM` requires the embedded ML-DSA-65 key to match one of
  the caller-supplied keys (RFC 9881 SPKI or legacy raw-key PEM, compared on
  the decoded key). Repeatable; it implies `--require-pqc`. A mismatch fails
  with `PQC_SIGNER_NOT_TRUSTED`. A file that is not an ML-DSA-65 public key
  exits with status 2.
- `--require-pqc` rejects packages without a complete, valid ML-DSA-65 pair.
  Without it, classical-only transition packages remain acceptable. Without
  `--pqc-signer-key` it does not establish whose ML-DSA-65 key signed; the CLI
  then prints a warning to stderr, which does not change the exit status or
  the `--json` output on stdout.
- `--conformance` expects packages under `valid/` to pass and packages under
  `invalid/` to fail. A tree with no packages under either is an input error
  (exit 2), not a pass.

Exit status is 0 when all requested assertions hold, 1 when a package fails,
and 2 for usage or input errors. The CLI makes no network calls.

Without `--signer-key`, verification establishes package consistency and a
valid signature under the embedded key; it does not identify the owner of that
key. The same holds separately for the ML-DSA-65 key and `--pqc-signer-key`.

Apache-2.0; see [`../../LICENSE`](../../LICENSE).

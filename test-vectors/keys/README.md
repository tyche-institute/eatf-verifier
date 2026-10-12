# Public development keys

Every private key in this directory is intentionally public and is suitable
only for tests.

| File | Purpose |
|---|---|
| `dev-rsa-4096.key` / `.pem` | RSA package signer fixture |
| `dev-tsa-rsa-3072.key` / `.pem` | Self-signed TEST-ONLY RFC 3161 TSA fixture |
| `dev-mldsa65.pem` | RFC 9881 public key of the ML-DSA-65 workshop signer, for `--pqc-signer-key` |

`dev-mldsa65.pem` is written by `scripts/generate-pqc-workshop.mjs`. Its
private key is derived from the public seed
SHA-256(`EATF public PKIC PQC workshop seed v1`), so it is just as public as
the RSA fixtures. It signs `valid/hybrid-mldsa65` and the hybrid workshop
packages.

The TSA certificate has a critical `timeStamping` extended key usage and is
used by `scripts/regenerate-test-timestamps.py`. The test vectors embed the TSA
signing certificate in each generated token.

Do not trust these keys for real evidence. A production deployment must
control private-key custody and distribute signer/TSA trust material through
an authenticated channel outside the AEP itself.

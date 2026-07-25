# Public development keys

Every private key in this directory is intentionally public and is suitable
only for tests.

| File | Purpose |
|---|---|
| `dev-rsa-4096.key` / `.pem` | RSA package signer fixture |
| `dev-tsa-rsa-3072.key` / `.pem` | Self-signed TEST-ONLY RFC 3161 TSA fixture |

The TSA certificate has a critical `timeStamping` extended key usage and is
used by `scripts/regenerate-test-timestamps.py`. The test vectors embed the TSA
signing certificate in each generated token.

Do not trust these keys for real evidence. A production deployment must
control private-key custody and distribute signer/TSA trust material through
an authenticated channel outside the AEP itself.

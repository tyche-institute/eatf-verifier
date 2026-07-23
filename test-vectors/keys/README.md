# test-vectors/keys/ — development RSA keypair

This directory contains a **development-only** RSA-4096 keypair used
to produce the round-trip conformance vector under
[`../valid/minimal-roundtrip/`](../valid/minimal-roundtrip/).

## Files

| File              | Contents                          | Public? |
|-------------------|-----------------------------------|---------|
| `dev-rsa-4096.key`| PKCS#8 PEM private key            | YES — checked into the repo. |
| `dev-rsa-4096.pem`| SPKI PEM public key               | YES.    |

**Both halves of the keypair are public.** This is intentional: anyone
cloning the repo can independently regenerate the conformance vector
from the same inputs and confirm byte-equality with the committed
package.

## Do NOT use these keys for production attestations

Real attestations require an issuer keypair whose **private** half:

- Was generated in a hardware security module (HSM) or a process whose
  custody you control.
- Has never been written to disk in plaintext.
- Is rotated on a documented schedule.
- Has a public-key history mirror (see
  [`tyche-institute/eatf-trust-anchors`](https://github.com/tyche-institute/eatf-trust-anchors))
  so that verifiers can pin an issuer's anchor without trusting a
  central directory.

Verifiers running against production attestations should reject any
package whose `public_key.pem` matches this dev key. The fingerprint
of `dev-rsa-4096.pem` is intentionally well-known (it can be
computed by hashing the PEM body); operators should treat it as a
known-bad anchor.

## Regenerating

```bash
node cli/eatf-sign/bin/eatf-sign.js --gen-rsa test-vectors/keys/dev-rsa-4096
```

This overwrites both files with a fresh keypair. The
`minimal-roundtrip` vector should be regenerated immediately after
(see its [`README.md`](../valid/minimal-roundtrip/README.md)).

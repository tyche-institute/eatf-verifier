# test-vectors/keys/ — development RSA keys

This directory contains a **development-only** RSA-4096 keypair used
to produce the round-trip conformance vector under
[`../valid/minimal-roundtrip/`](../valid/minimal-roundtrip/), plus an
unrelated public key used as a negative fixture.

## Files

| File                     | Contents                     | Public? |
|--------------------------|------------------------------|---------|
| `dev-rsa-4096.key`       | PKCS#8 PEM private key        | YES — checked into the repo. |
| `dev-rsa-4096.pem`       | SPKI PEM public key           | YES.    |
| `untrusted-rsa-4096.pem` | SPKI PEM public key, unrelated to the dev key | YES — public key only; no private half committed. |
| `test-accepting-authority.key` | PKCS#8 PEM private key of the TEST accepting authority | YES — checked into the repo. |
| `test-accepting-authority.pem` | SPKI PEM public key of the TEST accepting authority | YES.    |
| `test-granting-authority.key` | PKCS#8 PEM private key of the TEST granting authority (§4.5 mandates) | YES — checked into the repo. |
| `test-granting-authority.pem` | SPKI PEM public key of the TEST granting authority | YES.    |
| `reauthoring-adversary-4096.key` | PKCS#8 PEM private key of the re-authoring adversary fixture | YES — checked into the repo. |
| `reauthoring-adversary-4096.pem` | SPKI PEM public key of the re-authoring adversary fixture | YES.    |

**Both halves of the dev keypair are public.** This is intentional:
anyone cloning the repo can independently regenerate the conformance
vector from the same inputs and confirm byte-equality with the
committed package.

`test-accepting-authority` is the named principal whose signature
accepts the warrant in [`../valid/warranted-action/`](../valid/warranted-action/)
and the `../warrant/` behavioural vectors; both halves are public for
the same reproduce-the-vector reason. It is a **TEST principal only** —
who signs acceptance for production warrants, and under what custody, is
a governance question out of scope for these fixtures.

`test-granting-authority` is the deontic principal that signs the
detached `mandate.json` records of §4.5 — the vectors under
[`../mandate/`](../mandate/) and the three `valid/mandated-*` packages.
It is a **third** principal, distinct from both the package issuer
(`dev-rsa-4096`) and the epistemic `test-accepting-authority`, so a
package carrying both authority layers carries three separate keys and
the verifier's two gated signature checks answer to two different
holders. It is a **TEST principal only**: who grants mandates in
production, and under what custody, is a governance question out of
scope for these fixtures.

`reauthoring-adversary-4096` belongs to the adversary of
[`../boundary/reauthored-package-issuer-substitution/`](../boundary/reauthored-package-issuer-substitution/):
a party who holds a signing key of its own, but not the issuer's. Both
halves are committed so that vector — the one showing what the profile
canonical form does *not* close — regenerates byte-identically. Nothing
in the repository trusts this key.

`untrusted-rsa-4096.pem` is a valid but unrelated RSA-4096 public key.
It is swapped into the `untrusted-issuer` invalid vector by
[`../../scripts/generate-invalid-vectors.mjs`](../../scripts/generate-invalid-vectors.mjs):
the signature in that package was made with the dev key, so it does not
verify against this one. It is committed (rather than generated at
runtime) so the invalid vector regenerates byte-identically. Only the
public half is needed — nothing is ever signed with it.

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

# `eatf-verifier` (Python)

Offline Python verifier for EATF `.aep` evidence packages. Fresh
port of the canonical TypeScript implementation in [`lib/`](../lib/),
validated against the shared conformance set in
[`test-vectors/`](../test-vectors/).

Same trust model, same wire format, same `verify=true | false`
contract. No managed-service surface; no network calls.

## Install

```bash
pip install eatf-verifier            # classical signatures only
pip install eatf-verifier[pqc]       # + ML-DSA-65 post-quantum (needs liboqs)
```

Requires Python 3.11+. The `[pqc]` extra installs `oqs-python`,
which in turn requires the `liboqs` shared library to be present
on the system. Without `[pqc]`, the verifier still accepts
packages that lack a ML-DSA-65 signature (the v0.1 reference
fixtures fall into this category); packages carrying
`signature_pqc.sig` will be rejected as "ML-DSA-65 support not
compiled in" when the extra is absent.

## Usage

### Library

```python
from eatf_verifier import verify

with open("action.aep", "rb") as f:
    aep_bytes = f.read()

result = verify(aep_bytes)
print(result.valid)            # bool
print(result.failure_reason)   # str | None
print(result.report)           # list[str] — diagnostic lines
print(result.metadata)         # dict — parsed metadata.json
print(result.overt_receipt)    # dict — parsed overt_receipt.json
```

### CLI

```bash
eatf-verify-py action.aep
eatf-verify-py --conformance ../test-vectors/
eatf-verify-py --json action.aep | jq .
```

Exit codes match the Node CLI: `0` all verified; `1` at least one
failure; `2` bad CLI usage or unreadable file.

## What this implementation does NOT yet do

- **Full RFC 5280 certificate path validation for TSAs.** As of
  v0.2.1 the port performs the same *single-step pin* check the
  TypeScript reference does: the TSA signing cert's issuer DN
  must equal one of the pinned roots' subject DN
  (`DEFAULT_TSA_TRUST_LIST` ships the three DigiCert public
  roots). Multi-step chain walking with intermediate-CA
  enrolment and revocation handling is a planned 0.3.x feature
  in both verifiers.
- **W3C VC `attestations/agent.vc.json` parsing.** Neither the
  TypeScript reference nor this port handles the optional VC
  entry yet (see [`../docs/attestation-profile.md`](../docs/attestation-profile.md)).

Behaviour parity with the TS reference is otherwise tested via
the shared `test-vectors/` set.

## Conformance

Run the conformance test from the project root after install:

```bash
python -m eatf_verifier.cli --conformance ../test-vectors/
```

Expected output (matches the TS reference):

```
Conformance: 4 verified, 7 rejected, 0 contract mismatches.
```

The Python implementation is a v0.1-conformant verifier if it
matches the `verify=true | false` outcome for every vector. The
diagnostic text MAY differ from the TS reference.

## Why a fresh port

The Python port is intentionally a re-implementation, not a
translation:

- The TypeScript reference exists to be the canonical source of
  truth for the v0.1 line. Two independent implementations,
  validated against the same conformance set, empirically prove
  the spec is implementable from documentation alone.
- The Python port shares no code with the TS reference. Bugs in
  one don't propagate to the other.
- Operators choosing Python for their integration get a
  first-class verifier, not a bridge.

The cryptography choices follow Python ecosystem conventions:

- `cryptography` (pyca) for RSA, SHA-256, X.509.
- `asn1crypto` for CMS / RFC 3161 token parsing.
- `oqs-python` for ML-DSA-65 (optional extra).
- `zipfile` from the standard library for the AEP envelope.
- `json` from the standard library for canonical JSON (with
  a hand-written JCS pass).

## License

Apache License 2.0 — see [`../LICENSE`](../LICENSE).

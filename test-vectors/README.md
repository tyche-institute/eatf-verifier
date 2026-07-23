# test-vectors/ — conformance test vectors

Two sibling subdirectories:

- `valid/` — packages that MUST verify cleanly. Every implementation
  claiming v0.1 conformance must report `verify=true` for every
  package under this tree.
- `invalid/` — packages that MUST fail verification. Each subdirectory
  exercises one specific failure mode and ships a `verify-expected.txt`
  naming the diagnostic the verifier should report.

## Vector layout

```
<vector-name>/
├── package.aep
├── verify-expected.txt     # the verify=true/false contract
└── README.md               # what this vector exercises
```

## v0.1 vectors

| Vector                                             | Expected             | Exercises                                                                    |
|----------------------------------------------------|----------------------|------------------------------------------------------------------------------|
| `valid/valid-overt-profile/`                       | `verify=true`        | Full happy-path. OVERT foundational scope.                                   |
| `valid/mcp-tools-call-valid/`                      | `verify=true`        | OVERT `agentic-extended:mcp-tools-call`, policy decision `allow`.            |
| `valid/mcp-tools-call-denied-policy/`              | `verify=true`        | Same scope, policy decision `deny` — AEP authentic; call rejected by policy. |
| `valid/minimal-roundtrip/`                         | `verify=true`        | Round-trip baseline produced by `eatf-sign` from `test-vectors/keys/dev-rsa-4096`. |
| `invalid/tampered-canonical-bin/`                  | `verify=false`       | Hash-chain mismatch (`canonical.bin` byte-flipped after signing).            |
| `invalid/tampered-metadata/`                       | `verify=false`       | `metadata.policy_decision` changed; OVERT receipt cross-check fails.         |
| `invalid/bad-signature-classical/`                 | `verify=false`       | `signature.sig` byte-flipped; RSASSA-PKCS1-v1_5 verification fails.          |
| `invalid/untrusted-issuer/`                        | `verify=false`       | `public_key.pem` swapped for an unrelated valid RSA key.                     |
| `invalid/missing-canonical-bin/`                   | `verify=false`       | Required `canonical.bin` entry absent from the envelope.                     |
| `invalid/bad-timestamp/`                           | `verify=false`       | `timestamp.tsr` ASN.1 mangled; RFC 3161 token unparseable.                   |
| `invalid/tampered-overt-receipt/`                  | `verify=false`       | Hash-chain mismatch on `overt_receipt.json` (post-sign tamper).              |

The six new invalid vectors land in v0.1.4. They are produced
deterministically by `scripts/generate-invalid-vectors.mjs` from
the `minimal-roundtrip` baseline; regenerating produces byte-
identical files. The script lives in the repo so any downstream
implementer can audit the tamper logic.

## Running conformance

```bash
cd lib && npm install && npm run build && cd ..
cd cli/eatf-verify && npm install && cd ../..

node cli/eatf-verify/bin/eatf-verify.js --conformance test-vectors/
```

Expected output:
```
PASS  package.aep  expected=false  actual=false  (RSA signature does not verify against public_key.pem.)
PASS  package.aep  expected=false  actual=false  (timestamp.tsr missing or empty.)
PASS  package.aep  expected=false  actual=false  (Missing required entry: canonical.bin.)
PASS  package.aep  expected=false  actual=false  (canonical.bin does not match a supported canonical form.)
PASS  package.aep  expected=false  actual=false  (overt_receipt.json invalid: policy.decision does not match metadata.policy_decision.)
PASS  package.aep  expected=false  actual=false  (overt_receipt.json invalid: content_hash does not match hash.sha256.)
PASS  package.aep  expected=false  actual=false  (RSA signature does not verify against public_key.pem.)
PASS  package.aep  expected=true   actual=true
PASS  package.aep  expected=true   actual=true
PASS  package.aep  expected=true   actual=true
PASS  package.aep  expected=true   actual=true

Conformance: 4 verified, 7 rejected, 0 contract mismatches.
```

Implementations claiming v0.1 conformance run their own verifier
against every `valid/<vector>/package.aep` and every
`invalid/<vector>/package.aep` and report `PASS` (verify equals
expected) for every vector. The exact diagnostic text may differ
between implementations; the conformance contract only requires
the `verify=true|false` boolean.

More vectors will be added in successive 0.1.x point releases.

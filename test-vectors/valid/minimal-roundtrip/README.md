# `minimal-roundtrip/`

**Expected:** `verify=true`.

A round-trip-generated AEP: produced by `eatf-sign` (from the same
repository) using the dev RSA key at
[`test-vectors/keys/dev-rsa-4096.{key,pem}`](../../keys/) and verified
by `eatf-verify`. The presence of this vector demonstrates that the
signer and the verifier in this repository agree end-to-end.

The RFC 3161 timestamp token is reused from
`valid-overt-profile/package.aep` rather than freshly minted (so the
test is fully offline). The verifier accepts mismatched-imprint
timestamps with a warning under the "Java reference compatibility"
path; the SignerInfo signature embedded in the token still verifies
against its own certificate, which is what matters for the structural
check.

## Reproducing this vector

```bash
# 1. Build the verifier and signer.
(cd lib && npm install && npm run build)
(cd cli/eatf-sign && npm install)

# 2. Re-sign.
echo "EATF v0.1.3 round-trip demo: signed by dev-rsa-4096, verified offline." \
  > /tmp/payload.txt
cat > /tmp/meta.json <<'JSON'
{
  "schema": "urn:eatf:spec:aep:metadata:1.0",
  "attestation_id": "att_minimal_roundtrip_01",
  "created_at": "2026-05-15T20:00:00Z",
  "agent_id": "urn:eatf:tenant:demo:agent:roundtrip-demo",
  "action_type": "foundational:aep-response",
  "policy_id": "atap-basic",
  "policy_version": "1.0",
  "policy_coverage": 1.0,
  "policy_decision": "allow",
  "format_version": "ATAP-1.0"
}
JSON
node cli/eatf-sign/bin/eatf-sign.js \
  --payload /tmp/payload.txt \
  --key test-vectors/keys/dev-rsa-4096.key \
  --public-key test-vectors/keys/dev-rsa-4096.pem \
  --metadata /tmp/meta.json \
  --scope foundational:aep-response \
  --timestamp test-vectors/valid/valid-overt-profile/package.aep:timestamp.tsr \
  --out /tmp/regenerated.aep

# 3. Verify.
node cli/eatf-verify/bin/eatf-verify.js /tmp/regenerated.aep
# → verify=true
```

The regenerated `.aep` will differ from the committed one by exactly
one timestamp/nonce-influenced byte sequence (the RSA signature is
deterministic for the same inputs under RSASSA-PKCS1-v1_5, and JCS
output is deterministic; the only randomness in the package comes from
the embedded timestamp, which is reused verbatim). Hash comparisons
against the committed file are therefore meaningful as a regression
check.

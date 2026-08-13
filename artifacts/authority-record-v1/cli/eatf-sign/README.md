# `eatf-sign` — offline CLI signer

Command-line tool for producing EATF `.aep` evidence packages. Thin
wrapper around the `sign()` export of [`@eatf/verifier`](../../lib) —
no network calls; the RFC 3161 timestamp token is supplied as a file.

## Install

Requires Node 20 or later. From a clone of the repository:

```bash
cd lib && npm install && npm run build && cd ..
cd cli/eatf-sign && npm install && cd ../..
```

## Usage

### Round-trip demo

```bash
# 1. Generate a dev keypair (one-off; clearly marked as DEV).
node cli/eatf-sign/bin/eatf-sign.js --gen-rsa /tmp/dev-key

# 2. Build a payload and minimal metadata.
echo "Hello, world." > /tmp/payload.txt
cat > /tmp/meta.json <<'JSON'
{
  "schema": "urn:eatf:spec:aep:metadata:1.0",
  "attestation_id": "att_demo_01",
  "created_at": "2026-05-15T00:00:00Z",
  "agent_id": "urn:eatf:tenant:demo:agent:hello",
  "action_type": "demo.hello-world",
  "policy_id": "atap-basic",
  "policy_version": "1.0",
  "policy_coverage": 1.0,
  "policy_decision": "allow",
  "format_version": "ATAP-1.0"
}
JSON

# 3. Sign. The --timestamp argument reuses an RFC 3161 token from an
#    existing fixture (verifier accepts mismatched-imprint timestamps
#    for backwards compatibility). Replace with --timestamp <real.tsr>
#    if you have a fresh one from a TSA.
node cli/eatf-sign/bin/eatf-sign.js \
  --payload /tmp/payload.txt \
  --key /tmp/dev-key.key \
  --public-key /tmp/dev-key.pem \
  --metadata /tmp/meta.json \
  --scope foundational:aep-response \
  --timestamp test-vectors/valid/valid-overt-profile/package.aep:timestamp.tsr \
  --out /tmp/hello.aep

# 4. Verify what we just signed.
node cli/eatf-verify/bin/eatf-verify.js /tmp/hello.aep
# → verify=true
```

## Options

```
--payload <file>        File to attest.
--key <pem>             RSA private key in PEM (PKCS#8 or PKCS#1).
--public-key <pem>      RSA public key in PEM (embedded as public_key.pem).
--metadata <json>       Attestation metadata JSON.
--scope <urn>           OVERT scope (e.g. foundational:aep-response).
--timestamp <spec>      RFC 3161 TimeStampResp bytes. Either:
                          - /path/to/file.tsr
                          - /path/to/some.aep:timestamp.tsr (extract from inside)
--out <file>            Output path. Default: ./package.aep.
--iap <name>            Issuing-AEP-party name in receipt.witness.iap.
                        Default: "EATF.eu".
--gen-rsa <stem>        Generate <stem>.key + <stem>.pem (DEV key).
--version, -V
--help, -h
```

Exit codes: `0` package written; `1` sign error; `2` bad CLI usage.

## Where do RFC 3161 timestamps come from?

EATF itself does not operate a TSA. Each deployment chooses one. To
mint a fresh timestamp from a public TSA outside this CLI:

```bash
# Hash the canonical bytes (for AEP v0.1, this is just the payload).
sha256sum /tmp/payload.txt | cut -d' ' -f1 > /tmp/digest.hex

# Build an RFC 3161 query.
openssl ts -query -digest "$(cat /tmp/digest.hex)" -sha256 -no_nonce -cert -out /tmp/req.tsq

# Submit to a public TSA (freetsa.org, DigiCert, etc.).
curl -s -H "Content-Type: application/timestamp-query" \
     --data-binary @/tmp/req.tsq \
     https://freetsa.org/tsr > /tmp/resp.tsr

# Pass to eatf-sign.
eatf-sign --timestamp /tmp/resp.tsr ...
```

## What this CLI does NOT do

- **No network calls.** RFC 3161 token must be pre-fetched.
- **No agent registration.** The signer reads metadata from a JSON file
  passed in by the caller; it does not call any registry.
- **No PQC signing yet.** ML-DSA-65 signing lands in a 0.1.x point
  release; the verifier already handles packages that carry it
  (entries `signature_pqc.sig` + `pqc_public_key.pem`).
- **No HSM integration.** v0.1.3 expects a software RSA key in PEM.
  HSM (PKCS#11) signing is on the longer-term roadmap.

## License

Apache License 2.0 — see [`../../LICENSE`](../../LICENSE).

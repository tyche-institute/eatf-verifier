# `eatf-sign`

Offline CLI that creates an AEP from a payload, JSON metadata, an RSA keypair,
an OVERT scope, and a pre-fetched RFC 3161 response.

```bash
eatf-sign \
  --payload payload.txt \
  --key signer.key \
  --public-key signer.pem \
  --metadata metadata.json \
  --scope foundational:aep-response \
  --timestamp response.tsr \
  --out package.aep
```

Add a hybrid ML-DSA-65 signature with a development keypair:

```bash
eatf-sign --gen-mldsa dev-mldsa65
eatf-sign \
  --payload payload.txt \
  --key signer.key --public-key signer.pem \
  --pqc-key dev-mldsa65.key --pqc-public-key dev-mldsa65.pem \
  --metadata metadata.json --scope foundational:aep-response \
  --timestamp response.tsr --out hybrid.aep
eatf-verify --require-pqc hybrid.aep
```

`--timestamp` accepts either a raw `TimeStampResp` file or
`existing.aep:timestamp.tsr`. The signer rejects the token unless:

- it parses as RFC 3161;
- its SHA-256 message imprint matches `canonical.bin`;
- its CMS signature verifies against an embedded TSA signing certificate.

The CLI never contacts a TSA. A producer can request a response out of band:

```bash
digest="$(eatf-sign \
  --payload payload.txt \
  --metadata metadata.json \
  --print-digest)"
openssl ts -query -digest "$digest" -sha256 -no_nonce -cert -out request.tsq
curl -sS -H 'Content-Type: application/timestamp-query' \
  --data-binary @request.tsq https://example.invalid/tsa > response.tsr
```

Replace the illustrative URL with the deployment's selected TSA. The signer
uses software keys; HSM/PKCS#11 integration remains future work. `--gen-rsa`
and `--gen-mldsa` create development keys and must not be used for production
attestations. The ML-DSA public key is RFC 9881 SPKI; the seed PEM is an
explicit toolkit development format, not PKCS #8.

`metadata.json` must include a fixed `created_at` value when
`--print-digest` is used. The later signing pass reads the same metadata and
therefore reconstructs the exact digest covered by the timestamp. Hashing the
payload alone is incorrect because current packages also bind the metadata.

Apache-2.0; see [`../../LICENSE`](../../LICENSE).

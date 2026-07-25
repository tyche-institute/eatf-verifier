# `minimal-roundtrip`

Expected verdict: `verify=true`.

This package is produced by the current `eatf-sign` CLI from the payload and
metadata in `examples/01-minimal-sign-and-verify/`, the public development RSA
keypair, and a matching response from the repository's TEST-ONLY TSA.

Reproduce the complete workflow:

```bash
bash bin/setup.sh
examples/01-minimal-sign-and-verify/run.sh /tmp/eatf-roundtrip
```

The timestamp imprint equals SHA-256(`canonical.bin`) and its CMS signature
verifies against the embedded test-TSA certificate. Both verifiers also accept
the caller-supplied development signer key as an explicit trust pin.
`canonical.bin` uses the current
`response.txt || LF || RFC8785-JCS(metadata)` profile, so metadata is covered
by the hash, RSA signature, and timestamp. The signed metadata requires
`overt_receipt.sig`, which covers the exact OVERT receipt bytes and prevents
unmarked downgrade.

# Example 02 — sign-and-verify with RFC 3161 timestamp

Extends Example 01 with a timestamping step. The signer sends the
manifest-signature hash to a test TSA and embeds the resulting
`TimeStampResp` in the AEP.

```bash
eatf-sign --in records/ --key ../../test-vectors/valid/keys/dev.pem \
          --tsa http://localhost:8765/tsa \
          --out action.aep

eatf-verify action.aep \
            --issuer-anchor ../../test-vectors/valid/anchors/issuer-root.pem \
            --tsa-anchor ../../test-vectors/valid/anchors/tsa-root.pem
# → verify=true; signedAt=2026-05-14T08:42:11Z
```

Stub. Runnable example lands in a 0.1.x point release.

# Example 01 — minimal sign-and-verify

Demonstrates the smallest possible roundtrip: sign an action record
into an AEP, then verify it offline.

```bash
# Sign
eatf-sign --in records/ --key ../../test-vectors/valid/keys/dev.pem \
          --out action.aep

# Verify
eatf-verify action.aep \
            --issuer-anchor ../../test-vectors/valid/anchors/issuer-root.pem
# → verify=true
```

Stub. Runnable example lands in a 0.1.x point release.

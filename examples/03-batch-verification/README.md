# Example 03 — batch verification

Verifying a directory of AEPs in one invocation, suitable for auditor
or research workflows.

```bash
eatf-verify --batch packages/ \
            --issuer-anchor ../../test-vectors/valid/anchors/issuer-root.pem \
            --tsa-anchor ../../test-vectors/valid/anchors/tsa-root.pem \
            --json > report.json
```

Stub. Runnable example lands in a 0.1.x point release.

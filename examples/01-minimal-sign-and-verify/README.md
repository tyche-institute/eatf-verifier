# Example 01: minimal sign, inspect, and dual verification

From the repository root:

```bash
examples/01-minimal-sign-and-verify/run.sh /tmp/eatf-example
```

The script signs `payload.txt` with the public development fixture key, reuses
the matching committed test-TSA response, inspects the result, and verifies it
with both implementations while pinning the expected signer key.

Expected final line:

```text
Round-trip passed with both verifiers: /tmp/eatf-example/minimal-roundtrip.aep
```

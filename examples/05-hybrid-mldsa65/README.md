# Hybrid RSA-4096 + ML-DSA-65 round trip

This example generates a disposable ML-DSA-65 development keypair, uses the
public signer to add both classical and post-quantum signatures to the same
canonical bytes, and verifies the result with the TypeScript and Python
implementations under an explicit `require-pqc` policy.

```bash
./examples/05-hybrid-mldsa65/run.sh
```

The timestamp is reused from the deterministic minimal example because the
payload and signed metadata are identical. No network request is made.

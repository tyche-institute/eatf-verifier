# Hybrid RSA-4096 + ML-DSA-65 round trip

This example generates a disposable ML-DSA-65 development keypair, uses the
public signer to add both classical and post-quantum signatures to the same
canonical bytes, and verifies the result with the TypeScript and Python
implementations under an explicit `require-pqc` policy, with both the RSA and
the ML-DSA-65 signer keys pinned. Without `--pqc-signer-key`, `--require-pqc`
would accept an ML-DSA-65 signature from any key.

```bash
./examples/05-hybrid-mldsa65/run.sh
```

The timestamp is reused from the deterministic minimal example because the
payload and signed metadata are identical. No network request is made.

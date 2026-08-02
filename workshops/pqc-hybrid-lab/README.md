# Break the hybrid signature: an offline ML-DSA-65 lab

This self-contained lab contrasts a transition verifier (`if-present`) with a
policy that requires the post-quantum half (`required`). All packages are
prepared, deterministic, and verified offline by independent TypeScript and
Python implementations.

## Run the complete lab

From the repository root:

```bash
bash bin/setup.sh
./workshops/pqc-hybrid-lab/run.sh
```

There are two distinct downgrade observations:

- `03-pqc-pair-stripped.aep` is rejected even in transition mode because the
  signed OVERT witness still names `signature_pqc.sig`. Removing the PQC pair
  therefore breaks structural binding.
- `04-classical-transition.aep` is a legitimately created classical-only
  package. It passes `if-present` but is rejected with
  `PQC_SIGNATURE_REQUIRED` when the relying party requires PQC. That explicit
  relying-party policy is still necessary during migration.

## Inspect one package

```bash
bin/eatf-inspect workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep
bin/eatf-verify --require-pqc workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep
bin/eatf-verify-py --require-pqc workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep
```

The public key inside `pqc_public_key.pem` is an RFC 9881 ML-DSA-65
SubjectPublicKeyInfo. The test TSA, RSA key, and deterministic ML-DSA seed are
fixtures only. This lab is a research and interoperability artifact, not a
certification or production deployment profile.

Regenerate the packages after changing the signer or verifier:

```bash
npm run build
node scripts/generate-pqc-workshop.mjs
```

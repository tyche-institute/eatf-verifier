# Break the hybrid signature: an offline ML-DSA-65 lab

This self-contained lab contrasts a transition verifier (`if-present`) with a
policy that requires the post-quantum half (`required`). All packages are
prepared, deterministic, and verified offline by independent TypeScript and
Python implementations.

The conference core is designed for 60 minutes, with documented 45- and
90-minute variants. Start with [QUICKSTART.md](QUICKSTART.md), then use
[RUN-SHEETS.md](RUN-SHEETS.md) and the no-network
[EXPECTED-TRANSCRIPT.md](EXPECTED-TRANSCRIPT.md).

## Run the complete lab

From the repository root:

```bash
bash bin/setup.sh
./workshops/pqc-hybrid-lab/run.sh
```

The cross-platform equivalent is:

```bash
python workshops/pqc-hybrid-lab/run_lab.py
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

The adjacent archive-migration worksheet is available in
[`docs/pqc-archive-migration-worksheet.md`](../../docs/pqc-archive-migration-worksheet.md)
and in printable HTML/PDF forms.

Regenerate the packages after changing the signer or verifier:

```bash
npm run build
node scripts/generate-pqc-workshop.mjs
```

Build the deterministic release download, including this lab and the archive
worksheet:

```bash
npm run build:conference-assets
```

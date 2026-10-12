# Break the hybrid signature: an offline ML-DSA-65 lab

This portable prepared-package lab contrasts a transition verifier
(`if-present`) with a policy that requires the post-quantum half (`required`)
and with a relying party that also pins both signer keys (`pinned`). All
packages are deterministic and verified offline by the toolkit's TypeScript
and Python verifiers, both built by Tyche Institute, after the one-time
toolkit setup.

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

The release ZIP includes `run_lab.py` and `run.sh`. After setup, set
`EATF_REPO_ROOT` to the checkout, extract the ZIP, and run `python run_lab.py`
inside the extracted directory. The runner then uses the downloaded packages,
not the repository copies. See [QUICKSTART.md](QUICKSTART.md).

There are two distinct downgrade observations:

- `03-pqc-pair-stripped.aep` is rejected even in transition mode because the
  signed OVERT witness still names `signature_pqc.sig`. Removing the PQC pair
  therefore breaks structural binding.
- `04-classical-transition.aep` is a legitimately created classical-only
  package. It passes `if-present` but is rejected with
  `PQC_SIGNATURE_REQUIRED` when the relying party requires PQC. That explicit
  relying-party policy is still necessary during migration.

One substitution passes both policies:

- `07-foreign-mldsa-key.aep` is `01-valid-hybrid.aep` with only
  `signature_pqc.sig` and `pqc_public_key.pem` replaced by an unrelated
  ML-DSA-65 key's signature over the same `canonical.bin`. Nothing else in the
  package authenticates the ML-DSA key, so both verifiers accept it under
  `if-present` and under `required`, even with the RSA key pinned. Only the
  `pinned` policy (`--require-pqc --signer-key keys/dev-rsa-4096.pem
  --pqc-signer-key keys/dev-mldsa65.pem`) rejects it, with
  `PQC_SIGNER_NOT_TRUSTED`. `--require-pqc` alone proves that an ML-DSA-65 signature exists, not whose
  key made it, and both CLIs print a warning to stderr when it is used without
  `--pqc-signer-key`.

## Inspect one package

```bash
bin/eatf-inspect workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep
bin/eatf-verify --require-pqc workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep
bin/eatf-verify-py --require-pqc workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep
bin/eatf-verify --require-pqc \
  --pqc-signer-key workshops/pqc-hybrid-lab/keys/dev-mldsa65.pem \
  workshops/pqc-hybrid-lab/packages/07-foreign-mldsa-key.aep
```

The public key inside `pqc_public_key.pem` is an RFC 9881 ML-DSA-65
SubjectPublicKeyInfo. `keys/` holds the two public signer keys the `pinned`
policy expects. The test TSA, RSA key, and deterministic ML-DSA seeds are
fixtures only. This lab is a research and interoperability artifact, not a
certification or production deployment profile.

The archive-migration worksheet is available in the repository at
[`docs/pqc-archive-migration-worksheet.md`](../../docs/pqc-archive-migration-worksheet.md)
and in the release ZIP under `archive-migration/` in Markdown, HTML, and PDF.

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

# Annotated expected transcript

Run:

```bash
./workshops/pqc-hybrid-lab/run.sh
```

Expected decision table:

```text
package                              policy         TypeScript  Python  first code
01-valid-hybrid.aep                  transitional   True        True    -
01-valid-hybrid.aep                  required       True        True    -
02-pqc-signature-tampered.aep        transitional   False       False   PQC_SIGNATURE_INVALID
02-pqc-signature-tampered.aep        required       False       False   PQC_SIGNATURE_INVALID
03-pqc-pair-stripped.aep             transitional   False       False   OVERT_INVALID
03-pqc-pair-stripped.aep             required       False       False   OVERT_INVALID
04-classical-transition.aep          transitional   True        True    -
04-classical-transition.aep          required       False       False   PQC_SIGNATURE_REQUIRED
05-pqc-signature-missing.aep         transitional   False       False   OVERT_INVALID
05-pqc-signature-missing.aep         required       False       False   OVERT_INVALID
06-response-tampered.aep             transitional   False       False   CANONICAL_FORM_MISMATCH
06-response-tampered.aep             required       False       False   CANONICAL_FORM_MISMATCH

Cross-language policy mismatches: 0
```

Interpretation:

- A bad ML-DSA signature reaches `PQC_SIGNATURE_INVALID` in both verifiers.
- Removing both PQC entries from the hybrid package is not a successful
  downgrade: the signed witness still names the signature entry, so structural
  validation fails first.
- The legitimate classical transition package is structurally valid. Only the
  explicit relying-party `required` policy rejects it.
- An incomplete hybrid pair and a changed payload fail before a relying party
  could treat the package as valid evidence.

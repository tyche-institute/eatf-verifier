# `eatf-inspect`

`eatf-inspect` prints the flat AEP v1 ZIP layout, entry sizes, parsed metadata,
and an OVERT receipt summary. It does not validate hashes or signatures.

```bash
eatf-inspect test-vectors/valid/mcp-tools-call-valid/package.aep
eatf-inspect --json test-vectors/valid/mcp-tools-call-valid/package.aep
```

The output identifies these wire entries when present:

```text
canonical.bin
hash.sha256
metadata.json
overt_receipt.json
overt_receipt.sig
public_key.pem
response.txt
signature.sig
signature_pqc.sig
pqc_public_key.pem
timestamp.tsr
```

Use `eatf-verify` or `eatf-verify-py` for a verification assertion. Exit
codes are 0 for completed inspection, 1 for an unreadable/malformed ZIP, and 2
for bad CLI usage.

Apache-2.0; see [`../../LICENSE`](../../LICENSE).

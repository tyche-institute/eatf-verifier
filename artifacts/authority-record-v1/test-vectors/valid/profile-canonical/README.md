# `profile-canonical/`

**Expected:** `verify=true`.

An AEP whose `canonical.bin` uses the **profile canonical form** of
`docs/specs/aep-profile-v1.md` §6: `response.txt` + LF +
JCS(`metadata.json`). The signature, the hash, and the RFC 3161
timestamp therefore cover the metadata as well as the response, and the
verifier reports `canonicalForm: "profile"`.

Every other shipped valid vector uses the Java response-only canonical
form (`canonical.bin` equals `response.txt` verbatim); in that form the
whole of `metadata.json` lies outside `signature.sig`, and the verifier
reports `canonicalForm: "response-only"`. This vector is the
conformance evidence for the stronger binding.

Produced by `eatf-sign` (from this repository) with
`canonicalForm: "profile"`, using the dev RSA key at
[`test-vectors/keys/dev-rsa-4096.{key,pem}`](../../keys/). The RFC 3161
timestamp token is reused from `valid-overt-profile/package.aep` rather
than freshly minted (so generation is fully offline); the verifier
accepts mismatched-imprint timestamps with a warning under the "Java
reference compatibility" path.

## Reproducing this vector

```bash
# 1. Build the verifier and signer.
(cd lib && npm install && npm run build)

# 2. Regenerate.
node scripts/generate-profile-canonical-vector.mjs

# 3. Confirm no drift.
git diff --quiet test-vectors/valid/profile-canonical/ && echo byte-identical
```

The regenerated `.aep` is byte-for-byte identical to the committed one
for the same reasons as `minimal-roundtrip/`: deterministic RSA and JCS,
a verbatim-reused timestamp token, a fixed `created_at`, and the
signer's pinned ZIP entry timestamp (`ZIP_ENTRY_MTIME` in
[`lib/src/signer.ts`](../../../lib/src/signer.ts)).

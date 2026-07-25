# `tampered-overt-receipt/`

**Expected:** `verify=false`, diagnostic containing
`overt_receipt.json invalid`.

A well-formed AEP envelope whose embedded OVERT receipt has been
tampered with after signing. Its declared `content_hash` no longer equals the
package's `hash.sha256`, so the receipt no longer points at the signed
canonical record. Exercises the cross-document content-hash check on a legacy
receipt without a separate receipt signature.

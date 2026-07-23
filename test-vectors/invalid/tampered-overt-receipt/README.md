# `tampered-overt-receipt/`

**Expected:** `verify=false`, diagnostic containing
`overt_receipt.json invalid`.

A well-formed AEP envelope whose embedded OVERT receipt has been
tampered with after signing. The hash declared in the manifest no
longer matches the actual `overt_receipt.json` bytes. Exercises the
hash-chain check.

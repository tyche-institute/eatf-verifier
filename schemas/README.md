# schemas/ — JSON Schema definitions

Both schemas use **JSON Schema 2020-12**
(<https://json-schema.org/draft/2020-12/schema>).

| File | Purpose |
|---|---|
| `aep-v1.schema.json` | The `metadata.json` document carried inside an `.aep` package. |
| `overt-receipt-v1.schema.json` | The optional `overt_receipt.json` OVERT-inspired receipt entry. |

The package **container** itself (which ZIP entries are required, and the
verification order) is documented in `../docs/aep-format.md`; the verifier
implementations in `../lib` and `../lib-python` are the executable source of
truth.

## OVERT attribution

OVERT is an open standard published by Glacis Technologies, Inc.
(https://overt.is). This project is independent of Glacis Technologies and
carries no endorsement, certification, or conformance claim from them; the
`overt_receipt.json` entry is OVERT-inspired and defined by this project. See
the repository [README](../README.md#overt-attribution-and-non-endorsement).

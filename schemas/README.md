# schemas/ — JSON Schema definitions

Both schemas use **JSON Schema 2020-12**
(<https://json-schema.org/draft/2020-12/schema>).

| File | Purpose |
|---|---|
| `aep-v1.schema.json` | The `metadata.json` document carried inside an `.aep` package. |
| `overt-receipt-v1.schema.json` | The optional `overt_receipt.json` OVERT receipt entry. |

The package **container** itself (which ZIP entries are required, and the
verification order) is documented in `../docs/aep-format.md`; the verifier
implementations in `../lib` and `../lib-python` are the executable source of
truth.

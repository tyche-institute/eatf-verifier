# schemas/ — JSON Schema definitions

All schemas use **JSON Schema 2020-12**
(<https://json-schema.org/draft/2020-12/schema>).

Planned schemas for v0.1:

| File                  | Purpose                                              |
|-----------------------|------------------------------------------------------|
| `manifest.schema.json`| AEP manifest envelope.                               |
| `record.schema.json`  | Per-action record format.                            |
| `attestation.schema.json` | Agent attestation (W3C VC 2.0 profile).          |

## v0.1.0 status

Stub. Schemas land in successive 0.1.x point releases with
conformance test vectors under `../test-vectors/`.

## Validation

Schemas will be validated against the test vectors as part of CI;
see `../.github/workflows/`.

# cli/ — EATF command-line tools

Three command-line entry points are planned for v0.1.

| Tool           | Purpose                                                                     |
|----------------|-----------------------------------------------------------------------------|
| `eatf-sign`    | Build an AEP from a directory of records, sign it, timestamp it.            |
| `eatf-verify`  | Verify an AEP offline; print a `VerificationReport`; exit 0 on pass.        |
| `eatf-inspect` | Pretty-print the manifest, signatures, attestation, and timestamp of an AEP without verifying.            |

## v0.1.0 status

Stub. The runnable CLIs land in successive 0.1.x point releases.

See each subdirectory's README for the planned invocation surface.

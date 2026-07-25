# Runnable examples

Run `bash bin/setup.sh` from the repository root first.

| Example | Reviewer question answered |
|---|---|
| `01-minimal-sign-and-verify` | Can the toolkit create, inspect, and verify one AEP with both implementations? |
| `02-with-rfc3161-timestamp` | Does the timestamp bind the canonical SHA-256 digest and carry a valid CMS signature? |
| `03-batch-verification` | Do both implementations satisfy all 11 conformance verdicts? |
| `04-tamper-and-reject` | Does a one-byte change cause both implementations to reject the package? |

Each directory contains an executable `run.sh`. The umbrella command
`npm run test:toolkit` runs all four in sequence.

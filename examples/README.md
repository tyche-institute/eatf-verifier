# examples/ — runnable demonstrations

Each subdirectory is self-contained and includes a `README.md`, the
input records, expected output, and a one-line invocation. Examples
use only the keys and trust anchors shipped under
`../test-vectors/`.

| Example                                                      | Demonstrates                                                                          |
|--------------------------------------------------------------|---------------------------------------------------------------------------------------|
| `01-minimal-sign-and-verify/`                                | Smallest possible sign-then-verify roundtrip.                                         |
| `02-with-rfc3161-timestamp/`                                 | Same roundtrip with an RFC 3161 timestamp applied by a test TSA.                      |
| `03-batch-verification/`                                     | Verifying a directory of packages in one invocation.                                  |
| `04-private-ca-setup/`                                       | Setting up a private CA, issuing an issuer cert, configuring the verifier anchor set. |

## v0.1.0 status

Stub. Examples land in successive 0.1.x point releases alongside the
runnable CLI.

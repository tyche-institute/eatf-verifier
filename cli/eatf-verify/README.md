# `eatf-verify`

Offline TypeScript CLI over [`@eatf/verifier`](../../lib).

```bash
eatf-verify [--signer-key expected.pem] action.aep
eatf-verify --batch received-packages/
eatf-verify --conformance test-vectors/
eatf-verify --json action.aep
eatf-verify --require-pqc hybrid.aep
```

Important options:

- `--signer-key PEM` requires the embedded SPKI public key to match one of
  the caller-supplied keys. Repeat it for key rotation.
- `--tsa-trust-list PEM` performs only the documented advisory issuer-name
  pin. It is not RFC 5280 path validation.
- `--require-pqc` rejects packages without a complete, valid ML-DSA-65 pair.
  Without it, classical-only transition packages remain acceptable.
- `--conformance` expects packages under `valid/` to pass and packages under
  `invalid/` to fail.

Exit status is 0 when all requested assertions hold, 1 when a package fails,
and 2 for usage or input errors. The CLI makes no network calls.

Without `--signer-key`, verification establishes package consistency and a
valid signature under the embedded key; it does not identify the owner of that
key.

Apache-2.0; see [`../../LICENSE`](../../LICENSE).

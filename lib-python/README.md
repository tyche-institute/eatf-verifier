# `eatf-verifier` for Python

Python 3.11+ implementation of the EATF AEP verification contract. It uses the
same wire format and shared conformance vectors as the TypeScript library, with
language-native ZIP, ASN.1, X.509, and cryptographic libraries. Its maintained
RFC 8785 implementation is checked against the TypeScript port on numeric and
Unicode ordering boundaries.

```python
from eatf_verifier import VerifyOptions, verify

result = verify(
    open("action.aep", "rb").read(),
    VerifyOptions(
        trusted_signer_pems=[open("expected.pem", "rb").read()],
        trusted_pqc_signer_pems=[open("expected-mldsa65.pem", "rb").read()],
        pqc_policy="required",
    ),
)
print(result.valid, result.failure_reason)
```

CLI:

```bash
eatf-verify-py --signer-key expected.pem action.aep
eatf-verify-py --conformance test-vectors/
eatf-verify-py --json action.aep
eatf-verify-py --require-pqc hybrid.aep
eatf-verify-py --require-pqc --signer-key expected.pem \
  --pqc-signer-key expected-mldsa65.pem hybrid.aep
```

`--signer-key` / `trusted_signer_pems` pins only the RSA key.
`--pqc-signer-key` / `trusted_pqc_signer_pems` pins the ML-DSA-65 key, compared
on the decoded FIPS 204 key, and implies `--require-pqc`. Without it,
`--require-pqc` does not establish whose ML-DSA-65 key signed, and the CLI
prints a warning to stderr.

Base installation verifies RSA and ML-DSA-65 packages. It uses
`cryptography>=49` for FIPS 204 verification and RFC 9881 SPKI parsing; no
separate liboqs installation is required.

The PyPI project is not published yet. Install the versioned v0.6.1 source
directly from GitHub instead:

```bash
python -m pip install "eatf-verifier @ https://github.com/tyche-institute/eatf-verifier/archive/refs/tags/v0.6.1.zip#subdirectory=lib-python"
```

From an existing repository checkout, use `python -m pip install ./lib-python`.

Security boundaries match the TypeScript implementation:

- no network calls;
- no signer identity assertion unless trusted signer PEMs are supplied;
- strict RFC 3161 imprint and embedded CMS signature checks;
- optional TSA issuer-name pin, but no full RFC 5280 chain construction,
  revocation processing, or qualified-trust determination.

```bash
python -m pytest tests
python -m eatf_verifier.cli --conformance ../test-vectors
```

Apache-2.0; see [`../LICENSE`](../LICENSE).

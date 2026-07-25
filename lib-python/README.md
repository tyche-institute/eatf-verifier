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
    VerifyOptions(trusted_signer_pems=[open("expected.pem", "rb").read()]),
)
print(result.valid, result.failure_reason)
```

CLI:

```bash
eatf-verify-py --signer-key expected.pem action.aep
eatf-verify-py --conformance test-vectors/
eatf-verify-py --json action.aep
```

Base installation verifies RSA packages. The `[pqc]` extra installs the
official `liboqs-python` bindings for ML-DSA-65; the liboqs shared library must
also be available.

```bash
pip install eatf-verifier
pip install 'eatf-verifier[pqc]'
```

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

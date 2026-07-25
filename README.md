# EATF Agent Evidence Package toolkit

EATF is an open toolkit for creating, inspecting, and independently verifying
Agent Evidence Packages (`.aep`). An AEP is a portable ZIP envelope that binds
an AI-agent action record to canonical bytes, hashes, signatures, an optional
OVERT receipt, and an RFC 3161 timestamp.

The tools run locally after installation. They make no runtime network calls,
need no account or API key, and do not depend on a hosted EATF service.

## Statement of need

Agent-action records often cross organizational boundaries: the producer,
auditor, deployer, and researcher may be different parties. A producer-hosted
dashboard cannot by itself let those parties check a record after export or
after the producer is unavailable. This repository supplies a documented
package format, a signer, an inspector, two verifier implementations, schemas,
positive and negative conformance vectors, and runnable examples.

Related standards provide complementary building blocks. RATS/EAT and COSE
address attestation claims and protected messages; DSSE, in-toto, and Sigstore
address software-supply-chain provenance; RO-Crate and PROV address research
object description and provenance. EATF's narrower purpose is a runnable,
offline package and verification workflow for one recorded agent action.

## Toolkit contents

| Path | Component |
|---|---|
| `lib/` | TypeScript verifier and reference signer (`@eatf/verifier`) |
| `lib-python/` | Python verifier (`eatf-verifier`) |
| `cli/eatf-sign/` | Offline AEP signer |
| `cli/eatf-inspect/` | Non-validating package inspector |
| `cli/eatf-verify/` | TypeScript verification CLI |
| `schemas/` | JSON Schemas for AEP metadata and OVERT receipts |
| `test-vectors/` | 4 accepted and 7 rejected conformance packages |
| `examples/` | Four executable reviewer journeys |
| `experiments/decision-path/` | Model-based differential oracle, generated corpus, and results |
| `docs/aep-format.md` | Implemented wire-format and verification contract |

This is the public AEP toolkit, not the larger EATF service or governance
platform. It does not include tenants, hosted APIs, dashboards, policy
administration, or identity registries.

## Install from source

Prerequisites are Node.js 20+ and Python 3.11+.

```bash
git clone https://github.com/tyche-institute/eatf-verifier.git
cd eatf-verifier
bash bin/setup.sh
export PATH="$PWD/bin:$PATH"
```

The setup script installs pinned Node dependencies, creates `.venv`, installs
the Python package with its test tools, builds TypeScript, and checks all five
command entry points.

Run the complete reviewer workflow:

```bash
npm run test:toolkit
```

It signs a package, inspects it, verifies it with TypeScript and Python,
validates its RFC 3161 token, runs both conformance suites, tampers with a copy,
and confirms that both verifiers reject the tampered package.

## Minimal workflow

```bash
examples/01-minimal-sign-and-verify/run.sh /tmp/eatf-example

eatf-inspect /tmp/eatf-example/minimal-roundtrip.aep
eatf-verify \
  --signer-key test-vectors/keys/dev-rsa-4096.pem \
  /tmp/eatf-example/minimal-roundtrip.aep
eatf-verify-py \
  --signer-key test-vectors/keys/dev-rsa-4096.pem \
  /tmp/eatf-example/minimal-roundtrip.aep
```

The committed keys and TSA certificate are public test fixtures. Never use
them for production evidence.

## Verification contract

Both verifiers apply the same decisive checks:

1. required ZIP entries and JSON parsing;
2. the profile canonical form, or explicitly reported legacy compatibility;
3. SHA-256 binding of `canonical.bin`;
4. optional exact signer-key pin, when supplied by the caller;
5. RSA-4096 PKCS#1 v1.5/SHA-256 signature;
6. OVERT receipt cross-checks and, for current signer output, its
   downgrade-protected separate RSA signature;
7. ML-DSA-65 signature, when its key/signature pair is present;
8. RFC 3161 parsing, SHA-256 message-imprint equality, and CMS signature
   verification against the embedded TSA signing certificate.

Without `--signer-key`, a successful result proves package consistency and
control of the embedded private key, but does not establish who owns that key.
The current TSA trust-list option is an advisory issuer-name pin, not full RFC
5280 path validation. These boundaries are reported rather than hidden.

## Quality controls

```bash
npm test
.venv/bin/python -m pytest lib-python/tests
eatf-verify --conformance test-vectors
eatf-verify-py --conformance test-vectors
```

The shared set contains four positive vectors and seven single-fault negative
controls. Tests also cover matching and non-matching signer-key pins, receipt
signature downgrade, RFC 8785 boundaries, and validation of every positive
vector against both Draft 2020-12 schemas. CI runs the same build, unit,
conformance, packaging, and end-to-end workflow on Linux, macOS, and Windows
where the operating-system step is portable.

Run the v0.3.0 decision-path experiment:

```bash
python experiments/decision-path/run_experiment.py
```

Its fixed oracle generates 21 deterministic cases spanning two accepting
controls and 16 rejection states, then compares both implementations with the
oracle and with one another at the level of verdict plus first-failure code.
The preserved confirmatory result is 21/21 oracle matches, 21/21
cross-language matches, and zero boolean or first-code mismatches.

## Scope and limitations

- The signer currently emits RSA-signed packages; both verifiers can also
  verify ML-DSA-65 entries.
- The current signer binds `response.txt` and `metadata.json` using the
  profile canonical form. Verifiers retain read-only support for legacy
  response-only packages and warn that their metadata is not signature-bound.
- Metadata canonicalization uses maintained RFC 8785 libraries in both
  implementations and a shared I-JSON domain that rejects unsafe
  integer-valued numbers and unpaired Unicode surrogates.
- Full RFC 5280 TSA chain construction, revocation checking, HSM integration,
  and automatic trust-registry discovery are outside version 0.3.0.
- EATF is not a trust service, certificate authority, legal-compliance
  determination, or substitute for an auditor's policy.

## License and citation

Apache License 2.0; see [LICENSE](LICENSE).

Citation metadata is in [CITATION.cff](CITATION.cff). The archived v0.1.2
release remains available at
[doi:10.5281/zenodo.21511609](https://doi.org/10.5281/zenodo.21511609).
The reviewed v0.2.0 source snapshot is archived at
[doi:10.5281/zenodo.21571908](https://doi.org/10.5281/zenodo.21571908);
v0.3.0 adds the decision-path research bundle. The all-versions concept DOI is
[doi:10.5281/zenodo.21511608](https://doi.org/10.5281/zenodo.21511608).

## Contributing and support

Ordinary bugs and feature requests belong in the
[public issue tracker](https://github.com/tyche-institute/eatf-verifier/issues).
See [CONTRIBUTING.md](CONTRIBUTING.md) for the local checks and format-change
contract, [GOVERNANCE.md](GOVERNANCE.md) for maintenance and release
decisions, and [SECURITY.md](SECURITY.md) for private vulnerability reports.

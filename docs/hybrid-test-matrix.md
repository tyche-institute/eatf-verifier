# Seven tests for a hybrid signature format

A hybrid signature format carries a classical signature and a post-quantum
(PQC) signature over the same bytes. Such a format can pass its own unit tests
and still accept input that a relying party must reject. This page lists seven
tests to run before you call a hybrid format verified. Each row names the
vector or test that runs it in this repository, with the command and the
expected output. Replay the rows here, then write the same seven rows for your
own format.

The page accompanies the talk *PQC-ready is not PQC-verified* at the PKI
Consortium Post-Quantum Cryptography Conference, Amsterdam, 1–3 December 2026.

## The matrix

| # | Test | Expected result | What it catches | Where it runs here |
|---|---|---|---|---|
| 1 | Verify a valid hybrid object with a second implementation that uses another signature library | Both accept | A signer and a verifier that agree only with each other | `test-vectors/valid/hybrid-mldsa65` |
| 2 | Corrupt one signature, each half in turn | Reject; the failure names the corrupted half | A half that is never checked | `test-vectors/invalid/bad-signature-pqc`, `test-vectors/invalid/bad-signature-classical` |
| 3 | Offer a PQC key with another object identifier, with explicit NULL parameters, or with a wrong length | Reject every one | A key wrapper that accepts any bytes | `lib/test/mldsa-key-encoding.test.ts`, `lib-python/tests/test_mldsa_key_encoding.py` |
| 4 | Remove the PQC half from a hybrid object | Reject under every policy | Silent downgrade | `workshops/pqc-hybrid-lab/packages/03-pqc-pair-stripped.aep` |
| 5 | Offer a legitimate classical-only object to a policy that requires PQC | Reject under that policy | Classical-only evidence accepted with no end date | `workshops/pqc-hybrid-lab/packages/04-classical-transition.aep` |
| 6 | Replace the PQC key and signature with those of a foreign key, while the classical signer is pinned | Reject once the PQC key is pinned too | A PQC key that nothing authenticates | `workshops/pqc-hybrid-lab/packages/07-foreign-mldsa-key.aep` |
| 7 | Make the test suite check how many cases it ran | Fail on zero cases; assert the exact count | A green run that checked nothing | `--conformance` in both command-line tools |

Rows 6 and 7 come from failures of this toolkit. Through v0.6.1 both verifiers
accepted the row 6 substitution under `--require-pqc`, with the RSA key pinned.
Through v0.6.1 the Python conformance run on native Windows printed
`0 verified, 0 rejected, 0 contract mismatches` and exited 0. Release v0.7.0
fixed both; [`CHANGELOG.md`](../CHANGELOG.md) has the details.

## Run the rows here

Set up once, with network access. Everything after that runs offline.

```bash
git clone https://github.com/tyche-institute/eatf-verifier.git
cd eatf-verifier
bash bin/setup.sh
export PATH="$PWD/bin:$PATH"
```

The commands below use `eatf-verify`, the TypeScript verifier. `eatf-verify-py`,
the Python verifier, takes the same arguments and gives the same verdict, exit
code and first failure code in every row. Add `--json` to read the first
failure code (`failureCode` in TypeScript output, `failure_code` in Python
output).

### Row 1: a second implementation

```bash
eatf-verify --require-pqc test-vectors/valid/hybrid-mldsa65/package.aep
eatf-verify-py --require-pqc test-vectors/valid/hybrid-mldsa65/package.aep
```

Each prints `verify=true` and a true `pqc` line, and exits 0. The TypeScript
verifier checks ML-DSA-65 with `@noble/post-quantum`, the Python verifier with
`cryptography`. Each command also warns on stderr that `--require-pqc` without
`--pqc-signer-key` does not say whose key signed. Row 6 is about that warning.

### Row 2: one corrupted signature per half

```bash
eatf-verify test-vectors/invalid/bad-signature-pqc/package.aep
eatf-verify test-vectors/invalid/bad-signature-classical/package.aep
```

Both print `verify=false` and exit 1. The first reports
`ML-DSA-65 signature does not verify.` (`PQC_SIGNATURE_INVALID`), the second
`RSA signature does not verify against public_key.pem.`
(`RSA_SIGNATURE_INVALID`). The PQC control changes one bit of
`signature_pqc.sig` in a hybrid package. The classical control changes one
byte of `signature.sig` in an RSA-only package.

### Row 3: key encoding

```bash
(cd lib && npx vitest run test/mldsa-key-encoding.test.ts)
.venv/bin/python -m pytest lib-python/tests/test_mldsa_key_encoding.py
```

13 tests pass in each language. Both files hold the same table. One key is
accepted: an RFC 9881 SubjectPublicKeyInfo with the `id-ml-dsa-65` object
identifier (2.16.840.1.101.3.4.3.18), absent parameters and a 1952-byte key,
1974 bytes in all. Five keys are rejected: the object identifiers of ML-DSA-44
and ML-DSA-87, explicit NULL parameters, a key one byte short and a key one
byte long. Each of the 6 keys is tried twice: through the key parser, and
inside an otherwise valid hybrid package, where both verifiers return
`PQC_VERIFY_ERROR` for the five.

### Row 4: strip the PQC half

```bash
eatf-verify workshops/pqc-hybrid-lab/packages/03-pqc-pair-stripped.aep
```

Prints `verify=false` with
`overt_receipt.json invalid: witness.signature_refs references missing file signature_pqc.sig.`
(`OVERT_INVALID`) and exits 1. The command sets no PQC policy. The package is
rejected all the same, because the signed receipt names `signature_pqc.sig`.

### Row 5: the cut-over rule

```bash
eatf-verify workshops/pqc-hybrid-lab/packages/04-classical-transition.aep
eatf-verify --require-pqc workshops/pqc-hybrid-lab/packages/04-classical-transition.aep
```

The first prints `verify=true` and exits 0. The second prints `verify=false`
with `Verification policy requires a complete ML-DSA-65 signature pair.`
(`PQC_SIGNATURE_REQUIRED`) and exits 1. The package is valid classical
evidence, so nothing inside it can refuse it. Only the relying party's policy
can.

### Row 6: a foreign PQC key

```bash
eatf-verify --require-pqc \
  --signer-key workshops/pqc-hybrid-lab/keys/dev-rsa-4096.pem \
  workshops/pqc-hybrid-lab/packages/07-foreign-mldsa-key.aep
eatf-verify --require-pqc \
  --signer-key workshops/pqc-hybrid-lab/keys/dev-rsa-4096.pem \
  --pqc-signer-key workshops/pqc-hybrid-lab/keys/dev-mldsa65.pem \
  workshops/pqc-hybrid-lab/packages/07-foreign-mldsa-key.aep
```

The first prints `verify=true` and `pqc=true` and exits 0: the RSA signer is
pinned, PQC is required, and an unrelated ML-DSA-65 key passes. The second
prints `verify=false` with
`ML-DSA-65 signer public key is not in the caller-supplied trust set.`
(`PQC_SIGNER_NOT_TRUSTED`) and exits 1.

### Row 7: the suite counts its cases

```bash
eatf-verify --conformance test-vectors
eatf-verify --conformance test-vectors/valid; echo "exit $?"
```

The first ends with
`Conformance: 5 verified, 8 rejected, 0 contract mismatches.` and exits 0.
The second is pointed at a directory with no `valid/` or `invalid/` below it.
It prints
`eatf-verify: --conformance found no .aep vectors under valid/ or invalid/ in test-vectors/valid`
and `exit 2`. Continuous integration compares the summary line on Linux, macOS
and Windows, not only the exit code.

### Rows 4 to 6 in one table

```bash
python3 workshops/pqc-hybrid-lab/run_lab.py
```

The runner replays 7 packages under 3 policies with both verifiers: 21 lines,
42 observations. It ends with `Cross-language policy mismatches: 0`.
[`EXPECTED-TRANSCRIPT.md`](../workshops/pqc-hybrid-lab/EXPECTED-TRANSCRIPT.md)
holds the full table.

## Write the rows for your format

1. Sign one object with your signer. Verify it with an implementation that
   shares no signature library with the signer. Keep that positive vector in
   continuous integration for both implementations.
2. Take the valid hybrid object and change one bit of the PQC signature.
   Expect a reject that names the PQC signature. Restore it, then change one
   bit of the classical signature and expect a reject that names the
   classical one. Leave the other half intact each time.
3. Re-encode the PQC public key three ways: under another algorithm's object
   identifier, with explicit NULL parameters where the standard requires them
   absent, and with a key one byte short and one byte long. Keep every
   encoded length consistent with its content. Expect a reject each time.
4. Delete the PQC signature and key from a valid hybrid object and change
   nothing else. Expect a reject even when no policy asks for PQC. If the
   result is accepted, the PQC half can be removed without a trace.
5. Create a classical-only object the way a legitimate signer would. Expect an
   accept under the transition policy and a reject under the policy that
   requires PQC. Write down the date on which the relying party switches.
6. Sign the same bytes with a PQC key the relying party has never seen. Put
   that key and signature in place of the originals. Pin the classical signer
   and require PQC. Expect a reject. If the object is accepted, nothing
   authenticates your PQC key.
7. Print the number of cases the suite ran. Fail when it is zero. Compare the
   number with the expected count on every platform you test.

Record the verdict and the first failure code of each implementation. Two
verifiers that both reject can still disagree on the reason.

| # | Your vector | Implementation A | Implementation B | First failure code |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |

## Limits

- Tyche Institute wrote both verifiers. They use different ML-DSA libraries,
  so row 1 here compares two libraries, not two authors. The v0.7.4 entry in
  [`CHANGELOG.md`](../CHANGELOG.md) records what a verifier written outside
  Tyche Institute found.
- Seven rows are a minimum. They do not cover malformed entries or parser
  differences; releases v0.7.1, v0.7.2 and v0.7.4 fixed such cases, and their
  tests are in `lib/test/` and `lib-python/tests/`.
- The rows were written for one design: two separate signatures over the same
  bytes, each with its own key. A composite signature has one key and one
  signature value. We have not tested one.
- The vectors for rows 1, 2, 4 and 5 have been in the repository since
  v0.6.0, package 07 and the zero-case exit code since v0.7.0. The row 3
  table was added after v0.7.4.
- The keys and the time-stamping authority in this repository are public test
  fixtures. The [README](../README.md#scope-and-limitations) states what the
  verifiers do not check.

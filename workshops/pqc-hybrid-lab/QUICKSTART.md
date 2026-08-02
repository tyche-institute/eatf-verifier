# Offline quick start

The required conference path uses prepared packages and makes no runtime
network calls. Complete setup before the session if possible.

## Setup

```bash
git clone https://github.com/tyche-institute/eatf-verifier.git
cd eatf-verifier
bash bin/setup.sh
```

## Verify the bundle before the lab

```bash
cd workshops/pqc-hybrid-lab
sha256sum --check SHA256SUMS
cd ../..
python workshops/pqc-hybrid-lab/run_lab.py
```

On macOS, use `shasum -a 256 -c SHA256SUMS` if `sha256sum` is unavailable.
Windows participants can skip the shell checksum command and compare the
published hashes in `SHA256SUMS`, then run the Python command from the
repository root.

The final line must be:

```text
Cross-language policy mismatches: 0
```

## Minimum manual replay

```bash
bin/eatf-inspect workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep
bin/eatf-verify --require-pqc workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep
bin/eatf-verify-py --require-pqc workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep
```

Then compare the legitimate transition package under both policies:

```bash
bin/eatf-verify workshops/pqc-hybrid-lab/packages/04-classical-transition.aep
bin/eatf-verify --require-pqc workshops/pqc-hybrid-lab/packages/04-classical-transition.aep
```

The first command accepts the package. The second rejects it with
`PQC_SIGNATURE_REQUIRED`.

The keys and timestamp material in this repository are public test fixtures.
Never use them for production evidence.

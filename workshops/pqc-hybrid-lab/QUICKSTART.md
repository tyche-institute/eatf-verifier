# Offline quick start

The required conference path uses prepared packages and makes no runtime
network calls. Complete setup before the session if possible.

## Setup once before the session

```bash
git clone https://github.com/tyche-institute/eatf-verifier.git
cd eatf-verifier
bash bin/setup.sh
export EATF_REPO_ROOT="$PWD"
export PATH="$EATF_REPO_ROOT/bin:$PATH"
```

Setup can require a network connection. Package replay does not. On Windows
PowerShell, set `$env:EATF_REPO_ROOT` to the absolute checkout path; the
portable runner uses it to locate both verifiers.

## Verify and run the downloaded bundle

From the extracted `eatf-pqc-hybrid-lab` download:

```bash
sha256sum --check SHA256SUMS
python3 run_lab.py
```

On macOS, use `shasum -a 256 -c SHA256SUMS` if `sha256sum` is unavailable.
Windows participants can skip the shell checksum command and compare the
published hashes in `SHA256SUMS`, then run `python run_lab.py` from the
extracted download after setting `EATF_REPO_ROOT`.

The same runner remains available inside a repository checkout:

```bash
cd "$EATF_REPO_ROOT/workshops/pqc-hybrid-lab"
python3 run_lab.py
```

The final line must be:

```text
Cross-language policy mismatches: 0
```

## Minimum manual replay

```bash
eatf-inspect packages/01-valid-hybrid.aep
eatf-verify --require-pqc packages/01-valid-hybrid.aep
eatf-verify-py --require-pqc packages/01-valid-hybrid.aep
```

Then compare the legitimate transition package under both policies:

```bash
eatf-verify packages/04-classical-transition.aep
eatf-verify --require-pqc packages/04-classical-transition.aep
```

The first command accepts the package. The second rejects it with
`PQC_SIGNATURE_REQUIRED`.

The keys and timestamp material in this repository are public test fixtures.
Never use them for production evidence.

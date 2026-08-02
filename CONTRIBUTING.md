# Contributing

Issues, documentation corrections, new conformance vectors, and focused pull
requests are welcome. Please use the public issue tracker for ordinary bugs and
feature proposals. Report vulnerabilities privately as described in
[`SECURITY.md`](SECURITY.md).

## Development setup

Prerequisites are Node.js 20.19+, Python 3.11+, and OpenSSL for the timestamp
demonstration.

```bash
git clone https://github.com/tyche-institute/eatf-verifier.git
cd eatf-verifier
bash bin/setup.sh
export PATH="$PWD/bin:$PATH"
npm run test:toolkit
```

Before opening a pull request, run:

```bash
npm run build
npm test
.venv/bin/python -m ruff check lib-python
.venv/bin/python -m pytest lib-python/tests
eatf-verify --conformance test-vectors
eatf-verify-py --conformance test-vectors
```

## Compatibility changes

Changes to the AEP wire contract need coordinated updates to:

1. the TypeScript and Python implementations;
2. `docs/aep-format.md` and the affected JSON Schema;
3. a positive or single-fault negative shared vector;
4. both conformance runs and the end-to-end example; and
5. `CHANGELOG.md`.

The boolean conformance verdict is the cross-language contract. Diagnostic
wording may differ. New writers should emit only the current profile form;
legacy support is read-only and must not be expanded silently.

## Review expectations

Keep pull requests narrow, explain the user-visible behavior, and include a
test that would fail without the change. Maintainers may request design
discussion before accepting a new cryptographic primitive or wire-format
extension. By contributing, you agree that your contribution is licensed
under Apache-2.0.

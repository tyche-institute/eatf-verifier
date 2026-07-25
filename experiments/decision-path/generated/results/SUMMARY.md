# Decision-path experiment result

- Cases: 21
- Distinct expected rejection states: 16
- Oracle matches in both implementations: 21/21
- TypeScript/Python verdict-and-code agreement: 21/21
- Boolean mismatches: 0
- First-failure-code mismatches: 0

The oracle was fixed in `oracle.json` before verifier execution. Each case
changes one predeclared condition or invocation parameter. The corpus is not
the repository's 4+7 conformance suite and does not vary transport roots.

# Decision-path differential experiment

This experiment evaluates the first decisive state of the offline AEP
verification procedure. It is the research artifact for the SN Computer
Science paper, not an extension of the repository's 4-valid/7-invalid
conformance suite.

`oracle.json` fixes the mutation operator, expected verdict, and expected
machine-readable first-failure code before either implementation is run.
`generate_corpus.py` applies those operators to the v0.2.0
`minimal-roundtrip` fixture. `run_experiment.py` then executes the independent
TypeScript and Python implementations and compares:

1. each implementation with the predeclared oracle; and
2. the implementations with one another.

Run from the repository root:

```bash
python experiments/decision-path/run_experiment.py
```

Generated packages and results are written below `generated/`. The experiment
does not contact a network. The test-only keys and timestamp certificate are
the repository fixtures documented under `test-vectors/keys/`. Generated ZIP
members use a fixed 1980 timestamp and permissions so repeated runs produce
byte-identical corpus packages.

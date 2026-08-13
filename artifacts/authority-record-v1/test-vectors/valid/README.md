# test-vectors/valid/

Packages that MUST verify cleanly under any v0.1-conformant verifier.

Each vector is a self-contained subdirectory:

```
<vector-name>/
├── package.aep
├── verify-expected.txt     # verify=true
└── README.md
```

See [`../README.md`](../README.md) for the conformance contract and
[`../../cli/eatf-verify/README.md`](../../cli/eatf-verify/README.md)
for how to run the reference verifier.

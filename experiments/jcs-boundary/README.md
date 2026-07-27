# JCS boundary experiment — the method applied to third-party code

The decision-path experiment in `../decision-path/` tests two implementations
written by this project's author. This experiment applies the same discipline
to two RFC 8785 implementations that the project **depends on but did not
write**:

| id | package | version | author |
|---|---|---|---|
| `js` | `canonicalize` (npm) | 3.0.0 | Samuel Erdtman, a co-author of RFC 8785 |
| `py` | `rfc8785` (PyPI) | 0.1.4 | Trail of Bits |

## What is declared before execution

`oracle.json` assigns every case one of three classes, each with the clause of
RFC 8785 that justifies it:

- **`permitted`** — the input satisfies the §3.1 input duty and no clause
  obliges an implementation to reject it;
- **`must_terminate`** — a clause imposes an implementation-level MUST to
  terminate with an error (§3.2.2.2 lone surrogates, §3.2.2.3 NaN/Infinity);
- **`undefined`** — the input violates the §3.1 duty, but no clause states what
  an implementation should then do.

Only the first two classes are scored. The third cannot be: there is no
obligation to conform to.

## Prior art, credited not claimed

That inputs outside the IEEE 754 double domain "produce undefined results", and
that implementations "[do not] deal with such numbers in a uniform way due to
dependencies on number parsing performed by the platform itself", was stated by
the specification's principal author in
[cyberphone/json-canonicalization#3](https://github.com/cyberphone/json-canonicalization/issues/3)
(2018) and reiterated in
[#20](https://github.com/cyberphone/json-canonicalization/issues/20) (2021).
The two `undefined` cases here reproduce that documented behaviour; they are
included as controls, not as findings.

## Run it

```sh
python experiments/jcs-boundary/run_experiment.py
```

Offline after dependency installation. Deterministic: two consecutive runs
produce a byte-identical `generated/SHA256SUMS`.

## What the run reports

Outcome class per implementation per case, whether the two agree on the exact
canonical bytes, and — for JavaScript only — whether the host `JSON.parse`
changed the numeric value before the canonicalizer was reached. That last
column matters: where the value changes, the canonicalization library is
faithfully canonicalizing a value the language already altered, and blaming the
library would be wrong.

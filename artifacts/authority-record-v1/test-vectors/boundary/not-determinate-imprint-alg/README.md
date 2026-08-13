# `not-determinate-imprint-alg/`

**Expected:** `verify=true`, imprint check indeterminate.

`../valid/minimal-roundtrip` with the `messageImprint` hash-algorithm
OID inside the TSTInfo flipped from SHA-256
(`2.16.840.1.101.3.4.2.1`) to SHA-512 (`...2.3`). The verifier only
knows how to recompute a SHA-256 imprint, so it can neither confirm nor
refute the imprint: `tsa-imprint` is `not_determinate` with reason
`capability_absent`. `tsa-present` still passes (the token parses), and
the package verifies.

This distinguishes `not_determinate` (the check ran but hit the edge of
the verifier's capability) from `not_assessed` (the check never ran).
The shipped tokens carry no embedded certificate, so no SignerInfo
signature constrains this edit — the memo's planned cert-stripping
`not-determinate-tsa-cert` vector is redundant here (every shipped token
already lacks a cert, pinned by `advisory-fail-imprint`), so this vector
pins the *other* `not_determinate` path instead.

Produced by `scripts/generate-boundary-vectors.mjs`.

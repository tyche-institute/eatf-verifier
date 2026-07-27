# Pre-registered reading of RFC 8785, recorded before the upstream reports

This file fixes how we read two clauses of RFC 8785 **before** either
observation was reported to the maintainers of the packages concerned. It
exists so that our interpretation cannot be adjusted after a maintainer
replies. Nothing here is a vulnerability claim.

**Recorded:** 27 July 2026, before any issue was filed.

## Clause 1 — lone surrogates

RFC 8785 §3.2.2.2 carries an implementation-level obligation:

> Note: Since invalid Unicode data like "lone surrogates" (e.g., U+DEAD) may
> lead to interoperability issues including broken signatures, occurrences of
> such data MUST cause a compliant JCS implementation to terminate with an
> appropriate error.

**Our reading.** The obligation is addressed to the implementation, not to the
data producer, and the required behaviour is to terminate with an error rather
than to emit any output. RFC 7493 §2.1 supports this by forbidding unpaired
surrogates in member names and string values, giving `"\uDEAD"` as its own
example of an invalid one.

**What we therefore expect of a conforming implementation:** given a JSON value
containing an unpaired surrogate, it terminates with an error.

**What we observed** (`canonicalize` 3.0.0, npm): for `{"a":"\ud800"}` and
`{"a":"\udead"}` the package returns canonical output rather than terminating.
Verified directly: the string is built in memory, `String.prototype.isWellFormed()`
returns `false` on it, and the package still returns a value.

**What we do NOT claim.** We do not claim the input is reachable through the
package's own documented text-in path in every deployment; we do not claim a
security impact; and we note that the mechanism is `JSON.stringify`, which
since ES2019 escapes lone surrogates rather than throwing, so the behaviour is
inherited rather than hand-written.

## Clause 2 — the numeric domain

RFC 8785 §3.1 places the duty on the data:

> JSON number data MUST be expressible as IEEE 754 [IEEE754] double-precision
> values.

Appendix B, Note 1, separately gives an interoperability range:

> For maximum compliance with the ECMAScript "JSON" object, values that are to
> be interpreted as true integers SHOULD be in the range -9007199254740991 to
> 9007199254740991.

**Our reading.** These are two different bounds. §3.1 is a MUST on
representability; Appendix B Note 1 is a SHOULD on the safe-integer range for
maximum ECMAScript compliance. A value that is exactly representable as an
IEEE 754 double satisfies §3.1 even when it lies outside the safe-integer
range. 2^54 = 18014398509481984 is exactly representable — verified:
`float(2**54) == 2**54` — and therefore satisfies §3.1 while lying outside
Appendix B Note 1's range.

**What we therefore expect:** an implementation may reject such a value as a
deliberate policy stricter than the RFC, but rejecting it is not required by
§3.1, and describing the bound as exact-representability would be inaccurate.

**What we observed** (`rfc8785` 0.1.4, PyPI): 2^54 raises `IntegerDomainError`
with the message "exceeds safe integer domain for JSON floats", while the
package's own docstring describes the bound as "the true integer precision of
an IEEE 754 double-precision float". Those two descriptions differ, and the
implemented bound is the safe-integer one.

**What we do NOT claim.** We do not claim the choice is wrong. Rejecting
outside the interoperability range is a defensible and arguably safer policy.
The observation is that the bound implemented is the Appendix B range while the
docstring names representability.

## Standing caveat

The non-uniform handling of numbers outside the double-precision domain is
documented by the specification's principal author in
cyberphone/json-canonicalization issues 3 (2018) and 20 (2021). We cite that
prior art rather than claiming it. Neither observation above concerns that
documented class: one is an explicit implementation-level MUST, the other is
the difference between two stated bounds.

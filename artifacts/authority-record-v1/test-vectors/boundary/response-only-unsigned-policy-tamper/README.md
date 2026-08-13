# `response-only-unsigned-policy-tamper/`

**Expected:** `verify=true` — and that is the point.

Starts from `../valid/mcp-tools-call-denied-policy` (a genuine
`policy_decision: "deny"` package) and flips the decision `deny`→`allow`
in **both** `metadata.json` and `overt_receipt.json` after signing.

Because these packages use the response-only canonical form
(`canonical.bin == response.txt`), `metadata.json` lies entirely
outside `signature.sig`, `hash.sha256`, and the RFC 3161 imprint. The
OVERT-inspired receipt cross-check only compares the two files *to each other*,
so flipping both consistently defeats it. The package therefore still
verifies clean — a `deny` decision rewritten to `allow` with no
cryptographic tripwire.

What surfaces the tamper is the boundary: `canonical-profile` is
`fail`/`enforced=false` (the profile form was tried and did not match),
`canonical-response-only` is `pass`, and `unsignedFields` lists
`metadata.policy_decision`, `metadata.policy_id`,
`metadata.policy_version` and the rest of `metadata.json` — every field
a relying party must NOT trust as bound. This is the security payload
of the whole boundary work: a package can verify while its policy
decision was rewritable, and only the emitted boundary says so.

Produced by `scripts/generate-boundary-vectors.mjs`.

# oauthlib 4.0.1: reading of the flags

A flag is a case with a target that the target does not decide. The columns
"target fires" and "own test without the target" are mechanical and come from
`generated/oauthlib/flags.csv`. The class is a reading of the sources, with its
reason, and is reported as a reading. Line numbers refer to the commit of the
subject (`subjects/oauthlib/subject.json`, commit `6e3aa05a`).

Classes: **A** the test does not reach its target; **B** the target fires and a
handler replaces its exception; **C** the target the rule assigned is not the
check the test describes; **D** cannot be decided from the sources. The
classes are tried in the order C, A, B, D, and a flag gets the first that
fits.

Check identifiers are shortened: `ac.` stands for
`oauth2.rfc6749.grant_types.authorization_code.AuthorizationCodeGrant.`,
`hybrid.` for `openid.connect.core.grant_types.hybrid.HybridGrant.` and
`implicit.` for `openid.connect.core.grant_types.implicit.ImplicitGrant.`.

| Case | Target | Decided by | Target fires | Own test without the target | Class |
|---|---|---|---|---|---|
| `AuthorizationCodeGrantTest.test_pkce_required_verifier_invalid_challenge_valid_method_valid#0` (`tests/oauth2/rfc6749/grant_types/test_authorization_code.py:300`) | `ac.validate_token_request#8` | `ac.validate_token_request#4` | no | passes | C |
| `AuthorizationCodeGrantTest.test_pkce_verifier_valid_challenge_valid_method_missing#0` (`tests/oauth2/rfc6749/grant_types/test_authorization_code.py:316`) | `ac.validate_token_request#4` | `ac.validate_token_request#6` | no | passes | C |
| `OpenIDAuthCodeInterferenceTest.test_pkce_required_verifier_invalid_challenge_valid_method_valid#0` (block at `tests/oauth2/rfc6749/grant_types/test_authorization_code.py:300`, run under `tests/openid/connect/core/grant_types/test_authorization_code.py`) | `ac.validate_token_request#8` | `ac.validate_token_request#4` | no | passes | C |
| `OpenIDAuthCodeInterferenceTest.test_pkce_verifier_valid_challenge_valid_method_missing#0` (block at `tests/oauth2/rfc6749/grant_types/test_authorization_code.py:316`, run under `tests/openid/connect/core/grant_types/test_authorization_code.py`) | `ac.validate_token_request#4` | `ac.validate_token_request#6` | no | passes | C |
| `OpenIDHybridCodeIdTokenTest.test_required_nonce#0` (`tests/openid/connect/core/grant_types/test_hybrid.py:62`) | `ac.validate_authorization_request#8` | `hybrid.openid_authorization_validator#1` | no | passes | C |
| `OpenIDHybridCodeIdTokenTokenTest.test_required_nonce#0` (`tests/openid/connect/core/grant_types/test_hybrid.py:96`) | `ac.validate_authorization_request#8` | `hybrid.openid_authorization_validator#1` | no | passes | C |
| `OpenIDHybridInterferenceTest.test_pkce_required_verifier_invalid_challenge_valid_method_valid#0` (block at `tests/oauth2/rfc6749/grant_types/test_authorization_code.py:300`, run under `tests/openid/connect/core/grant_types/test_hybrid.py`) | `ac.validate_token_request#8` | `ac.validate_token_request#4` | no | passes | C |
| `OpenIDHybridInterferenceTest.test_pkce_verifier_valid_challenge_valid_method_missing#0` (block at `tests/oauth2/rfc6749/grant_types/test_authorization_code.py:316`, run under `tests/openid/connect/core/grant_types/test_hybrid.py`) | `ac.validate_token_request#4` | `ac.validate_token_request#6` | no | passes | C |
| `OpenIDImplicitNoAccessTokenTest.test_required_nonce#0` (`tests/openid/connect/core/grant_types/test_implicit.py:164`) | `ac.validate_authorization_request#8` | `implicit.openid_authorization_validator#1` | no | passes | C |
| `OpenIDImplicitTest.test_required_nonce#0` (`tests/openid/connect/core/grant_types/test_implicit.py:143`) | `ac.validate_authorization_request#8` | `implicit.openid_authorization_validator#1` | no | passes | C |

Counts: A 0, B 0, C 10, D 0.

## Reasons

**The 10 cases come from 4 blocks.** Rows 1, 3 and 7 are 3 executions of 1
block, `test_pkce_required_verifier_invalid_challenge_valid_method_valid#0`
(`tests/oauth2/rfc6749/grant_types/test_authorization_code.py`, lines 295 to
301), and rows 2, 4 and 8 of 1 block,
`test_pkce_verifier_valid_challenge_valid_method_missing#0` (lines 311 to
317). The test class `AuthorizationCodeGrantTest` that holds them is imported
by `tests/openid/connect/core/grant_types/test_authorization_code.py` (lines
14 to 16) and subclassed there as `OpenIDAuthCodeInterferenceTest` (lines 24
to 29), and in `tests/openid/connect/core/grant_types/test_hybrid.py` as
`OpenIDHybridInterferenceTest` (lines 15 to 20). Both subclasses only replace
`self.auth` by an OpenID Connect grant. That grant hands
`validate_token_request` to an OAuth 2.0 `AuthorizationCodeGrant` through
`__getattr__` (`oauthlib/openid/connect/core/grant_types/base.py`, lines 19
to 20; `hybrid.py`, lines 23 to 24), so the 3 executions of each block run the
same code on the same input and share 1 reason. The 4 cases named
`test_required_nonce` come from 4 blocks of 4 test classes with 1 test body.
All 10 targets were assigned in the name tier (`subjects/oauthlib/targets.json`,
basis `name`).

**The 3 cases of `test_pkce_required_verifier_invalid_challenge_valid_method_valid#0`
(rows 1, 3, 7): C.** The test requires Proof Key for Code Exchange (PKCE),
sends the verifier `"foobar"` and makes the validator return the stored
challenge `"raboof"` with the method `"plain"` (test file, lines 296 to 299);
the block expects `InvalidGrantError` and asserts nothing more (lines 300 to
301). The name says the challenge is invalid, and the challenge is present,
so the check the test describes is the comparison of verifier and challenge:
the raise at line 491 of `oauthlib/oauth2/rfc6749/grant_types/authorization_code.py`
(lines 487 to 491), which belongs to check `ac.validate_token_request#4`
because it raises the same class with the same empty message as line 468.
The rule gave `ac.validate_token_request#8`, "Challenge not found" (lines 492
to 495), which applies only when the validator returns no challenge (line
473 takes the branch `challenge is not None`). It won on the tokens
`challenge`, `invalid`, `pkce` and `required` (score 4.28 against 3.58 for
`#4`, `targets.json`). The case is decided by `#4`, the described check.

**The 3 cases of `test_pkce_verifier_valid_challenge_valid_method_missing#0`
(rows 2, 4, 8): C.** The test returns a stored challenge `"foobar"` and no
challenge method (`get_code_challenge_method.return_value = None`, test file,
lines 312 to 315), and the block expects `InvalidGrantError` (lines 316 to
317). The name says the method is missing. The check the test describes is
`ac.validate_token_request#6`, "Challenge method not found"
(`authorization_code.py`, lines 477 to 479), which decides the case. The rule
gave `ac.validate_token_request#4` (lines 468 and 491), which won on the
tokens `challenge`, `method` and `verifier` (score 3.58 against 1.79 for `#6`,
`targets.json`).

**The 4 cases of `test_required_nonce` (rows 5, 6, 9, 10): C.** Each test sets
`self.request.nonce = None` and expects `InvalidRequestError` from
`validate_authorization_request` (`test_hybrid.py`, lines 61 to 62 and 95 to
96; `test_implicit.py`, lines 142 to 143 and 163 to 164); the test then checks
that the authorization response carries `error=invalid_request` (for example
`test_hybrid.py`, lines 64 to 68). The test classes use the response types
`code id_token` and `code id_token token` with `HybridGrant` (`test_hybrid.py`,
lines 51 to 53 and 85 to 87) and `id_token token` and `id_token` with the
OpenID Connect `ImplicitGrant` (`test_implicit.py`, lines 29 and 155), and
the scope `openid`. The check the test describes is the mandatory nonce
check: `hybrid.openid_authorization_validator#1`
(`oauthlib/openid/connect/core/grant_types/hybrid.py`, lines 57 to 61, "Request
is missing mandatory nonce parameter.") for the 2 hybrid classes, and
`implicit.openid_authorization_validator#1`
(`oauthlib/openid/connect/core/grant_types/implicit.py`, lines 46 to 50, same
message) for the 2 implicit classes. These are the checks that decide the
cases. They run as validators appended to `custom_validators.post_auth`
(`hybrid.py`, lines 30 to 31; `implicit.py`, lines 24 to 25), called at line
431 of `authorization_code.py` and through `custom_validators.all_post` at
lines 352 to 356 of `oauthlib/oauth2/rfc6749/grant_types/implicit.py`. No call
names them, so they are not reachable by name from the entry points
(`generated/oauthlib/checks.csv`, column `reachable`: no) and are not among the
candidates of the rule. Among the 17 candidates of class `InvalidRequestError`
or a subclass, the rule gave `ac.validate_authorization_request#8`, a
`MissingCodeChallengeError` raised when PKCE is required and no code
challenge is sent (`authorization_code.py`, lines 405 to 406), on the single
token `required`, which it shares with the guard `is_pkce_required`
(`targets.json`, score 2.83, all other scores 0). The test sends no challenge
and is about the nonce; for the 2 implicit classes the target lies in another
grant type, which these tests never call.

## What the flags of this library show

All 10 flags are wrong targets of the rule, all in the name tier: 6 cases of 2
PKCE blocks, each run under 3 test classes, where the name of the test scored
a sibling check of the same class higher than the check the test describes,
and 4 cases of nonce tests whose described check is not reachable by name and
so was no candidate. In each of the 10 the check the test describes decides
the case. No flag is a test whose input another check rejects first, and none
is a target replaced by a handler.

#!/usr/bin/env python3
"""Define the checks and the cases of the PyJWT study (see PROTOCOL.md).

    work/venv/bin/python define_s2.py [--subject work/pyjwt]

Reads the subject's source and its own tests, applies the rules of the
protocol, and writes checks.json and cases.json next to this file. Both files
are fixed before any observation. The runner refuses to start when the
subject differs from the SHA-256 values they record.

The two tables below are the only hand-written part: CHECKS names the checks
of the two mutated files, and LABELS gives each included block its target
check, or the reason it has none. Everything else is read from the source and
validated against these tables.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMIT = "7d5ef55e42ce42221f58dc49943e92ccad1fa66a"
MUTATED = ["jwt/api_jws.py", "jwt/api_jwt.py"]
EXTERNAL = ["jwt/algorithms.py"]
EXCEPTIONS = "jwt/exceptions.py"

# Functions of the mutated files that a decode call can execute: the subject.
SUBJECT_FUNCTIONS = {
    "jwt/api_jws.py": [
        "PyJWS.__init__", "PyJWS._get_default_options", "PyJWS.get_algorithm_by_name",
        "PyJWS.decode_complete", "PyJWS.decode", "PyJWS._decode_base64url_segment",
        "PyJWS._load", "PyJWS._verify_signature", "PyJWS._validate_headers",
        "PyJWS._validate_kid", "PyJWS._validate_crit",
    ],
    "jwt/api_jwt.py": [
        "PyJWT.__init__", "PyJWT._get_default_options", "PyJWT._get_sig_options",
        "PyJWT._merge_options", "PyJWT.decode_complete", "PyJWT._decode_payload",
        "PyJWT.decode", "PyJWT._validate_claims", "PyJWT._validate_required_claims",
        "PyJWT._validate_sub", "PyJWT._validate_jti", "PyJWT._validate_iat",
        "PyJWT._validate_nbf", "PyJWT._validate_exp", "PyJWT._validate_aud",
        "PyJWT._validate_iss",
    ],
}
# The encoding side, which only builds tokens, as the signer did in the first study.
OUTSIDE_FUNCTIONS = {
    "jwt/api_jws.py": [
        "PyJWS.register_algorithm", "PyJWS.unregister_algorithm", "PyJWS.get_algorithms",
        "PyJWS.encode", "PyJWS.get_unverified_header",
    ],
    "jwt/api_jwt.py": ["PyJWT.encode", "PyJWT._encode_payload"],
}

# id, file, function, ordinals of its raise statements in that function.
CHECKS = [
    ("jws.alg-required", "jwt/api_jws.py", "PyJWS.decode_complete", [0]),
    ("jws.detached-requires-b64-false", "jwt/api_jws.py", "PyJWS.decode_complete", [1]),
    ("jws.b64-requires-crit", "jwt/api_jws.py", "PyJWS.decode_complete", [2]),
    ("jws.b64-requires-detached", "jwt/api_jws.py", "PyJWS.decode_complete", [3]),
    ("jws.segment-encoding", "jwt/api_jws.py", "PyJWS._decode_base64url_segment", [0, 1, 2, 3, 4]),
    ("jws.token-type", "jwt/api_jws.py", "PyJWS._load", [0]),
    ("jws.segments", "jwt/api_jws.py", "PyJWS._load", [1]),
    ("jws.header-json", "jwt/api_jws.py", "PyJWS._load", [2]),
    ("jws.header-object", "jwt/api_jws.py", "PyJWS._load", [3]),
    ("jws.b64-empty-payload", "jwt/api_jws.py", "PyJWS._load", [4]),
    ("jws.alg-present", "jwt/api_jws.py", "PyJWS._verify_signature", [0]),
    ("jws.alg-allowed", "jwt/api_jws.py", "PyJWS._verify_signature", [1]),
    ("jws.jwk-alg-match", "jwt/api_jws.py", "PyJWS._verify_signature", [2]),
    ("jws.alg-supported", "jwt/api_jws.py", "PyJWS._verify_signature", [3]),
    ("jws.key-length", "jwt/api_jws.py", "PyJWS._verify_signature", [4]),
    ("jws.signature", "jwt/api_jws.py", "PyJWS._verify_signature", [5]),
    ("jws.kid-type", "jwt/api_jws.py", "PyJWS._validate_kid", [0]),
    ("jws.crit-list", "jwt/api_jws.py", "PyJWS._validate_crit", [0]),
    ("jws.crit-strings", "jwt/api_jws.py", "PyJWS._validate_crit", [1]),
    ("jws.crit-supported", "jwt/api_jws.py", "PyJWS._validate_crit", [2]),
    ("jws.crit-present", "jwt/api_jws.py", "PyJWS._validate_crit", [3]),
    ("jwt.payload-json", "jwt/api_jwt.py", "PyJWT._decode_payload", [0]),
    ("jwt.payload-object", "jwt/api_jwt.py", "PyJWT._decode_payload", [1]),
    ("jwt.required", "jwt/api_jwt.py", "PyJWT._validate_required_claims", [0]),
    ("jwt.iat-type", "jwt/api_jwt.py", "PyJWT._validate_iat", [0]),
    ("jwt.iat-future", "jwt/api_jwt.py", "PyJWT._validate_iat", [1]),
    ("jwt.nbf-type", "jwt/api_jwt.py", "PyJWT._validate_nbf", [0]),
    ("jwt.nbf-future", "jwt/api_jwt.py", "PyJWT._validate_nbf", [1]),
    ("jwt.exp-type", "jwt/api_jwt.py", "PyJWT._validate_exp", [0]),
    ("jwt.exp-expired", "jwt/api_jwt.py", "PyJWT._validate_exp", [1]),
    ("jwt.iss-present", "jwt/api_jwt.py", "PyJWT._validate_iss", [0]),
    ("jwt.iss-type", "jwt/api_jwt.py", "PyJWT._validate_iss", [1]),
    ("jwt.iss-match", "jwt/api_jwt.py", "PyJWT._validate_iss", [2, 3]),
    ("jwt.iss-param-type", "jwt/api_jwt.py", "PyJWT._validate_iss", [4]),
    ("jwt.aud-unexpected", "jwt/api_jwt.py", "PyJWT._validate_aud", [0]),
    ("jwt.aud-present", "jwt/api_jwt.py", "PyJWT._validate_aud", [1]),
    ("jwt.aud-strict-param", "jwt/api_jwt.py", "PyJWT._validate_aud", [2]),
    ("jwt.aud-strict-claim-format", "jwt/api_jwt.py", "PyJWT._validate_aud", [3]),
    ("jwt.aud-strict-match", "jwt/api_jwt.py", "PyJWT._validate_aud", [4]),
    ("jwt.aud-claim-format", "jwt/api_jwt.py", "PyJWT._validate_aud", [5, 6]),
    ("jwt.aud-match", "jwt/api_jwt.py", "PyJWT._validate_aud", [7]),
    ("jwt.sub-type", "jwt/api_jwt.py", "PyJWT._validate_sub", [0]),
    ("jwt.sub-match", "jwt/api_jwt.py", "PyJWT._validate_sub", [1]),
    ("jwt.jti-type", "jwt/api_jwt.py", "PyJWT._validate_jti", [0]),
    # Key checks in jwt/algorithms.py that a case can reach. Not mutated, not deleted.
    ("alg.none-key", "jwt/algorithms.py", "NoneAlgorithm.prepare_key", [0]),
    ("alg.hmac-empty-key", "jwt/algorithms.py", "HMACAlgorithm.prepare_key", [0]),
    ("alg.hmac-asymmetric-key", "jwt/algorithms.py", "HMACAlgorithm.prepare_key", [1]),
    ("alg.hmac-jwk-key", "jwt/algorithms.py", "HMACAlgorithm.prepare_key", [2, 3]),
    ("alg.ec-curve", "jwt/algorithms.py", "ECAlgorithm._validate_curve", [0]),
]

# The order in which PyJWT.decode evaluates the checks. A segment-encoding check
# runs once per segment; the external key checks run where the key is prepared.
ORDER = [
    "jws.alg-required", "jws.token-type", "jws.segments",
    "jws.segment-encoding:header", "jws.header-json", "jws.header-object",
    "jws.b64-empty-payload", "jws.segment-encoding:payload", "jws.segment-encoding:crypto",
    "jws.kid-type", "jws.crit-list", "jws.crit-strings", "jws.crit-supported", "jws.crit-present",
    "jws.detached-requires-b64-false", "jws.b64-requires-crit", "jws.b64-requires-detached",
    "jws.alg-present", "jws.alg-allowed", "jws.jwk-alg-match", "jws.alg-supported",
    "alg.none-key", "alg.hmac-empty-key", "alg.hmac-asymmetric-key", "alg.hmac-jwk-key",
    "alg.ec-curve", "jws.key-length", "jws.signature",
    "jwt.payload-json", "jwt.payload-object", "jwt.required",
    "jwt.iat-type", "jwt.iat-future", "jwt.nbf-type", "jwt.nbf-future",
    "jwt.exp-type", "jwt.exp-expired",
    "jwt.iss-present", "jwt.iss-type", "jwt.iss-match", "jwt.iss-param-type",
    "jwt.aud-unexpected", "jwt.aud-present", "jwt.aud-strict-param",
    "jwt.aud-strict-claim-format", "jwt.aud-strict-match", "jwt.aud-claim-format",
    "jwt.aud-match", "jwt.sub-type", "jwt.sub-match", "jwt.jti-type",
]
SEGMENT_CALLS = {"header": 0, "payload": 1, "crypto": 2}  # ordinal of the call in PyJWS._load


def lab(target: str, basis: str, segment: str | None = None) -> dict:
    return {"target": target, "segment": segment, "basis": basis}


def unl(reason: str) -> dict:
    return {"target": None, "reason": reason}


IA = "InvalidAudienceError only; "
LABELS = {
    "test_advisory.py::test_ghsa_ffqj_6fqr_9h24#0": unl(
        "InvalidKeyError only, which six checks raise; the name is an advisory identifier"),
    "test_advisory.py::test_ghsa_ffqj_6fqr_9h24#1": unl(
        "InvalidKeyError only, which six checks raise; the name is an advisory identifier"),
    "test_algorithms.py::test_jwt_encode_decode_rejects_wrong_curve#1": lab(
        "alg.ec-curve", "name: wrong curve"),
    "test_algorithms.py::test_pyjwt_decode_enforces_short_hmac_key#0": lab(
        "jws.key-length", "name: short HMAC key"),
    "test_algorithms.py::test_pyjwt_decode_honors_per_call_enforce_minimum_key_length#0": lab(
        "jws.key-length", "match 'below'; name: minimum key length"),
    "test_algorithms.py::test_pyjwt_decode_honors_per_call_enforce_minimum_key_length#1": lab(
        "jws.key-length", "match 'below'; name: minimum key length"),
    "test_api_jws.py::test_decode_fails_when_alg_is_not_on_method_algorithms_param#0": lab(
        "jws.alg-allowed", "name: alg not on the algorithms parameter"),
    "test_api_jws.py::test_decode_missing_segments_throws_exception#0": lab(
        "jws.segments", "message equals the check's"),
    "test_api_jws.py::test_decode_invalid_token_type_is_none#0": lab(
        "jws.token-type", "message contains 'Invalid token type'"),
    "test_api_jws.py::test_decode_invalid_token_type_is_int#0": lab(
        "jws.token-type", "message contains 'Invalid token type'"),
    "test_api_jws.py::test_decode_with_non_mapping_header_throws_exception#0": lab(
        "jws.header-object", "message equals the check's"),
    "test_api_jws.py::test_encode_with_headers_alg_none#0": lab(
        "jws.signature", "message equals the check's"),
    "test_api_jws.py::test_decode_algorithm_param_should_be_case_sensitive#0": lab(
        "jws.alg-supported", "message equals the check's"),
    "test_api_jws.py::test_bad_secret#0": lab("jws.signature", "message equals the check's"),
    "test_api_jws.py::test_bad_secret#1": lab("jws.signature", "message equals the check's"),
    "test_api_jws.py::test_decodes_with_jwk_and_mismatched_algorithm#0": unl(
        "InvalidAlgorithmError only; the name fits two checks: the allow-list check and the "
        "check that the token's algorithm matches the key's"),
    "test_api_jws.py::test_decodes_with_jwk_rejects_header_alg_outside_jwk_alg#0": lab(
        "jws.jwk-alg-match", "match 'does not match the key's algorithm'"),
    "test_api_jws.py::test_decode_with_optional_algorithms#0": lab(
        "jws.alg-required", "message contains the check's"),
    "test_api_jws.py::test_no_secret#0": lab("alg.hmac-empty-key", "match 'must not be empty'"),
    "test_api_jws.py::test_verify_signature_with_no_secret#0": lab(
        "alg.hmac-empty-key", "match 'must not be empty'"),
    "test_api_jws.py::test_verify_signature_with_no_algo_header_throws_exception#0": lab(
        "jws.alg-present", "name: no alg header"),
    "test_api_jws.py::test_decode_invalid_header_padding#0": lab(
        "jws.segment-encoding", "message contains 'header padding'", "header"),
    "test_api_jws.py::test_decode_invalid_header_string#0": unl(
        "message contains 'Invalid header', as three checks' messages do; the name 'invalid "
        "header string' fits two of them, the JSON check and the object check"),
    "test_api_jws.py::test_decode_deeply_nested_header_throws_decode_error#0": lab(
        "jws.header-json", "match 'Invalid header'; name: deeply nested header, which only the "
        "JSON check handles (it catches RecursionError)"),
    "test_api_jws.py::test_decode_invalid_payload_padding#0": lab(
        "jws.segment-encoding", "message contains 'Invalid payload padding'", "payload"),
    "test_api_jws.py::test_decode_invalid_crypto_padding#0": lab(
        "jws.segment-encoding", "message contains 'Invalid crypto padding'", "crypto"),
    "test_api_jws.py::test_decode_rejects_non_canonical_crypto_segment#0": lab(
        "jws.segment-encoding", "match 'Invalid crypto padding'", "crypto"),
    "test_api_jws.py::test_decode_rejects_embedded_padding_in_crypto_segment#0": lab(
        "jws.segment-encoding", "match 'Invalid crypto padding'", "crypto"),
    "test_api_jws.py::test_decode_with_algo_none_should_fail#0": unl(
        "DecodeError only; no check's message or condition names the 'none' algorithm"),
    "test_api_jws.py::test_decode_rejects_detached_payload_for_attached_content#0": lab(
        "jws.detached-requires-b64-false", "match 'detached_payload.*b64.*false'"),
    "test_api_jws.py::test_decode_b64_false_rejects_non_empty_payload_segment#0": lab(
        "jws.b64-empty-payload", "match 'Payload segment must be empty'"),
    "test_api_jws.py::test_decode_b64_false_without_crit_b64_is_rejected#0": lab(
        "jws.b64-requires-crit", "match 'b64.*crit'"),
    "test_api_jws.py::test_decode_detached_content_without_proper_argument#0": lab(
        "jws.b64-requires-detached", "message contains the check's"),
    "test_api_jws.py::test_decode_rejects_unknown_crit_extension#0": lab(
        "jws.crit-supported", "match 'Unsupported critical extension'"),
    "test_api_jws.py::test_decode_rejects_empty_crit#0": lab(
        "jws.crit-list", "match 'must be a non-empty list'"),
    "test_api_jws.py::test_decode_rejects_non_list_crit#0": lab(
        "jws.crit-list", "match 'must be a non-empty list'"),
    "test_api_jws.py::test_decode_rejects_crit_with_non_string_values#0": lab(
        "jws.crit-strings", "match 'values must be strings'"),
    "test_api_jws.py::test_decode_rejects_crit_extension_missing_from_header#0": lab(
        "jws.crit-present", "match 'missing from headers'"),
    "test_api_jwt.py::test_reused_options_do_not_disable_claim_verification#0": lab(
        "jwt.exp-expired", "class ExpiredSignatureError, which only the expiry check raises"),
    "test_api_jwt.py::test_decode_invalid_payload_string#0": unl(
        "message contains 'Invalid payload string', which two checks' messages start with; "
        "the name fits both"),
    "test_api_jwt.py::test_decode_payload_recursion_error_throws_decode_error#0": lab(
        "jwt.payload-json", "match 'Invalid payload' and a RecursionError cause, which only the "
        "payload JSON check chains"),
    "test_api_jwt.py::test_decode_with_non_mapping_payload_throws_exception#0": lab(
        "jwt.payload-object", "message equals the check's"),
    "test_api_jwt.py::test_decode_with_nonlist_aud_claim_throws_exception#0": lab(
        "jwt.aud-claim-format", "message equals the check's"),
    "test_api_jwt.py::test_decode_with_invalid_aud_list_member_throws_exception#0": lab(
        "jwt.aud-claim-format", "message equals the check's"),
    "test_api_jwt.py::test_decode_raises_exception_if_exp_is_not_int#0": lab(
        "jwt.exp-type", "message contains 'exp'; name: exp is not an int"),
    "test_api_jwt.py::test_decode_raises_exception_if_iat_is_not_int#0": lab(
        "jwt.iat-type", "class InvalidIssuedAtError, which only the iat type check raises"),
    "test_api_jwt.py::test_decode_raises_exception_if_iat_is_greater_than_now#0": lab(
        "jwt.iat-future", "class ImmatureSignatureError (two checks); name: iat later than now"),
    "test_api_jwt.py::test_decode_raises_exception_if_nbf_is_not_int#0": lab(
        "jwt.nbf-type", "name: nbf is not an int"),
    "test_api_jwt.py::test_decode_raises_clean_error_if_claim_is_non_numeric_type#0": {
        "by_param": "claim",
        "values": {
            "exp": dict(lab("jwt.exp-type", "name: non-numeric claim; message contains 'exp'"),
                        expected="DecodeError"),
            "nbf": dict(lab("jwt.nbf-type", "name: non-numeric claim; message contains 'nbf'"),
                        expected="DecodeError"),
            "iat": dict(lab("jwt.iat-type", "name: non-numeric claim; message contains 'iat'"),
                        expected="InvalidIssuedAtError"),
        },
    },
    "test_api_jwt.py::test_decode_with_expiration#0": lab(
        "jwt.exp-expired", "class ExpiredSignatureError, which only the expiry check raises"),
    "test_api_jwt.py::test_decode_with_notbefore#0": lab(
        "jwt.nbf-future", "class ImmatureSignatureError (two checks); name: not before"),
    "test_api_jwt.py::test_decode_with_expiration_with_leeway#0": lab(
        "jwt.exp-expired", "class ExpiredSignatureError, which only the expiry check raises"),
    "test_api_jwt.py::test_decode_with_notbefore_with_leeway#0": lab(
        "jwt.nbf-future", "class ImmatureSignatureError (two checks); name: not before"),
    "test_api_jwt.py::test_check_audience_none_specified#0": lab(
        "jwt.aud-unexpected", "name: no audience specified, while the token carries one"),
    "test_api_jwt.py::test_raise_exception_invalid_audience_list#0": unl(
        IA + "'invalid audience' is one check's message and another check's condition"),
    "test_api_jwt.py::test_raise_exception_invalid_audience#0": unl(
        IA + "'invalid audience' is one check's message and another check's condition"),
    "test_api_jwt.py::test_raise_exception_audience_as_bytes#0": unl(
        IA + "no check's message or condition names a bytes audience"),
    "test_api_jwt.py::test_raise_exception_invalid_audience_in_array#0": unl(
        IA + "'invalid audience' is one check's message and another check's condition"),
    "test_api_jwt.py::test_raise_exception_token_without_issuer#0": lab(
        "jwt.iss-present", "claim 'iss'; name: token without issuer"),
    "test_api_jwt.py::test_rasise_exception_on_partial_issuer_match#0": lab(
        "jwt.iss-match", "class InvalidIssuerError (three checks); name: issuer match"),
    "test_api_jwt.py::test_raise_exception_token_without_audience#0": lab(
        "jwt.aud-present", "claim 'aud'; name: token without audience"),
    "test_api_jwt.py::test_raise_exception_token_with_aud_none_and_without_audience#0": lab(
        "jwt.aud-present", "claim 'aud'; name: token without audience"),
    "test_api_jwt.py::test_raise_exception_invalid_issuer#0": lab(
        "jwt.iss-match", "class InvalidIssuerError (three checks); name: the check's message"),
    "test_api_jwt.py::test_raise_exception_invalid_issuer_list#0": lab(
        "jwt.iss-match", "class InvalidIssuerError (three checks); name: the check's message"),
    "test_api_jwt.py::test_decode_should_raise_error_if_exp_required_but_not_present#0": lab(
        "jwt.required", "claim 'exp'; name: required but not present"),
    "test_api_jwt.py::test_decode_should_raise_error_if_iat_required_but_not_present#0": lab(
        "jwt.required", "claim 'iat'; name: required but not present"),
    "test_api_jwt.py::test_decode_should_raise_error_if_nbf_required_but_not_present#0": lab(
        "jwt.required", "claim 'nbf'; name: required but not present"),
    "test_api_jwt.py::test_decode_with_verify_exp_option#0": lab(
        "jwt.exp-expired", "class ExpiredSignatureError, which only the expiry check raises"),
    "test_api_jwt.py::test_decode_with_verify_exp_option_and_signature_off#0": lab(
        "jwt.exp-expired", "class ExpiredSignatureError, which only the expiry check raises"),
    "test_api_jwt.py::test_decode_with_optional_algorithms#0": lab(
        "jws.alg-required", "message contains the check's"),
    "test_api_jwt.py::test_decode_strict_aud_forbids_list_audience#0": lab(
        "jwt.aud-strict-param", "match 'Invalid audience \\(strict\\)'"),
    "test_api_jwt.py::test_decode_strict_aud_forbids_list_claim#0": lab(
        "jwt.aud-strict-claim-format", "match 'Invalid claim format in token \\(strict\\)'"),
    "test_api_jwt.py::test_decode_strict_aud_does_not_match#0": lab(
        "jwt.aud-strict-match", "match 'Audience doesn't match \\(strict\\)'"),
    "test_api_jwt.py::test_decode_missing_sub_but_required_claim#0": lab(
        "jwt.required", "class MissingRequiredClaimError (three checks); name: sub required"),
    "test_api_jwt.py::test_decode_invalid_int_sub_claim#0": lab(
        "jwt.sub-type", "class InvalidSubjectError (two checks); name: int sub claim"),
    "test_api_jwt.py::test_decode_with_invalid_sub_claim#0": lab(
        "jwt.sub-match", "message contains 'Invalid subject'"),
    "test_api_jwt.py::test_decode_missing_jti_when_required_claim#0": lab(
        "jwt.required", "message contains 'jti'; name: jti required"),
    "test_api_jwt.py::test_jti_claim_with_invalid_int_value#0": lab(
        "jwt.jti-type", "class InvalidJTIError, which only the jti type check raises"),
    "test_api_jwt.py::test_decode_rejects_token_with_unknown_crit_extension#0": lab(
        "jws.crit-supported", "match 'Unsupported critical extension'"),
}


# -- reading the source -------------------------------------------------------

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    """Qualified name -> definition, for module functions and methods, including
    classes defined under a module-level `if` (as in jwt/algorithms.py)."""
    found: dict[str, ast.FunctionDef] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[prefix + child.name] = child
            elif isinstance(child, (ast.If, ast.Try)):
                walk(child, prefix)

    walk(tree, "")
    return found


def raise_nodes(fn: ast.AST) -> list[ast.Raise]:
    """The raise statements of a function in source order, not counting nested
    functions or classes. The recorder numbers them the same way."""
    out: list[ast.Raise] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(child, ast.Raise):
                out.append(child)
            visit(child)

    visit(fn)
    return sorted(out, key=lambda r: (r.lineno, r.col_offset))


def raised_class(node: ast.Raise) -> str | None:
    exc = node.exc
    if exc is None:
        return None
    target = exc.func if isinstance(exc, ast.Call) else exc
    return ast.unparse(target)


def raised_message(node: ast.Raise) -> str:
    exc = node.exc
    if isinstance(exc, ast.Call) and exc.args:
        return ast.unparse(exc.args[0])
    return ""


def exception_hierarchy(subject: Path) -> dict[str, list[str]]:
    """Class name -> its PyJWT ancestors, read from jwt/exceptions.py."""
    tree = ast.parse((subject / EXCEPTIONS).read_text(encoding="utf-8"))
    parents = {n.name: [ast.unparse(b) for b in n.bases] for n in tree.body
               if isinstance(n, ast.ClassDef)}

    def ancestors(name: str) -> list[str]:
        out = [name]
        for base in parents.get(name, []):
            out += ancestors(base)
        return out

    return {name: ancestors(name) for name in parents}


# -- checks -------------------------------------------------------------------

def build_checks(subject: Path) -> dict:
    hierarchy = exception_hierarchy(subject)
    trees = {rel: ast.parse((subject / rel).read_text(encoding="utf-8"))
             for rel in MUTATED + EXTERNAL}
    fns = {rel: functions(tree) for rel, tree in trees.items()}

    for rel in MUTATED:
        listed = SUBJECT_FUNCTIONS[rel] + OUTSIDE_FUNCTIONS[rel]
        if sorted(listed) != sorted(fns[rel]):
            raise SystemExit(f"{rel}: function lists differ from the source: "
                             f"{sorted(set(fns[rel]) ^ set(listed))}")

    checks, claimed = [], set()
    for cid, rel, fname, ordinals in CHECKS:
        raises = raise_nodes(fns[rel][fname])
        nodes = [raises[k] for k in ordinals]
        classes = {raised_class(n) for n in nodes}
        messages = {raised_message(n) for n in nodes}
        if len(classes) != 1 or len(messages) != 1:
            raise SystemExit(f"{cid}: its raise statements differ in class or message")
        cls = classes.pop()
        if "PyJWTError" not in hierarchy.get(cls, []):
            raise SystemExit(f"{cid}: {cls} is not a PyJWTError")
        claimed |= {(rel, fname, k) for k in ordinals}
        checks.append({
            "id": cid,
            "file": rel,
            "function": fname,
            "raises": ordinals,
            "lines": [[n.lineno, n.end_lineno] for n in nodes],
            "class": cls,
            "message": messages.pop(),
            "mutated": rel in MUTATED,
        })

    # Every raise of a PyJWTError on the subject's functions belongs to a check.
    non_checks = []
    for rel in MUTATED:
        for fname in SUBJECT_FUNCTIONS[rel]:
            for k, node in enumerate(raise_nodes(fns[rel][fname])):
                cls = raised_class(node)
                is_jwt = "PyJWTError" in hierarchy.get(cls or "", [])
                if is_jwt and (rel, fname, k) not in claimed:
                    raise SystemExit(f"{rel} {fname} raise {k} ({cls}) belongs to no check")
                if not is_jwt:
                    non_checks.append({"file": rel, "function": fname, "raise": k,
                                       "line": node.lineno, "class": cls,
                                       "message": raised_message(node)})

    ids = [c["id"] for c in checks]
    order_ids = {o.split(":")[0] for o in ORDER}
    if order_ids != set(ids):
        raise SystemExit(f"ORDER and CHECKS differ: {sorted(order_ids ^ set(ids))}")

    load = fns["jwt/api_jws.py"]["PyJWS._load"]
    seg_calls = [n for n in ast.walk(load) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "_decode_base64url_segment"]
    seg_calls.sort(key=lambda n: (n.lineno, n.col_offset))
    names = [ast.literal_eval(c.args[1]) for c in seg_calls]
    if names != list(SEGMENT_CALLS):
        raise SystemExit(f"PyJWS._load calls the segment check for {names}")

    return {
        "subject": {
            "name": "PyJWT", "version": "2.15.1", "commit": COMMIT,
            "repository": "https://github.com/jpadilla/pyjwt", "licence": "MIT",
            "sha256": {rel: sha256(subject / rel) for rel in MUTATED + EXTERNAL + [EXCEPTIONS]},
        },
        "rule": "A check is the set of raise statements in one decode-path function that "
                "construct the same PyJWTError subclass with the same message template.",
        "subject_functions": SUBJECT_FUNCTIONS,
        "outside_functions": OUTSIDE_FUNCTIONS,
        "checks": checks,
        "order": ORDER,
        "segment_calls": SEGMENT_CALLS,
        "non_check_raises": non_checks,
        "exception_ancestors": hierarchy,
    }


# -- cases --------------------------------------------------------------------

DECODE_ENTRIES = {"decode", "decode_complete"}


def is_raises_call(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "raises" and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "pytest")


def called_names(body: list[ast.stmt]) -> list[str]:
    out = []
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                f = node.func
                out.append(f.attr if isinstance(f, ast.Attribute) else
                           f.id if isinstance(f, ast.Name) else ast.unparse(f))
    return out


def assertion_spec(test: ast.expr, value_names: set[str], exc_name: str) -> list | None:
    """Turn one assert on the block's exception into a spec, or None if it does
    not mention the exception. Anything unrecognised stops the definition."""

    def is_value(node: ast.AST) -> bool:
        if isinstance(node, ast.Name) and node.id in value_names:
            return True
        return (isinstance(node, ast.Attribute) and node.attr == "value"
                and isinstance(node.value, ast.Name) and node.value.id == exc_name)

    def is_str_of_value(node: ast.AST) -> bool:
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "str" and len(node.args) == 1 and is_value(node.args[0]))

    mentions = any(is_value(n) for n in ast.walk(test))
    if not mentions:
        return None
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        left, op, right = test.left, test.ops[0], test.comparators[0]
        if isinstance(op, ast.Eq):
            if is_str_of_value(left) and isinstance(right, ast.Constant):
                return ["str_eq", right.value]
            if is_str_of_value(right) and isinstance(left, ast.Constant):
                return ["str_eq", left.value]
            if (isinstance(left, ast.Attribute) and is_value(left.value)
                    and isinstance(right, ast.Constant)):
                return ["attr_eq", left.attr, right.value]
        if isinstance(op, ast.In) and is_str_of_value(right):
            if isinstance(left, ast.Constant):
                return ["str_in", left.value]
            if isinstance(left, ast.Name):
                return ["str_in_param", left.id]
    if (isinstance(test, ast.Call) and isinstance(test.func, ast.Name)
            and test.func.id == "isinstance" and len(test.args) == 2
            and isinstance(test.args[0], ast.Attribute) and test.args[0].attr == "__cause__"
            and is_value(test.args[0].value) and isinstance(test.args[1], ast.Name)):
        return ["cause_isinstance", test.args[1].id]
    raise SystemExit(f"unrecognised assertion on the exception: {ast.unparse(test)}")


def post_assertions(fn: ast.FunctionDef, block: ast.With, exc_name: str | None) -> list:
    """The assertions a test makes on a block's exception after the block, up to
    the next block that rebinds the same name."""
    if exc_name is None:
        return []
    later = sorted((n for n in ast.walk(fn) if isinstance(n, (ast.Assert, ast.Assign, ast.With))
                    and n.lineno > block.end_lineno), key=lambda n: n.lineno)
    values: set[str] = set()
    specs = []
    for node in later:
        if isinstance(node, ast.With):
            item = node.items[0]
            if (is_raises_call(item.context_expr) and isinstance(item.optional_vars, ast.Name)
                    and item.optional_vars.id == exc_name):
                break
            continue
        if isinstance(node, ast.Assign):
            if (isinstance(node.value, ast.Attribute) and node.value.attr == "value"
                    and isinstance(node.value.value, ast.Name) and node.value.value.id == exc_name):
                values |= {t.id for t in node.targets if isinstance(t, ast.Name)}
            continue
        spec = assertion_spec(node.test, values, exc_name)
        if spec is not None:
            specs.append(spec)
    return specs


def parametrize_values(fn: ast.FunctionDef) -> dict[str, list]:
    out = {}
    for deco in fn.decorator_list:
        if (isinstance(deco, ast.Call) and ast.unparse(deco.func) == "pytest.mark.parametrize"
                and isinstance(deco.args[0], ast.Constant)):
            try:
                out[deco.args[0].value] = ast.literal_eval(deco.args[1])
            except ValueError:
                out[deco.args[0].value] = [ast.unparse(e) for e in deco.args[1].elts]
    return out


def build_cases(subject: Path, checks: dict) -> dict:
    hierarchy = checks["exception_ancestors"]
    check_ids = {c["id"] for c in checks["checks"]}
    blocks, seen_keys = [], set()
    test_files = sorted((subject / "tests").glob("test_*.py"))
    for path in test_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls_name, fn in [(None, n) for n in tree.body if isinstance(n, ast.FunctionDef)] + [
                (c.name, n) for c in tree.body if isinstance(c, ast.ClassDef)
                for n in c.body if isinstance(n, ast.FunctionDef)]:
            withs = sorted((n for n in ast.walk(fn) if isinstance(n, ast.With)
                            and is_raises_call(n.items[0].context_expr)),
                           key=lambda n: n.lineno)
            for k, w in enumerate(withs):
                call = w.items[0].context_expr
                var = w.items[0].optional_vars
                exc_name = var.id if isinstance(var, ast.Name) else None
                expected = ast.unparse(call.args[0]) if call.args else None
                match = next((ast.literal_eval(kw.value) for kw in call.keywords
                              if kw.arg == "match"), None)
                names = called_names(w.body)
                key = f"{path.name}::{fn.name}#{k}"
                if key in seen_keys:
                    raise SystemExit(f"duplicate block key {key}")
                seen_keys.add(key)
                decode_calls = [n for n in names if n in DECODE_ENTRIES]
                exp_names = [e.strip() for e in (expected or "").strip("()").split(",") if e.strip()]
                pyjwt_expected = bool(exp_names) and all(
                    "PyJWTError" in hierarchy.get(e, []) for e in exp_names)
                row = {
                    "key": key,
                    "file": path.name,
                    "class": cls_name,
                    "test": fn.name,
                    "k": k,
                    "with_line": w.lineno,
                    "call_lines": [call.lineno, call.end_lineno],
                    "expected": expected,
                    "match": match,
                    "post": post_assertions(fn, w, exc_name),
                    "calls": sorted(set(names)),
                    "parametrize": parametrize_values(fn),
                }
                if not decode_calls:
                    row["included"] = False
                    row["exclusion"] = "the block calls no decode or decode_complete"
                elif key in LABELS and "by_param" in LABELS[key]:
                    row["included"] = True
                elif not pyjwt_expected:
                    row["included"] = False
                    row["exclusion"] = f"expects {expected}, which is not a PyJWTError"
                else:
                    row["included"] = True
                blocks.append(row)

    included = {b["key"] for b in blocks if b["included"]}
    if included != set(LABELS):
        raise SystemExit("LABELS and the included blocks differ:\n  missing labels: "
                         f"{sorted(included - set(LABELS))}\n  labels for no included block: "
                         f"{sorted(set(LABELS) - included)}")
    for b in blocks:
        if not b["included"]:
            continue
        label = LABELS[b["key"]]
        targets = ([v["target"] for v in label["values"].values()] if "by_param" in label
                   else [label["target"]])
        for t in targets:
            if t is not None and t not in check_ids:
                raise SystemExit(f"{b['key']}: unknown target {t}")
        if "by_param" in label:
            param = label["by_param"]
            if sorted(b["parametrize"].get(param, [])) != sorted(label["values"]):
                raise SystemExit(f"{b['key']}: labels by {param} differ from the parametrization")
        b["label"] = label

    inc = [b for b in blocks if b["included"]]
    labelled = [b for b in inc if "by_param" in b["label"] or b["label"]["target"] is not None]
    return {
        "subject": checks["subject"],
        "rules": {
            "case": "A case is one execution of a `with pytest.raises(...)` block of the subject's "
                    "own tests/ whose statements call decode or decode_complete (of PyJWS or "
                    "PyJWT, as a method, a module function or the jwt package function) and "
                    "whose expected exception is a PyJWTError subclass.",
            "target": "The target is the single check left after intersecting three candidate "
                      "sets: the checks that raise the asserted class or a subclass; the checks "
                      "whose message or attributes satisfy the test's assertions on the "
                      "exception (match=, assertions after the block), if it makes any; and the "
                      "checks whose message or condition the test's name names, if it names "
                      "any. If more than one check is left, the block has no target.",
        },
        "counts": {
            "raises_blocks": len(blocks),
            "decode_blocks": sum(1 for b in blocks if b.get("exclusion") !=
                                 "the block calls no decode or decode_complete"),
            "included_blocks": len(inc),
            "labelled_blocks": len(labelled),
            "unlabelled_blocks": len(inc) - len(labelled),
        },
        "test_files_sha256": {p.name: sha256(p) for p in test_files},
        "blocks": blocks,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--subject", default=str(HERE / "work" / "pyjwt"))
    args = parser.parse_args(argv)
    subject = Path(args.subject).resolve()
    checks = build_checks(subject)
    cases = build_cases(subject, checks)
    for name, data in (("checks.json", checks), ("cases.json", cases)):
        # Parametrized values that JSON cannot hold (bytes) are kept as their Python literal.
        text = json.dumps(data, indent=1, ensure_ascii=False, default=repr)
        (HERE / name).write_text(text + "\n", encoding="utf-8")
    n = sum(1 for c in checks["checks"] if c["mutated"])
    print(f"checks: {n} in the mutated files, {len(checks['checks']) - n} external; "
          f"non-check raises on the subject: {len(checks['non_check_raises'])}")
    print("cases:", json.dumps(cases["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

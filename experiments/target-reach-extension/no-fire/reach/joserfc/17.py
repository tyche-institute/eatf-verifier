#!/usr/bin/env python3
"""Row 17 of no-fire/sample.csv: joserfc `_keys.JWKRegistry.import_key#1`,
`raise MissingKeyTypeError("Missing key type")` at `joserfc/_keys.py`, line 70.

The source shows that no input through an entry point reaches line 70 (see
READING.md for the guards). `JWKRegistry.import_key` (`_keys.py` 55-79) is
called at 2 places of the package only: `jwk.import_key` (`jwk.py` 162) and
`KeySet.import_key_set` (`_keys.py` 178, through `registry_cls`, 115). No
function of the package calls either of them, and neither is an entry point.
The only key imported from a token is the "epk" header (`_rfc7518/jwe_algs.py`
225; the ECDH-1PU draft at `drafts/jwe_ecdh_1pu.py` 95 is not registered by
default), and it is imported by the class of the caller's key, ECKey or OKPKey
after `check_key_type` (224), whose `import_key` ends in `BaseKey.import_key`
(`_rfc7517/models.py` 270-282), not in `JWKRegistry.import_key`.

The inputs below are the closest ones found, run to show where they stop:

- input: `joserfc.jwe.decrypt_compact(token, key)`, no setting other than the
  key (an ECKey on P-256); the token is an ECDH-ES + A128GCM compact JWE for
  that key whose "epk" header has no "kty" member. Expected: KeyParameterError
  "'kty' is required" from `_rfc7517/models.py` 61, line 70 not executed.
- input-b: the same call with a well-formed token and the key given as a JWK
  dict without "kty". Expected: ValueError("Invalid key") from `jwk.py` 103
  (`guess_key` takes only key objects, a key set or a callable, 77-103), line
  70 not executed.

Controls, not inputs of the result:

- control-epk-with-kty: the well-formed token (the same "epk" with "kty")
  decrypts with the ECKey, so the token of the input differs only in "kty".
- control-import-key-set: a direct call of `KeySet.import_key_set` (not an
  entry point; PROTOCOL.md 4.4 excludes it as an input) with a key set whose
  key has no "kty", to show that the tracer records line 70 when it runs.
- control-key-callable: `decrypt_compact(token, resolve)`, where `resolve` is
  a key callable of the caller (`jwk.py` 59-60, 77-78) that builds the key with
  `KeySet.import_key_set` from a key set whose key has no "kty". The call of
  `import_key_set` is made by the caller's own code, a direct call of a
  function of the package that is not an entry point, which PROTOCOL.md 4.4
  excludes; it is run to show what the check does if such a callable were
  counted as a setting.

    python3 -I <this file>
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ beside the scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_harness as H  # noqa: E402

ROW = 17
CHECK = "_keys.JWKRegistry.import_key#1"
RECIPIENT_SECRET = 0x5A17_0C0F_FEE1_D00D_2026_1117_0017_0001
EPHEMERAL_SECRET = 0x0E9A_E5E5_C0DE_F00D_2026_1117_0017_0002
IV = bytes(range(100, 112))
PLAINTEXT = b'{"iss":"https://issuer.example","sub":"reach-17"}'


def token(with_kty: bool) -> tuple[str, dict]:
    recipient = H.p256_private_key(RECIPIENT_SECRET)
    ephemeral = H.p256_private_key(EPHEMERAL_SECRET)
    epk = H.p256_public_jwk(ephemeral, with_kty=with_kty)
    return H.jwe_ecdh_es_gcm(recipient.public_key(), ephemeral, PLAINTEXT, IV, epk), epk


def facts_of(value: str, epk: dict) -> dict:
    return {"token_sha256": H.sha256_bytes(value.encode("ascii")), "segment_lengths": H.segment_lengths(value),
            "epk_members": sorted(epk), "plaintext_sha256": H.sha256_bytes(PLAINTEXT)}


def build_epk(with_kty: bool):
    def make():
        from joserfc import jwe
        from joserfc.jwk import ECKey
        value, epk = token(with_kty)
        key = ECKey.import_key(H.p256_private_key(RECIPIENT_SECRET))
        return (lambda: jwe.decrypt_compact(value, key)), facts_of(value, epk)
    return make


def build_key_as_dict():
    from joserfc import jwe
    value, epk = token(True)
    private = H.p256_private_key(RECIPIENT_SECRET)
    jwk = H.p256_public_jwk(private, with_kty=False)
    jwk["d"] = H.b64url(private.private_numbers().private_value.to_bytes(32, "big")).decode("ascii")
    facts = facts_of(value, epk)
    facts["key_members"] = sorted(jwk)
    return (lambda: jwe.decrypt_compact(value, jwk)), facts


def build_import_key_set():
    from joserfc.jwk import KeySet
    jwk = H.p256_public_jwk(H.p256_private_key(RECIPIENT_SECRET), with_kty=False)
    return (lambda: KeySet.import_key_set({"keys": [jwk]})), {"key_members": sorted(jwk)}


def build_key_callable():
    from joserfc import jwe
    from joserfc.jwk import KeySet
    value, epk = token(True)
    private = H.p256_private_key(RECIPIENT_SECRET)
    jwk = H.p256_public_jwk(private, with_kty=False)
    jwk["d"] = H.b64url(private.private_numbers().private_value.to_bytes(32, "big")).decode("ascii")

    def resolve(obj):  # the caller's key callable: its own call of KeySet.import_key_set
        return KeySet.import_key_set({"keys": [jwk]})

    facts = facts_of(value, epk)
    facts["key_set_members"] = sorted(jwk)
    return (lambda: jwe.decrypt_compact(value, resolve)), facts


CASES = [
    H.Case("input", "input", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "key: ECKey (P-256); algorithms, registry, sender_key: defaults",
           "ECDH-ES + A128GCM compact JWE for the key whose epk header has no kty member",
           build_epk(False)),
    H.Case("input-b", "input", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "key: a JWK dict of the P-256 key without kty; algorithms, registry, sender_key: defaults",
           "well-formed ECDH-ES + A128GCM compact JWE (epk with kty)",
           build_key_as_dict),
    H.Case("control-epk-with-kty", "control", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "as the input", "the well-formed token (epk with kty)",
           build_epk(True)),
    H.Case("control-import-key-set", "control",
           "joserfc.jwk.KeySet.import_key_set (_keys.py:170; not an entry point)",
           "none", "key set {\"keys\": [P-256 public JWK without kty]}",
           build_import_key_set),
    H.Case("control-key-callable", "control", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "key: a callable of the caller that returns KeySet.import_key_set({\"keys\": [P-256 private JWK "
           "without kty]}); algorithms, registry, sender_key: defaults",
           "the well-formed token (epk with kty); the call of import_key_set is the caller's own code",
           build_key_callable),
]

if __name__ == "__main__":
    sys.exit(H.main(__file__, ROW, CHECK, CASES))

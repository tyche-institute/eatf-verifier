#!/usr/bin/env python3
"""Writes `reach.csv` of this folder: 1 row per sampled check of joserfc (rows
16 to 20 of `no-fire/sample.csv`, in that order), with the columns of
PROTOCOL.md 4.4 (`library` to `reason`) and then `row`, `input`, `fired`
(fires, does not fire or undecided), `record` and `source_lines`.

The class, message and raise site of each exception come from the records
`<n>.json` written by the scripts; the script stops if a record does not hold
what its row states (the sampled check, clean runs, identical repeat runs, and
for a check not reached no execution of its raise line). The reasons and the
source lines are those of READING.md. Paths of the source are relative to the
source root of the copy (`src/`).

    python3 -I -B <this file>
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTENSION = HERE.parents[2]
SAMPLE = EXTENSION / "no-fire" / "sample.csv"
PREFIX = "no-fire/reach/joserfc"
COLUMNS = ["library", "check", "result", "entry_point", "scripts", "settings", "exception", "reason",
           "row", "input", "fired", "record", "source_lines"]
FIRED = {"reached": "fires", "not reached": "does not fire", "undecided": "undecided"}
DEFAULTS = "no setting differs from its default (algorithms, registry and sender_key not given)"

ROWS = {
    16: {
        "result": "reached",
        "entry_point": "jwe.decrypt_compact (joserfc/jwe.py:96)",
        "settings": f"key: OctKey of a 16-byte key; {DEFAULTS}",
        "input": "compact JWE {\"alg\":\"dir\",\"enc\":\"A128GCM\"} sealed with the key, with 16 bytes in the JWE "
                 "Encrypted Key segment, which is to be empty with direct encryption (comment at "
                 "joserfc/_rfc7516/message.py 245-247); control: the same token with an empty segment decrypts",
        "reason": "The raise statement at joserfc/_rfc7516/message.py:249 executed and its RAISE event is a firing "
                  "by the rule of the recorder; the exception that reaches the caller is the object raised there. "
                  "On the way: joserfc/jwe.py 123-126 the default registry (joserfc/_rfc7516/registry.py 196); "
                  "128 extract_compact (joserfc/_rfc7516/compact.py 37-48 the sizes pass, 49-56 the header has alg "
                  "and enc, 75 keeps the 16 bytes of the second segment as recipient.encrypted_key); 131 guess_key "
                  "returns the OctKey (joserfc/jwk.py 82-83); 132 check_use passes, the key has no use "
                  "(joserfc/_rfc7517/models.py 220-222); 136 perform_decrypt -> joserfc/_rfc7516/message.py 101 "
                  "-> 107 get_enc(\"A128GCM\") passes (joserfc/_rfc7516/registry.py 185, 188, 192: registered and "
                  "recommended, joserfc/_rfc7518/jwe_encs.py 83, 114); 110 check_iv passes (12 bytes, iv_size 96 "
                  "bits: joserfc/_rfc7516/models.py 204-207, joserfc/_rfc7518/jwe_encs.py 82); 117 the recipient "
                  "header check passes (203-206); 120 check_header passes (joserfc/_rfc7516/registry.py 97-111); "
                  "123 get_alg(\"dir\") passes (recommended, joserfc/_rfc7518/jwe_algs.py 42); 124 "
                  "decrypt_recipient: 244 direct_mode is true, since dir sets no key size (joserfc/_rfc7516/"
                  "models.py 238, 246-248; joserfc/_rfc7518/jwe_algs.py 39-51); 248 recipient.encrypted_key is not "
                  "empty; 249 raise. The handler at joserfc/_rfc7516/message.py 126 catches it (a JoseError, "
                  "joserfc/errors.py 178-180), 127 verify_all_recipients is true by default "
                  "(joserfc/_rfc7516/registry.py 74, 84), 128 raises the same object again, and perform_decrypt "
                  "(99-103) catches only InvalidExchangeKeyError.",
        "source_lines": "joserfc/jwe.py 96-137; joserfc/_rfc7516/compact.py 36-77; joserfc/jwk.py 63-103; "
                        "joserfc/_rfc7517/models.py 205-222; joserfc/_rfc7516/message.py 99-155, 203-206, 242-285; "
                        "joserfc/_rfc7516/registry.py 48-111, 154-196; joserfc/_rfc7516/models.py 204-207, 234-262; "
                        "joserfc/_rfc7518/jwe_algs.py 39-51; joserfc/_rfc7518/jwe_encs.py 79-117; "
                        "joserfc/registry.py 182-230; joserfc/errors.py 7-20, 178-180",
    },
    17: {
        "result": "not reached",
        "entry_point": "none reaches the check; the closest inputs go through jwe.decrypt_compact "
                       "(joserfc/jwe.py:96)",
        "settings": "input: key ECKey (P-256), no setting differs from its default; input-b: the key given as a "
                    "JWK dict of the same key without kty, no other setting",
        "input": "input: ECDH-ES + A128GCM compact JWE for the key whose epk header has no kty member; input-b: "
                 "the well-formed token with the key as a JWK dict without kty; controls: the well-formed token "
                 "decrypts; a direct call of KeySet.import_key_set and a key callable that calls it both fire "
                 "the check (calls that section 4.4 excludes as inputs)",
        "reason": "JWKRegistry.import_key (joserfc/_keys.py 55-79) is called at 2 places of the package: "
                  "joserfc/jwk.py:162, in the module function jwk.import_key (126-162), and joserfc/_keys.py:178, "
                  "in KeySet.import_key_set (169-185), through registry_cls = JWKRegistry (115). No function of "
                  "the package calls jwk.import_key or KeySet.import_key_set, and neither has the name of an entry "
                  "point: in the package, the other references to the name import_key are definitions "
                  "(joserfc/jwk.py 107, 111, 115, 119, 123, 126; joserfc/_rfc7517/models.py 270; "
                  "joserfc/_rfc7518/ec_key.py 153, oct_key.py 79, rsa_key.py 137; joserfc/_rfc8037/okp_key.py "
                  "159), calls on a key class (joserfc/_keys.py 79; joserfc/jwk.py 151, 156; super() at "
                  "joserfc/_rfc7518/ec_key.py 163, oct_key.py 85, rsa_key.py 147 and joserfc/_rfc8037/okp_key.py "
                  "181), docstrings (joserfc/_keys.py 45; joserfc/jwe.py 183; joserfc/jws.py 334), a comment "
                  "(joserfc/_rfc7518/jws_algs.py 68), a string of __all__ (joserfc/jwk.py 43) and the 2 calls "
                  "described next; the name import_key_set occurs only at its definition (joserfc/_keys.py 170); "
                  "and the getattr calls of the package (joserfc/_rfc7518/jwe_algs.py 259, jwe_encs.py 41, "
                  "jws_algs.py 61, 92, 143; joserfc/_rfc7519/claims.py 102) select hash functions and claim "
                  "validators. The 2 remaining calls, joserfc/_rfc7518/jwe_algs.py:225 (ECDH-ES) and "
                  "joserfc/drafts/jwe_ecdh_1pu.py:95 (ECDH-1PU, whose register_ecdh_1pu, 110, the package never "
                  "calls), import the epk header of the token with the class of the caller's key "
                  "(recipient_key.import_key). That key comes from guess_key: an OctKey, RSAKey, ECKey or OKPKey "
                  "(joserfc/jwk.py 82-83) or a key of a KeySet of the caller (84-101); anything else raises "
                  "ValueError (103). check_key_type (joserfc/_rfc7518/jwe_algs.py 224; joserfc/_rfc7516/models.py "
                  "250-252) lets only the key types EC and OKP pass (jwe_algs.py 185), that is ECKey and OKPKey "
                  "(joserfc/_rfc7518/ec_key.py 111; joserfc/_rfc8037/okp_key.py 117), whose import_key "
                  "(joserfc/_rfc7518/ec_key.py 152-164; joserfc/_rfc8037/okp_key.py 158-182) goes through super() "
                  "to BaseKey.import_key (joserfc/_rfc7517/models.py 269-282); the classes between them (CurveKey "
                  "at 337, AsymmetricKey at 317) define no import_key. The epk is a dict there, since check_header "
                  "at joserfc/_rfc7516/message.py:120 checks it with is_jwk (joserfc/_rfc7518/jwe_algs.py 187; "
                  "joserfc/registry.py 43-45, 71, 83, 189-197); BaseKey.import_key checks a dict with "
                  "validate_dict_key (276-277, 263-267) and raises KeyParameterError at "
                  "joserfc/_rfc7517/models.py:61 when kty is missing (kty is required, joserfc/registry.py:143). "
                  "No class of the package derives from JWKRegistry (defined at joserfc/_keys.py:32; no class "
                  "statement names it as a base). The 2 closest inputs stop at those guards (input at "
                  "joserfc/_rfc7517/models.py:61, input-b at joserfc/jwk.py:103), with no line of joserfc/_keys.py "
                  "executed. Line 70 runs only when code of the caller calls JWKRegistry.import_key, "
                  "jwk.import_key or KeySet.import_key_set with a dict without kty: a direct call "
                  "(control-import-key-set) or a call in a key callable given to decrypt_compact "
                  "(control-key-callable; joserfc/jwk.py 59-60, 77-78) executes it, and MissingKeyTypeError "
                  "reaches the caller, since joserfc/_keys.py:179 catches only InvalidKeyTypeError, of which "
                  "MissingKeyTypeError is no subclass (joserfc/errors.py 46-51). Section 4.4 excludes such a call "
                  "as an input (no other function of the package is called directly). The toolkit counts the "
                  "check reachable because the attribute name import_key at joserfc/_rfc7518/jwe_algs.py:225 "
                  "stands for every definition of that name, JWKRegistry.import_key among them (name-paths.txt).",
        "source_lines": "joserfc/_keys.py 29-200; joserfc/jwk.py 28-162; joserfc/jwe.py 96-137, 165-192, "
                        "250-278; joserfc/jws.py 324-340; joserfc/_rfc7516/message.py 99-155, 242-285; "
                        "joserfc/_rfc7516/registry.py 97-111; joserfc/_rfc7516/models.py 234-262; "
                        "joserfc/_rfc7518/jwe_algs.py 184-227, 243-260; joserfc/_rfc7518/ec_key.py 108-166; "
                        "joserfc/_rfc7518/oct_key.py 69-87; joserfc/_rfc7518/rsa_key.py 103-104, 134-149; "
                        "joserfc/_rfc7518/jws_algs.py 64-72; joserfc/_rfc8037/okp_key.py 112-183; "
                        "joserfc/_rfc7517/models.py 55-85, 263-284, 295, 317, 337; joserfc/_rfc7518/derive_key.py "
                        "1-54; joserfc/_rfc7519/claims.py 98-104; joserfc/registry.py 43-45, 68-112, 136-146, "
                        "182-230; joserfc/drafts/jwe_ecdh_1pu.py 1-30, 84-116; joserfc/errors.py 1-60; a scan of "
                        "the 55 Python files of the package for import_key, import_key_set, getattr, JWKRegistry, "
                        "registry_cls and the bases of every class statement",
    },
    18: {
        "result": "reached",
        "entry_point": "jwe.decrypt_compact (joserfc/jwe.py:96)",
        "settings": f"key: OctKey of a 16-byte key; {DEFAULTS}",
        "input": "compact JWE {\"alg\":\"dir\",\"enc\":\"A128GCM\"} of a 49153-byte plaintext sealed with the key: "
                 "a ciphertext segment of 65538 characters in a token of 65619; control: a 49152-byte plaintext "
                 "(segment of 65536 characters) decrypts",
        "reason": "The raise statement at joserfc/_rfc7516/registry.py:140 executed and its RAISE event is a firing "
                  "by the rule of the recorder; the exception that reaches the caller is the object raised there. "
                  "On the way: joserfc/jwe.py 123-126 the default registry; 128 extract_compact: "
                  "joserfc/_rfc7516/compact.py 37 validate_compact_value_size passes (65619 characters; the "
                  "maximum is 1024 + 1024 + 64 + 65536 + 64 = 67712, joserfc/_rfc7516/registry.py 56-64, "
                  "113-122); 39-41 5 segments; 44-46 the protected header (39 characters), the encrypted key (0) "
                  "and the initialization vector (16) pass (registry.py 124-136); 47 "
                  "validate_ciphertext_size(ciphertext_segment): 139 the segment has 65538 characters, more than "
                  "max_ciphertext_length 65536 (registry.py 62); 140 raise. The limit applies to the base64url "
                  "segment, not to the decoded ciphertext (49153 bytes), although the comment at registry.py 61 "
                  "reads \"max ciphertext's size in bytes\"; the JSON serializations reach the same line through "
                  "joserfc/_rfc7516/json.py:117. No handler lies between registry.py 140 and the caller "
                  "(compact.py 47 comes before the try at 49, and decrypt_compact has none).",
        "source_lines": "joserfc/jwe.py 96-137; joserfc/_rfc7516/compact.py 36-77; joserfc/_rfc7516/registry.py "
                        "55-68, 113-152; joserfc/_rfc7516/json.py 107-122; joserfc/errors.py 7-20, 163-167",
    },
    19: {
        "result": "reached",
        "entry_point": "jwe.decrypt_compact (joserfc/jwe.py:96)",
        "settings": f"key: OctKey of a 32-byte key; {DEFAULTS}",
        "input": "compact JWE {\"alg\":\"dir\",\"enc\":\"XC20P\"} sealed with the key (XChaCha20-Poly1305 of the "
                 "pycryptodome of the environment, 24-byte nonce); XC20P is not registered by default",
        "reason": "The raise statement at joserfc/_rfc7516/registry.py:186 executed and its RAISE event is a firing "
                  "by the rule of the recorder; the exception that reaches the caller is the object raised there. "
                  "On the way: joserfc/jwe.py 123-126 the default registry; 128 extract_compact passes (sizes, a "
                  "header with alg and enc); 131-132 the key is accepted; 136 perform_decrypt -> "
                  "joserfc/_rfc7516/message.py 101 -> 107 registry.get_enc(\"XC20P\") -> "
                  "joserfc/_rfc7516/registry.py 171-172 -> 185: XC20P is not in the enc registry, since the package "
                  "defines it only in joserfc/drafts/jwe_chacha20.py 34 and never calls "
                  "register_chacha20_poly1305 (39-41), while setup_jwe_algorithms (joserfc/jwa.py 93-102, called "
                  "at joserfc/jwe.py:49) registers the enc models of joserfc/_rfc7518/jwe_encs.py 110-117 "
                  "(joserfc/jwa.py 22-23, 98-99); 186 raise. Line 107 lies outside the handler of "
                  "joserfc/_rfc7516/message.py 118-128, and perform_decrypt (99-103) catches only "
                  "InvalidExchangeKeyError.",
        "source_lines": "joserfc/jwe.py 44-52, 96-137; joserfc/_rfc7516/compact.py 36-77; "
                        "joserfc/_rfc7516/message.py 99-110; joserfc/_rfc7516/registry.py 48-52, 91-95, 166-193; "
                        "joserfc/jwa.py 18-26, 90-102; joserfc/_rfc7518/jwe_encs.py 79-117; "
                        "joserfc/drafts/jwe_chacha20.py 1-41; joserfc/drafts/__init__.py (0 bytes); "
                        "joserfc/errors.py 7-20, 91-96",
    },
    20: {
        "result": "reached",
        "entry_point": "jwe.decrypt_compact (joserfc/jwe.py:96)",
        "settings": "algorithms=[\"dir\", \"A256GCM\"] (default None, documented at joserfc/jwe.py:118); key: "
                    "OctKey of a 16-byte key; registry and sender_key not given",
        "input": "compact JWE {\"alg\":\"dir\",\"enc\":\"A128GCM\"} sealed with the key; control: the same token "
                 "decrypts with the default settings",
        "reason": "The raise statement at joserfc/_rfc7516/registry.py:190 executed and its RAISE event is a firing "
                  "by the rule of the recorder; the exception that reaches the caller is the object raised there. "
                  "On the way: joserfc/jwe.py 123-124 algorithms is given, so a new JWERegistry holds it as "
                  "allowed (joserfc/_rfc7516/registry.py 83), with the models registered on the class (48-52, "
                  "91-95); 128 extract_compact passes; 131-132 the key is accepted; 136 perform_decrypt -> "
                  "joserfc/_rfc7516/message.py 101 -> 107 get_enc(\"A128GCM\") -> registry.py 171-172 -> 185 "
                  "A128GCM is registered -> 188 allowed is set -> 189 A128GCM is not in it -> 190 raise. Line 107 "
                  "lies outside the handler of joserfc/_rfc7516/message.py 118-128, and perform_decrypt (99-103) "
                  "catches only InvalidExchangeKeyError. Control: with the default settings (allowed is None, "
                  "191-193) the same token decrypts.",
        "source_lines": "joserfc/jwe.py 96-137; joserfc/_rfc7516/compact.py 36-77; joserfc/_rfc7516/message.py "
                        "99-110; joserfc/_rfc7516/registry.py 48-52, 70-95, 166-193; joserfc/errors.py 7-20, 91-96",
    },
}


def describe_exception(raised: dict) -> str:
    site = raised["site"]
    where = f"{site['file']}:{site['line']}"
    check = f" (a raise line of the check {site['check']})" if site["check"] else ""
    return f"{raised['class']} (\"{raised['message']}\"), raised at {where}{check}"


def main() -> int:
    with SAMPLE.open(encoding="utf-8", newline="") as handle:
        sample = list(csv.DictReader(handle))
    out_rows = []
    for row, fields in ROWS.items():
        entry = sample[row - 1]
        record = json.loads((HERE / f"{row}.json").read_text(encoding="utf-8"))
        if entry["library"] != "joserfc" or record["check"] != entry["check"] or record["row"] != row:
            raise SystemExit(f"row {row}: the record is not the sampled check")
        if not record["all_runs_clean"]:
            raise SystemExit(f"row {row}: a run failed or changed the copy")
        reached = record["fired_by_an_input"]
        if (fields["result"] == "reached") != reached:
            raise SystemExit(f"row {row}: the record says fired_by_an_input={reached}")
        for case in record["cases"]:
            if not case["runs_identical"]:
                raise SystemExit(f"row {row}: the 2 runs of {case['name']} differ")
        inputs = [c for c in record["cases"] if c["kind"] == "input"]
        parts = []
        for case in inputs:
            outcome = case["runs"][0]["inner"]["outcome"]
            if "raised" not in outcome:
                raise SystemExit(f"row {row}: {case['name']} returned")
            text = describe_exception(outcome["raised"])
            if outcome["raised"]["is_the_object_raised_at_the_check"]:
                text += ", the object raised at the check"
            parts.append(text if len(inputs) == 1 else f"{case['name']}: {text}")
        if not reached:
            for case in inputs:
                inner = case["runs"][0]["inner"]
                if inner["target_raise_line_executed"] or inner["target_fired"]:
                    raise SystemExit(f"row {row}: {case['name']} executed the raise line")
                lines = inner["lines_executed"].get(record["file"], [])
                parts.append(f"{case['name']}: lines of {record['file']} executed: {len(lines)}")
        out_rows.append({
            "library": "joserfc", "check": entry["check"], "result": fields["result"],
            "entry_point": fields["entry_point"],
            "scripts": f"{PREFIX}/{row}.py, with {PREFIX}/reach_harness.py"
                       + (f"; {PREFIX}/name-paths.py" if row == 17 else ""),
            "settings": fields["settings"], "exception": "; ".join(parts), "reason": fields["reason"],
            "row": row, "input": fields["input"], "fired": FIRED[fields["result"]],
            "record": f"{PREFIX}/{row}.json", "source_lines": fields["source_lines"],
        })
    with (HERE / "reach.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"wrote {HERE / 'reach.csv'}: {len(out_rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())

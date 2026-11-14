#!/bin/sh
# Recount of the candidates whose exclusion or inclusion decides the selection,
# with the toolkit's own enumerators (survey.py). Static: nothing is run.
#
#   sh recount.sh CLONES > recounts.txt
#
# CLONES holds 1 clone per project, checked out at the tag named below.
# A rejection base is the label of 1 class of the package or a built-in class
# (reach/checks.py); a class that 2 modules define under 1 name is named with
# its module. The 2nd and 3rd lines of google-auth give the counts under the
# other readings of its rejection base (PROTOCOL.md, section 3).
set -eu
CLONES=$1
HERE=$(cd "$(dirname "$0")" && pwd)
TOOLKIT=$(dirname "$HERE")
survey() { python3 -I -B "$HERE/survey.py" "$TOOLKIT" "$@"; }
at() { printf '\n##### %s, tag %s, commit %s\n' "$1" "$2" "$(git -C "$CLONES/$1" -c safe.directory='*' rev-parse HEAD)"; }

at urllib3 2.8.0
survey "$CLONES/urllib3/src" urllib3 match_hostname,_match_hostname,assert_fingerprint,_assert_fingerprint CertificateError,SSLError ../test --blocks
at cryptography 50.0.2
survey "$CLONES/cryptography/src" cryptography decrypt,decrypt_at_time,extract_timestamp cryptography.fernet.InvalidToken,cryptography.hazmat.primitives.twofactor.InvalidToken ../tests --checks
at truststore v0.10.5
survey "$CLONES/truststore/src" truststore _verify_peercerts,_verify_peercerts_impl SSLError,SSLCertVerificationError ../tests --checks
at pyopenssl 26.4.0
survey "$CLONES/pyopenssl/src" OpenSSL verify_certificate,get_verified_chain X509StoreContextError,OpenSSL.crypto.Error,OpenSSL.SSL.Error ../tests --checks
at pynacl 1.6.2
survey "$CLONES/pynacl/src" nacl verify,decrypt,crypto_sign_open CryptoError ../tests --checks
at msal 1.39.0
survey "$CLONES/msal" msal obtain_token_by_auth_code_flow,acquire_token_by_auth_code_flow,decode_id_token,obtain_token_by_authorization_code,parse_auth_response ValueError,RuntimeError tests --blocks
at pyjwt 2.15.1
survey "$CLONES/pyjwt" jwt decode,decode_complete PyJWTError tests
at google-auth google-auth-v2.62.2
survey "$CLONES/google-auth/packages/google-auth" google decode ValueError tests,tests_async
survey "$CLONES/google-auth/packages/google-auth" google decode GoogleAuthError tests,tests_async
survey "$CLONES/google-auth/packages/google-auth" google decode ValueError,GoogleAuthError tests,tests_async
at oauthlib v4.0.1
survey "$CLONES/oauthlib" oauthlib validate_authorization_request,validate_token_request OAuth2Error tests
at authlib v1.9.5
survey "$CLONES/authlib" authlib decode,deserialize,deserialize_compact,deserialize_json,validate JoseError tests
at joserfc 1.8.0
survey "$CLONES/joserfc/src" joserfc decode,decrypt_compact,decrypt_json,deserialize_compact,deserialize_json,validate,validate_compact JoseError ../tests

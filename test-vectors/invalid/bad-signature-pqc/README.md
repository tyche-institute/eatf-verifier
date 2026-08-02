# Invalid ML-DSA-65 signature

Expected: `verify=false`, first failure `PQC_SIGNATURE_INVALID`.

The classical signature, canonical bytes, and timestamp remain intact. One bit
of `signature_pqc.sig` has been changed.

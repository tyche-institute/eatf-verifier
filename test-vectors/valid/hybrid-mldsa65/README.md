# Valid hybrid ML-DSA-65 package

Expected: `verify=true`, `pqc=true`.

The package carries RSA-4096 and ML-DSA-65 signatures over the same canonical
bytes. Its PQC key is encoded as RFC 9881 SubjectPublicKeyInfo with the
`id-ml-dsa-65` AlgorithmIdentifier and absent parameters.

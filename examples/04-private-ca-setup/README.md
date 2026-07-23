# Example 04 — private CA setup

Walks through creating a private CA, issuing an issuer certificate
under it, and configuring an `eatf-verify` invocation that trusts the
CA root.

```bash
# 1. Bootstrap the private root CA (out-of-band; openssl in this example)
openssl req -x509 -newkey rsa:4096 -nodes -days 3650 \
            -keyout ca.key -out ca.pem -subj "/CN=Example Operator Root CA"

# 2. Issue an EATF issuer certificate under the root
openssl req -new -newkey rsa:4096 -nodes -keyout issuer.key \
            -out issuer.csr -subj "/CN=Example Issuer 1"
openssl x509 -req -in issuer.csr -CA ca.pem -CAkey ca.key \
             -CAcreateserial -days 365 -out issuer.pem

# 3. Sign an AEP with the issuer key
eatf-sign --in records/ --key issuer.key --cert issuer.pem \
          --out action.aep

# 4. Verify against the root anchor
eatf-verify action.aep --issuer-anchor ca.pem
```

Stub. Runnable example lands in a 0.1.x point release.

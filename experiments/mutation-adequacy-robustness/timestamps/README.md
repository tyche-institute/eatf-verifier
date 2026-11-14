# Time stamps of the protocol commit

`protocol-commit.txt` names the commit that fixed `../PROTOCOL.md`, before any
script of this folder existed:

    708beeca2317261e5b653748b7990f36b42542ec

Its SHA-256 was sent to 2 independent time-stamping authorities (RFC 3161)
before the first script was written. Both tokens carry the time
2026-11-14 02:46:40 UTC.

| File | Authority |
|---|---|
| `protocol-commit.freetsa.tsr` | freetsa.org (`https://freetsa.org/tsr`) |
| `protocol-commit.digicert.tsr` | DigiCert (`http://timestamp.digicert.com`) |
| `freetsa-root.crt`, `freetsa-tsa.crt` | freetsa.org's root and signing certificates, as served on 2026-11-14 |

Verify, from this directory:

```sh
openssl ts -verify -data protocol-commit.txt -in protocol-commit.freetsa.tsr \
    -CAfile freetsa-root.crt -untrusted freetsa-tsa.crt
openssl ts -verify -data protocol-commit.txt -in protocol-commit.digicert.tsr \
    -CAfile /etc/ssl/certs/ca-certificates.crt
openssl ts -reply -in protocol-commit.digicert.tsr -text
```

The second command uses the system's trust store, which holds DigiCert's root.

What the tokens show: a text naming this commit existed at that time, and a
commit id covers the protocol's text and the history before it. What they do
not show: that nothing was run before the protocol was fixed. For this folder
that matters little, because all 4 analyses are post hoc and carry no
prediction.

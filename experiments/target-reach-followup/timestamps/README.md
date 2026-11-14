# Time stamps

## The protocol commit

`protocol-commit.txt` names the commit that fixed `../PROTOCOL.md` and
`../labels/INSTRUCTION.md`, before any reading pack was built, any label was
made by the instruction, any suite was traced or any tool mutant was made on
the 4 held-out libraries:

    ebcf76f12ab5199c26cbebb542a26695f28702c0

Its SHA-256 was sent to 2 independent time-stamping authorities (RFC 3161)
before the first reading pack of the 4 was built. Both tokens carry the time
2026-11-14 14:09:33 UTC.

| File | Authority |
|---|---|
| `protocol-commit.freetsa.tsr` | freetsa.org (`https://freetsa.org/tsr`) |
| `protocol-commit.digicert.tsr` | DigiCert (`http://timestamp.digicert.com`) |
| `freetsa-root.crt`, `freetsa-tsa.crt` | freetsa.org's root and signing certificates, as served on 2026-11-14 (the files of `../../target-reach/timestamps/`) |

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
commit id covers the protocol's text, the instruction of the readings, the
programs and the history before them. What they do not show: that nothing
was done on the 4 libraries before the protocol was fixed. Section 5 of the
protocol states what had been done on each of them, and the results of
`../../target-reach/` on them were known.

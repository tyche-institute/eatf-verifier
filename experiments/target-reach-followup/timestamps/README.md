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

## The commit of the labels

`readings-commit.txt` names the commit that holds the labels files of
readings A and B of the 4 libraries (`../labels/readings/<name>/A.tsv` and
`B.tsv`), as returned and after the check of form alone:

    eab1ea1589a5d8acb0f418d6c7baaa3b0f2a0ef4

Its SHA-256 was sent to the same 2 authorities before a labels file was
compared with a record, a target or the other reading. Both tokens carry the
time 2026-11-14 14:24:47 UTC.

| File | Authority |
|---|---|
| `readings-commit.freetsa.tsr` | freetsa.org |
| `readings-commit.digicert.tsr` | DigiCert |

Verify as above, with `readings-commit` in place of `protocol-commit`.

What the tokens show: the labels of the 2 readings existed in this form at
that time, and the analysis programs that compare them are those of the
history of this commit, with the 1 correction that `../DEVIATIONS.md`
describes. What they do not show: how a reading was made. `../PROTOCOL.md`,
section 4.1, states what a reading is given and what it is not given.

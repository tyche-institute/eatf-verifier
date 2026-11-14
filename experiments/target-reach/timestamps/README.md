# Time stamps

## The protocol commit

`protocol-commit.txt` names the commit that fixed `../PROTOCOL.md`, before any
target was computed, any test was run under the recorder or any check was
deleted on the 4 held-out libraries:

    b93e078770feeebbb1e9b7824f0d4a42f515b4e6

Its SHA-256 was sent to 2 independent time-stamping authorities (RFC 3161)
before the `targets` step ran on any of the 4. Both tokens carry the time
2026-11-14 09:22:14 UTC.

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
commit id covers the protocol's text, the toolkit, the definitions of the
subjects and the history before them. What they do not show: that nothing
was run on the 4 libraries before the protocol was fixed. Section 5 of the
protocol states what had been done on each of them.

## The commit of the targets

`targets-commit.txt` names the commit that added `targets.json` for the 4
held-out libraries, assigned by the rule before any of their tests was run
under the recorder and before any check was deleted:

    0a026ca9fc7e62155a0e2401ca7bb96dec4f1ac6

Its SHA-256 was sent to the same 2 authorities before the `baseline` step ran
on any of the 4. The tokens carry the times 2026-11-14 09:25:09 UTC
(freetsa.org) and 2026-11-14 09:25:10 UTC (DigiCert).

| File | Authority |
|---|---|
| `targets-commit.freetsa.tsr` | freetsa.org |
| `targets-commit.digicert.tsr` | DigiCert |

Verify as above, with `targets-commit` in place of `protocol-commit`.

What these tokens show: the targets of the 4 libraries existed, as committed,
at that time. With the first pair they bound the time in which the targets
were computed: after 09:22:14 UTC and before 09:25:10 UTC. What they do not
show: that no recorder run preceded them; the records of the runs carry
their own start times, which are later.

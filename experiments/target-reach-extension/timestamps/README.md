# Time stamps

## The protocol commit

`protocol-commit.txt` names the commit that fixed `../PROTOCOL.md`, the
definitions of the 7 screened libraries, the sample of 20 checks and the
tools, before any test of a subject ran under the recorder or in a whole
suite, any check was deleted or any header was decoded:

    0796d80a8b34fe2915f48fd92c1485735b2a6fec

Its SHA-256 was sent to 2 independent time-stamping authorities (RFC 3161)
before any step of section 6 of the protocol ran. Both tokens carry the time
2026-11-17 15:27:56 UTC.

| File | Authority |
|---|---|
| `protocol-commit.freetsa.tsr` | freetsa.org (`https://freetsa.org/tsr`) |
| `protocol-commit.digicert.tsr` | DigiCert (`http://timestamp.digicert.com`) |
| `freetsa-root.crt`, `freetsa-tsa.crt` | freetsa.org's root and signing certificates, copied from `../../target-reach/timestamps/` |

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
commit id covers the protocol's text, the definitions, the sample, the tools
and the history before them. What they do not show: that nothing was run on
the subjects before the protocol was fixed. Section 5 of the protocol states
what had been done before the commit, and `../preparation/tools/` and the
`PREPARATION.md` of each screened library record it.

## The results commit

`results-commit.txt` names the commit that holds the outputs of steps 3 to 6
of section 6 of the protocol, the reading of the 20 sampled checks,
`../DEVIATIONS.md` and the logs of the commands (step 7):

    cc0d4c30f10ee0b559ebb81f7cb39a12078443b7

Its SHA-256 was sent to the same 2 authorities after the commit was pushed.
Both tokens carry the time 2026-11-17 16:24:27 UTC.

| File | Authority |
|---|---|
| `results-commit.freetsa.tsr` | freetsa.org (`https://freetsa.org/tsr`) |
| `results-commit.digicert.tsr` | DigiCert (`http://timestamp.digicert.com`) |

Verify with the 3 commands above, with `results-commit` in place of
`protocol-commit`. The tokens show that the results existed at that time, in
the commit that they name; with the tokens of the protocol commit, they bound
the time of the runs from both sides.

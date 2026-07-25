# Example 02: RFC 3161 timestamp verification

```bash
examples/02-with-rfc3161-timestamp/run.sh
```

The script extracts the committed `TimeStampResp`, prints its TSTInfo with
OpenSSL, verifies it against the recorded canonical SHA-256 digest and the
test-only TSA certificate, then runs both EATF verifiers. No TSA is contacted.

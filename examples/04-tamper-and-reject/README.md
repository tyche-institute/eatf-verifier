# Example 04: tamper and reject

```bash
examples/04-tamper-and-reject/run.sh
```

The demonstrator flips one byte in `canonical.bin` in a temporary copy.
TypeScript and Python must both return a non-zero exit status. The source
package is never modified.

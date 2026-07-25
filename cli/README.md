# EATF command-line tools

| Tool | Purpose |
|---|---|
| `eatf-sign` | Create an AEP from payload, metadata, keys, scope, and an out-of-band RFC 3161 response. |
| `eatf-inspect` | Print package structure and selected metadata without making authenticity claims. |
| `eatf-verify` | Run the TypeScript verification pipeline on files, directories, or the conformance tree. |
| `eatf-verify-py` | Run the same verdict contract through the Python implementation. |

Install all commands from the repository root:

```bash
bash bin/setup.sh
export PATH="$PWD/bin:$PATH"
```

All four operate without runtime network calls. `eatf-sign` requires a
timestamp response obtained out of band; the verifier never downloads keys or
trust material.

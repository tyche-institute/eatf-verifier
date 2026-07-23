# `mcp-tools-call-denied-policy/`

**Expected:** `verify=true`, `overtReceipt.policy.decision == "deny"`.

A well-formed AEP for an MCP `tools/call` invocation that was
**denied** by the deployment's policy. The AEP itself is
cryptographically valid — the policy denial is part of the recorded
outcome, not a verification failure. This vector exercises the
distinction between "package is authentic" and "the underlying call
succeeded", which are independent properties.

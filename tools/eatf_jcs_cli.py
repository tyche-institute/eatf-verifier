"""Adapter: the EATF Python JCS function behind the a2a-jcs-v01 verifier contract.

Contract (agent-evidence-vectors docs/reference/corpus-readers.md):
  <verifier> rfc8785 <input.json>   exit 0 and {"canonical_utf8_hex": ...} on stdout,
                                    exit 1 when the input has no canonical form.
The canonicalizer is eatf_verifier.canonical.jcs, imported from a local clone given
by EATF_LIB_PYTHON. Nothing of ours is mixed in.
"""
import json
import os
import sys

sys.path.insert(0, os.environ["EATF_LIB_PYTHON"])
from eatf_verifier.canonical import jcs  # noqa: E402


def main(argv):
    if len(argv) != 3 or argv[1] not in ("rfc8785", "card-signing-input"):
        print("usage: eatf_jcs_cli.py rfc8785 <input.json>", file=sys.stderr)
        return 2
    raw = open(argv[2], "rb").read()
    try:
        value = json.loads(raw.decode("utf-8"), parse_constant=_refuse)
        out = jcs(value)
    except Exception as exc:  # any refusal means: no canonical form
        print(type(exc).__name__, file=sys.stderr)
        return 1
    print(json.dumps({"canonical_utf8_hex": out.hex()}))
    return 0


def _refuse(token):
    raise ValueError(token)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

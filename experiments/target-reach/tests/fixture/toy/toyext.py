"""A dependency outside the verifier package."""


def mac(key):
    if key == "secret2":
        raise LookupError("key revoked upstream")
    if key == "secret3":
        from toyverify.errors import PolicyError

        raise PolicyError("key revoked")
    return "sig-" + key

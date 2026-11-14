from .errors import KeyProblem

KEYS = {"k1": "secret1", "k2": "secret2", "k3": "secret3"}


def load_key(name):
    if name not in KEYS:
        raise KeyProblem("unknown key")
    return KEYS[name]

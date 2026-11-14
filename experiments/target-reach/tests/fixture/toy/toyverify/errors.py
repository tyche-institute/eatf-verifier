class ToyError(Exception):
    pass


class FormatError(ToyError):
    pass


class PolicyError(ToyError):
    pass


class KeyProblem(ToyError):
    pass


class ClaimMissing(PolicyError):
    def __init__(self, claim):
        self.claim = claim

    def __str__(self):
        return f"missing claim {self.claim!r}"

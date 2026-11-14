class TraceError(Exception):
    pass


class BadSig(TraceError):
    pass


class Expired(TraceError):
    pass


class BadPart(TraceError):
    pass


class TooDeep(TraceError):
    pass


class BadBox(TraceError):
    pass

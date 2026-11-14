from .errors import BadPart, Expired, TraceError


def check_expiry(token):
    if "expired" in token:
        raise Expired("token expired")


def lazy_parts(token):
    for part in token.split("."):
        if part == "stop":
            raise BadPart("lazy stop")
        yield part


def threaded_check(token, sink):
    if "thread" in token:
        sink.append(TraceError("thread saw the token"))


def util(token):
    return len(token)


for _name in ("one",):
    def looped(token):
        return token

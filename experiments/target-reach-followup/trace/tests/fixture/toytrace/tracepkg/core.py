import asyncio
import threading

from .errors import BadBox, BadPart, BadSig, TooDeep, TraceError
from .helpers import check_expiry as _expiry
from .helpers import lazy_parts, threaded_check, util


class Checks:
    def check_sig(self, token):
        if "badsig" in token:
            raise BadSig("bad signature")

    def check_none(self, token):
        return None


class Box:
    def __init__(self):
        self._v = 0

    @property
    def value(self):
        return self._v

    @value.setter
    def value(self, v):
        if v < 0:
            raise BadBox("negative box")
        self._v = v


def parts(token):
    for part in token.split("."):
        if part == "":
            raise BadPart("empty part")
        yield part


def walk(n):
    if n > 3:
        raise TooDeep("too deep")
    if n > 0:
        walk(n - 1)


async def _acheck(token):
    await _ainner(token)


async def _ainner(token):
    if "async" in token:
        raise TraceError("async rejected")


def decode(token, depth=0):
    if not isinstance(token, str):
        raise TraceError("token must be a string")
    util(token)
    head = token.split(".")[0]
    handler = getattr(Checks(), "check_" + head)
    handler(token)
    _expiry(token)

    def inner(t):
        if t.endswith("!"):
            raise TraceError("bang")

    inner(token)
    ordered = sorted(parts(token), key=lambda p: len(p))
    walk(len(ordered))
    box = Box()
    box.value = 1 if "negbox" not in token else -1
    sink = []
    worker = threading.Thread(target=threaded_check, args=(token, sink))
    worker.start()
    worker.join()
    asyncio.run(_acheck(token))
    if token.startswith("none.lazy"):
        return lazy_parts(token)
    return ordered


class Codec:
    def decode(self, token):
        return util(token)

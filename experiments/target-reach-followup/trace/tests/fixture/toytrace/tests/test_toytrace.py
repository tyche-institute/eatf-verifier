import pytest

from tracepkg import decode
from tracepkg.core import Codec
from tracepkg.errors import BadBox, BadPart, BadSig, Expired, TooDeep, TraceError
from tracepkg.helpers import util


def test_ok():
    assert decode("none.a.b") == ["a", "b", "none"]


def test_bad_signature():
    with pytest.raises(BadSig):
        decode("sig.badsig")


def test_expired_token():
    with pytest.raises(Expired):
        decode("none.expired")


def test_empty_part():
    with pytest.raises(BadPart):
        decode("none..x")


def test_too_deep():
    with pytest.raises(TooDeep):
        decode("none.a.b.c.d")


def test_negative_box():
    with pytest.raises(BadBox):
        decode("none.negbox")


def test_async_rejected():
    with pytest.raises(TraceError):
        decode("none.async")


def test_lazy_outside():
    it = decode("none.lazy.stop")
    with pytest.raises(BadPart):
        list(it)


def test_unwinding_then_direct_call():
    with pytest.raises(TraceError):
        decode("none.bang!")
    assert util("abc") == 3


def test_codec_own_name():
    assert Codec().decode("ab") == 2


def test_thread():
    assert decode("none.thread") == ["none", "thread"]

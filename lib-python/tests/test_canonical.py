"""Cross-language RFC 8785 boundary tests shared with the TypeScript port."""

from __future__ import annotations

import pytest
import rfc8785

from eatf_verifier.canonical import jcs


def test_ecmascript_number_serialization() -> None:
    value = [333333333.33333329, 4.5, 2e-3, 1e-27]
    assert jcs(value) == b"[333333333.3333333,4.5,0.002,1e-27]"


def test_utf16_member_order() -> None:
    value = {
        "€": "euro",
        "\r": "cr",
        "דּ": "hebrew",
        "1": "one",
        "😀": "emoji",
        "\u0080": "control",
        "ö": "o-umlaut",
    }
    assert jcs(value).decode("utf-8") == (
        '{"\\r":"cr","1":"one","\u0080":"control","ö":"o-umlaut",'
        '"€":"euro","😀":"emoji","דּ":"hebrew"}'
    )


def test_rejects_values_outside_the_shared_ijson_domain() -> None:
    with pytest.raises(rfc8785.IntegerDomainError):
        jcs({"unsafe": 9007199254740992})
    with pytest.raises(rfc8785.FloatDomainError):
        jcs({"unsafe": 1e30})
    with pytest.raises(rfc8785.CanonicalizationError):
        jcs({"surrogate": "\ud800"})

import math
from pathlib import Path

import pytest

from vat_number_validator._php_json import decode


@pytest.mark.parametrize("body", [b"\xff", b"\xef\xbb\xbf{}", b"", b"NaN", b"Infinity", b"-Infinity"])
def test_rejects_invalid_json(body: bytes) -> None:
    with pytest.raises((ValueError, UnicodeDecodeError)):
        decode(body)


def test_rejects_html() -> None:
    with pytest.raises(ValueError, match="Expecting value"):
        decode(Path("tests/fixtures/vies/http404-not-found.html").read_bytes())


@pytest.mark.parametrize("outer_object", [False, True])
@pytest.mark.parametrize("depth", [511, 512])
def test_php_depth_limit(depth: int, outer_object: bool) -> None:
    arrays = depth - int(outer_object)
    body = b"[" * arrays + b"0" + b"]" * arrays
    if outer_object:
        body = b'{"a":' + body + b"}"
    if depth == 512:
        with pytest.raises(ValueError, match="Maximum stack depth exceeded"):
            decode(body)
    else:
        assert isinstance(decode(body), (dict, list))


@pytest.mark.parametrize(
    "body",
    [
        rb'"\ud800"',
        rb'"\udfff"',
        rb'{"\ud800":1}',
        rb'{"x":"\ud800","x":"ok"}',
        rb'{"x":{"bad":"\ud800"},"x":null}',
    ],
)
def test_rejects_surrogates_even_when_overwritten(body: bytes) -> None:
    with pytest.raises(ValueError, match="Single unpaired UTF-16 surrogate in unicode escape"):
        decode(body)


def test_assoc_keys_duplicates_arrays_and_surrogate_pairs() -> None:
    assert decode(rb'{"\u0000a":1,"x":1,"x":[2,{"z":3}],"emoji":"\ud83d\ude00"}') == {
        "\0a": 1,
        "x": [2, {"z": 3}],
        "emoji": "😀",
    }


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("9223372036854775807", 9223372036854775807),
        ("-9223372036854775808", -9223372036854775808),
        ("9223372036854775808", float(9223372036854775808)),
        ("-9223372036854775809", float(-9223372036854775809)),
        ("10000000000000000000", 1e19),
    ],
)
def test_php_integer_range(token: str, expected: int | float) -> None:
    result = decode(token.encode())
    assert result == expected
    assert type(result) is type(expected)


def test_huge_integer_avoids_python_digit_limit() -> None:
    result = decode(b"9" * 5000)
    assert isinstance(result, float)
    assert math.isinf(result)


def test_valid_scalar_values() -> None:
    assert decode(b"true") is True
    assert decode(b"null") is None
    assert decode(b"1.25") == 1.25


# Messages verified with PHP json_decode via stdin, loading the reference autoloader.
_DEEP_ARRAY = b"[" * 511 + b"0" + b"]" * 511
_SURROGATE_ERROR = "Single unpaired UTF-16 surrogate in unicode escape"
_DEPTH_ERROR = "Maximum stack depth exceeded"


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (rb'{"x":"\ud800","y":' + _DEEP_ARRAY + b"}", _SURROGATE_ERROR),
        (b'{"y":' + _DEEP_ARRAY + rb',"x":"\ud800"}', _DEPTH_ERROR),
        (rb'{"\ud800":' + _DEEP_ARRAY + b"}", _SURROGATE_ERROR),
        (b'{"x":' + _DEEP_ARRAY + rb',"\ud800":0}', _DEPTH_ERROR),
        (rb'["\ud800",' + _DEEP_ARRAY + b"]", _SURROGATE_ERROR),
        (b"[" + _DEEP_ARRAY + rb',"\ud800"]', _DEPTH_ERROR),
        (rb'{"x":"\ud800","x":' + _DEEP_ARRAY + b"}", _SURROGATE_ERROR),
        (b'{"x":' + _DEEP_ARRAY + rb',"x":"\ud800"}', _DEPTH_ERROR),
    ],
    ids=[
        "value-before-depth",
        "depth-before-value",
        "key-before-its-value",
        "value-before-later-key",
        "array-surrogate-first",
        "array-depth-first",
        "overwritten-surrogate",
        "overwritten-depth",
    ],
)
def test_emulated_errors_follow_document_order(body: bytes, message: str) -> None:
    with pytest.raises(ValueError, match=message) as caught:
        decode(body)
    assert str(caught.value) == message

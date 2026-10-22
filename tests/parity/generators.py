"""Unfiltered deterministic inputs: never discard a case based on either validator's verdict."""

import json
import random
import string
from functools import cache
from typing import Any

from tests.cases import INVALID_NUMBERS, VALID_NUMBERS

SEED = 20261022
DIGITS = string.digits
LETTERS = string.ascii_uppercase
# Independent transcription of PHP country lengths, including legacy BE nine digits.
LENGTHS = {
    "AT": (9,),
    "BE": (9, 10),
    "BG": (9, 10),
    "CY": (9,),
    "CZ": (8, 9, 10),
    "DE": (9,),
    "DK": (8,),
    "EE": (9,),
    "EL": (9,),
    "ES": (9,),
    "FI": (8,),
    "FR": (11,),
    "HR": (11,),
    "HU": (8,),
    "IE": (8, 9),
    "IT": (11,),
    "LT": (9, 12),
    "LU": (8,),
    "LV": (11,),
    "MT": (8,),
    "NL": (12,),
    "PL": (10,),
    "PT": (9,),
    "RO": tuple(range(2, 11)),
    "SE": (12,),
    "SI": (8,),
    "SK": (10,),
    "XI": (5, 9, 12),
    "GB": (5, 9, 12),
    "CHE": (9,),
    "NO": (9,),
}
SEPARATORS = tuple(
    "\t\n\v\f\r\x85 .-\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007"
    "\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"
)


def random_text(rng: random.Random, alphabet: str, length: int) -> str:
    return "".join(rng.choices(alphabet, k=length))


def national(rng: random.Random, prefix: str, length: int, variant: int) -> str:
    digits = random_text(rng, DIGITS, length)
    if variant % 3 == 0:
        alphabet = DIGITS + (LETTERS + "+*" if prefix in ("FR", "IE", "NL", "ES", "CY", "AT", "GB", "XI") else "")
        return random_text(rng, alphabet, length)
    if prefix == "AT":
        return "U" + digits[1:]
    if prefix == "CY":
        return digits[:-1] + rng.choice(LETTERS)
    if prefix == "FR":
        return random_text(rng, DIGITS + "ABCDEFGHJKLMNPQRSTUVWXYZ", 2) + digits[2:]
    if prefix == "ES":
        family = variant % 4
        if family == 0:  # DNI: eight digits and a control letter.
            return digits[:-1] + rng.choice(LETTERS)
        first = rng.choice(("XYZ", "KLM", "ABCDEFGHJNPQRSUVW")[family - 1])
        control = DIGITS + "JABCDEFGHI" if family == 3 else LETTERS
        return first + digits[1:-1] + rng.choice(control)
    if prefix == "IE":
        if length == 8 and variant % 2:
            return digits[0] + rng.choice(LETTERS + "+*") + digits[2:-1] + rng.choice(LETTERS[:23])
        if length == 9:
            return digits[:-2] + rng.choice(LETTERS[:23]) + rng.choice(LETTERS[:9])
        return digits[:-1] + rng.choice(LETTERS[:23])
    if prefix == "EE":
        return "10" + digits[2:]
    if prefix == "IT":
        office = rng.choice((*range(1, 101), 120, 121, 888, 999))
        return digits[:-4] + f"{office:03d}" + digits[-1:]
    if prefix == "LT":
        return digits[:-2] + "1" + digits[-1:]
    if prefix == "NL":
        if variant % 2:
            return digits[:-3] + "B" + digits[-2:]
        return random_text(rng, DIGITS + LETTERS + "+*", length - 2) + digits[-2:]
    if prefix in ("GB", "XI") and length == 5:
        return rng.choice(("GD", "HA")) + digits[2:]
    return digits


@cache
def families() -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(SEED)
    result: dict[str, list[dict[str, Any]]] = {}
    vectors = [row[0] for row in VALID_NUMBERS.values()] + [row[0] for row in INVALID_NUMBERS.values()]
    mutations: list[dict[str, Any]] = []
    for index in range(4000):
        value = rng.choice(vectors)
        position = rng.randrange(len(value) + 1)
        mode = index % 8
        if mode == 0:
            value = value[:position] + rng.choice(SEPARATORS) + value[position:]
        elif mode == 1:
            value = (
                value[:position]
                + rng.choice(("/", "_", "\0", "\x1c", "\u180e", "\u200b", "ß", "\u0131", "\u017f", "ﬀ"))
                + value[position:]
            )
        elif mode == 2:
            value = "".join(c.lower() if rng.choice((True, False)) else c for c in value)
        elif mode == 3:
            value = value.translate(str.maketrans(DIGITS, "".join(chr(0xFF10 + i) for i in range(10))))
        elif mode == 4:
            value = rng.choice(tuple(LENGTHS)) + value[2:]
        elif mode == 5:
            value = rng.choice(("GR", "EL")) + rng.choice(("094014201", "09401924"))
        elif mode == 6:
            value = rng.choice(("CH", "CHE")) + "116281710" + rng.choice(("", "MWST", "TVA", "IVA"))
        else:
            value = "NO974760673" + rng.choice(("", "MVA", "mva", "IVA"))
        mutations.append({"op": "parse", "input": value})
    result["mutations"] = mutations
    parts = []
    for prefix, lengths in LENGTHS.items():
        for length in sorted({n + offset for n in lengths for offset in (-1, 0, 1)}):
            for variant in range(200):
                parts.append({"op": "parse", "input": prefix + national(rng, prefix, length, variant)})
    result["national_parts"] = parts
    countries = [
        None,
        "",
        " ",
        "FR",
        "fr",
        " fr ",
        "GR",
        "EL",
        "GB",
        "XI",
        "CH",
        "CHE",
        "\u00a0FR",
        "ZZ",
        "0",
        "\0FR\v",
    ]
    result["countries"] = [
        {
            "op": "parse",
            "input": rng.choice([*vectors, "27552032534", "FR552032799", "SE552032799", "NL0000000B27"]),
            "country": rng.choice(countries + list(LENGTHS)),
        }
        for _ in range(3000)
    ]
    sirens = []
    for index in range(3000):
        value = random_text(rng, DIGITS, rng.choice((8, 9, 9, 9, 10)))
        if index % 4 == 0:
            value = value[:3] + rng.choice(SEPARATORS) + value[3:]
        elif index % 4 == 1:
            value = rng.choice(("000", "ß", "\udcff", "+", "FR")) + value[3:]
        sirens.append({"op": "from_siren", "input": value})
    result["sirens"] = sirens
    bodies: list[bytes] = [
        b"",
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"NaN",
        b"Infinity",
        b"null",
        b"[]",
        b"[true]",
        b'"text"',
        rb'{"x":"\ud800","x":"ok"}',
        rb'{"\ud800":1}',
        rb'{"x":"\udfff"}',
        rb'{"\u0000x":1,"valid":true,"requestDate":"2026-10-22T01:00:38.289Z"}',
        b'{"valid":false,"valid":true,"requestDate":"2026-10-22T01:00:38.289Z"}',
    ]
    deep = b"[" * 511 + b"0" + b"]" * 511
    bodies.extend(
        (
            rb'{"x":"\ud800","y":' + deep + b"}",
            b'{"y":' + deep + rb',"x":"\ud800"}',
            rb'{"\ud800":' + deep + b"}",
            b'{"x":' + deep + rb',"\ud800":0}',
            rb'["\ud800",' + deep + b"]",
            b"[" + deep + rb',"\ud800"]',
            rb'{"x":"\ud800","x":' + deep + b"}",
            b'{"x":' + deep + rb',"x":"\ud800"}',
        )
    )
    for depth in (510, 511, 512, 513):
        bodies.extend((b"[" * depth + b"0" + b"]" * depth, b'{"x":' + b"[" * depth + b"0" + b"]" * depth + b"}"))
    types: list[Any] = [None, True, False, 42, 1.5, [], {}, "", "---", "N/A", "é", "\u00a0", "\0 ---\t"]
    dates = [
        "2026-10-22T01:00:38.289Z",
        "2024-02-29T00:00:00.000Z",
        "2026-02-31T01:00:38.289Z",
        "2026-10-22T25:00:38.289Z",
        "2026-10-22T01:00:60.289Z",
        "2026-10-22T01:00:38.289Z\0",
        "2026-10-22T01:00:38Z",
        "bad",
        None,
        42,
    ]
    checks: list[dict[str, Any]] = []
    for index in range(4000):
        data: dict[str, Any] = {"valid": rng.choice((True, False)), "requestDate": rng.choice(dates)}
        mode = index % 7
        if mode == 0:
            data[rng.choice(("name", "address", "requestIdentifier", "countryCode", "vatNumber", "valid"))] = (
                rng.choice(types)
            )
        elif mode == 1:
            data["errorWrappers"] = rng.choice(
                [None, [], [{"error": rng.choice(types)}], [["X"]], {"0": {"error": "X"}}, {"00": {"error": "X"}}]
            )
        elif mode == 2:
            data["requestDate"] = dates[0]
            text = rng.choice(("FOO  BAR", "---", "N/A", "", "é", "\u00a0", "\0 ---\t"))
            separator = rng.choice(("\r\n", "\r", "\n", "\v", "\f", "\x85", "\u2028", "\u2029"))
            data["name"] = data["address"] = f"  {text} {separator} {text}  "
            data["requestIdentifier"] = rng.choice(("", "ref", " ", "\0"))
        body = rng.choice(bodies) if mode == 3 else json.dumps(data, ensure_ascii=True).encode()
        checks.append(
            {
                "op": "check",
                "input": rng.choice(
                    (
                        "FR27552032534",
                        "BE0417497106",
                        "GR094014201",
                        "XI220430231",
                        "FR123",
                        "GB220430231",
                        "CHE116281710",
                        "NO974760673",
                    )
                ),
                "requester": rng.choice(
                    (None, "", "BE0417497106", "FR123", "GB220430231", "CHE116281710", "NO974760673")
                ),
                "status": rng.choice((200, 200, 200, 200, 301, 400, 503)),
                "body": body,
                "throw": index % 37 == 0,
            }
        )
    # Guarantee that every raw decoder edge is sent, independently of random input/source/status selection.
    checks.extend({"op": "check", "input": "BE0417497106", "body": body} for body in bodies)
    result["vies"] = checks
    settings: list[dict[str, Any]] = []
    env_values = [
        "true",
        "TRUE",
        "(false)",
        "empty",
        "(null)",
        "null",
        "false",
        '"2.5"',
        "'BE0417497106'",
        '"a\nb"',
        "0",
        "-1",
        "2.5",
        " 2.5 ",
        "1e3",
        "1_0",
        "inf",
        "nan",
        "0x1A",
        "",
        " ",
        " BE0417497106 ",
        "BE0417497106",
        "\u00a0",
        "\v",
        "\0",
    ]
    for _ in range(3000):
        env = {}
        for key in ("VAT_VALIDATOR_VIES_TIMEOUT", "VAT_VALIDATOR_REQUESTER"):
            if rng.randrange(5):
                env[key] = rng.choice([*env_values, random_text(rng, DIGITS + ".e+- abc", rng.randrange(1, 24))])
        settings.append({"op": "settings", "env": env})
    result["settings"] = settings
    return result

"""The associative-array mode of PHP json_decode, including discarded values."""

import json
from dataclasses import dataclass
from typing import final


@final
@dataclass(slots=True)
class _Pairs:
    values: list[tuple[str, object]]


def _integer(token: str) -> int | float:
    # PHP json_decode: integers outside the signed 64-bit range become doubles.
    if len(token.removeprefix("-")) > 19:
        return float(token)
    value = int(token)
    return value if -(2**63) <= value <= 2**63 - 1 else float(token)


def _constant(token: str) -> object:
    raise ValueError("Syntax error")


def _validate_string(value: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("Single unpaired UTF-16 surrogate in unicode escape")


def decode(body: bytes) -> object:
    tree: object = json.loads(
        body.decode("utf-8"), object_pairs_hook=_Pairs, parse_constant=_constant, parse_int=_integer
    )
    # PHP validates every value before duplicate keys can overwrite it.
    pending = [(tree, 0, False)]
    converted: dict[int, object] = {}
    while pending:
        node, parent_depth, visited = pending.pop()
        if isinstance(node, str):
            _validate_string(node)
        if not isinstance(node, (_Pairs, list)):
            continue
        depth = parent_depth + 1
        if depth > 511:
            raise ValueError("Maximum stack depth exceeded")
        if visited:
            if isinstance(node, _Pairs):
                converted[id(node)] = {key: converted.get(id(value), value) for key, value in node.values}
            else:
                converted[id(node)] = [converted.get(id(value), value) for value in node]
            continue
        pending.append((node, parent_depth, True))
        if isinstance(node, _Pairs):
            # LIFO: visit each key before its value, in document order.
            for key, value in reversed(node.values):
                pending.append((value, depth, False))
                pending.append((key, depth, False))
        else:
            pending.extend((value, depth, False) for value in reversed(node))
    return converted.get(id(tree), tree)

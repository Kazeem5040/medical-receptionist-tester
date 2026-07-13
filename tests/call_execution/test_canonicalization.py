from __future__ import annotations

from call_execution import canonical_json, stable_fingerprint


def test_canonical_json_sorts_keys() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_fingerprint_is_stable_for_equivalent_data() -> None:
    first = stable_fingerprint({"b": [2, 3], "a": 1})
    second = stable_fingerprint({"a": 1, "b": [2, 3]})

    assert first == second
    assert first.startswith("sha256:")

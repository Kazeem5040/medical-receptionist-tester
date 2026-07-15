from __future__ import annotations

from test_call_workflow import canonical_json, stable_fingerprint
from tests.test_call_workflow_factories import fixed_timestamp


def test_canonical_json_sorts_keys_and_serializes_datetime() -> None:
    assert canonical_json({"b": fixed_timestamp(), "a": 1}) == (
        '{"a":1,"b":"2026-01-02T03:04:05+00:00"}'
    )


def test_stable_fingerprint_matches_equivalent_data() -> None:
    first = stable_fingerprint({"b": [2, 3], "a": 1})
    second = stable_fingerprint({"a": 1, "b": [2, 3]})

    assert first == second
    assert first.startswith("sha256:")

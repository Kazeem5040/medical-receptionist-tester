from __future__ import annotations

from call_orchestrator import CallOrchestrator
from tests.call_orchestrator_factories import call_policy, call_preparation_request


def test_canonical_snapshot_is_json_compatible() -> None:
    orchestrator = CallOrchestrator(policy=call_policy())
    prepared = orchestrator.prepare_call(call_preparation_request())

    snapshot = orchestrator.create_canonical_snapshot(prepared)

    assert snapshot["status"] == "prepared"
    assert snapshot["source_scenario_id"] == "scenario-1"


def test_fingerprint_changes_when_request_changes() -> None:
    orchestrator = CallOrchestrator(policy=call_policy())

    first = orchestrator.create_fingerprint(call_preparation_request())
    second = orchestrator.create_fingerprint(
        call_preparation_request(scenario_seed="seed-2"),
    )

    assert first != second
    assert first.startswith("sha256:")

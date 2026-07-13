from __future__ import annotations

from call_orchestrator import CallOrchestrator, PreparedCall
from tests.call_orchestrator_factories import call_policy, call_preparation_request


def prepared_call() -> PreparedCall:
    return CallOrchestrator(policy=call_policy()).prepare_call(
        call_preparation_request(),
    )

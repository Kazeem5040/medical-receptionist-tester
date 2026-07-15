"""Policy defaults for the test-call workflow use case."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TestCallWorkflowPolicy(BaseModel):
    """Configurable use-case-level workflow rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    workflow_version: str = "1.0"
    policy_version: str = "1.0"
    require_prepared_call: bool = True
    require_submission_result: bool = True
    require_traceability: bool = True
    require_result_fingerprint: bool = True
    allow_provider_rejected_result: bool = True
    require_real_calls_feature_flag: bool = False
    real_calls_enabled: bool = False
    fail_if_outbound_call_not_created: bool = False


DEFAULT_TEST_CALL_WORKFLOW_POLICY = TestCallWorkflowPolicy()

"""Immutable models for the top-level test-call workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from call_execution import CallSubmissionResult
from call_orchestrator import PreparedCall

from .enums import (
    ProviderCapabilityState,
    TestCallWorkflowSeverity,
    TestCallWorkflowStatus,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TestCallWorkflowModel(BaseModel):
    """Base class for immutable test-call workflow models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class TestCallWorkflowTraceability(TestCallWorkflowModel):
    """Trace links across request, preparation, and provider submission."""

    workflow_id: NonEmptyString
    request_fingerprint: NonEmptyString
    preparation_id: NonEmptyString
    submission_id: NonEmptyString
    idempotency_key: NonEmptyString
    source_scenario_id: NonEmptyString
    source_scenario_version: int = Field(ge=1)
    scenario_template_fingerprint: NonEmptyString
    scenario_instance_fingerprint: NonEmptyString
    conversation_contract_fingerprint: NonEmptyString
    vapi_configuration_fingerprint: NonEmptyString
    submission_result_fingerprint: NonEmptyString
    scenario_seed: NonEmptyString


class TestCallWorkflowStatistics(TestCallWorkflowModel):
    """Timing and completion statistics for one workflow command."""

    workflow_started_at: datetime
    workflow_completed_at: datetime
    elapsed_milliseconds: int = Field(ge=0)
    preparation_completed: bool
    provider_submission_completed: bool


class TestCallWorkflowWarning(TestCallWorkflowModel):
    """Non-blocking warning produced by the workflow coordinator."""

    code: NonEmptyString
    message: NonEmptyString
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: TestCallWorkflowSeverity = TestCallWorkflowSeverity.WARNING


class TestCallStartResult(TestCallWorkflowModel):
    """Immediate result of starting one AI receptionist test workflow."""

    workflow_id: NonEmptyString
    status: TestCallWorkflowStatus
    provider_capability_state: ProviderCapabilityState
    prepared_call: PreparedCall
    submission_result: CallSubmissionResult
    traceability: TestCallWorkflowTraceability
    statistics: TestCallWorkflowStatistics
    workflow_version: NonEmptyString
    workflow_policy_version: NonEmptyString
    result_fingerprint: NonEmptyString
    warnings: tuple[TestCallWorkflowWarning, ...] = Field(default_factory=tuple)
    metadata: dict[str, str] = Field(default_factory=dict)

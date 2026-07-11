"""Immutable models for preparing one test call."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from conversation_contracts import ConversationContract
from scenarios import ScenarioTemplate
from scenarios.models import ScenarioInstance
from vapi_adapter import VapiAssistantConfiguration

from .enums import CallWorkflowStatus, DestinationKind

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
IdempotencyKey = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=8, max_length=128),
]
CorrelationId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]


class CallOrchestratorModel(BaseModel):
    """Base class for immutable call orchestration models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class ApprovedDestination(CallOrchestratorModel):
    """Destination reference that must be approved by policy."""

    kind: DestinationKind
    value: NonEmptyString
    label: NonEmptyString | None = None


class CallPreparationRequest(CallOrchestratorModel):
    """Strict input for preparing one future test call."""

    scenario_template: ScenarioTemplate
    scenario_seed: NonEmptyString
    destination: ApprovedDestination
    idempotency_key: IdempotencyKey
    request_id: CorrelationId | None = None
    requested_call_duration_seconds: int | None = Field(default=None, ge=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class CallPreparationWarning(CallOrchestratorModel):
    """Non-blocking warning produced during call preparation."""

    code: NonEmptyString
    message: NonEmptyString
    path: tuple[str | int, ...] = Field(default_factory=tuple)


class PreparedCall(CallOrchestratorModel):
    """Prepared call artifact ready for a future provider API client."""

    preparation_id: NonEmptyString
    idempotency_key: IdempotencyKey
    status: CallWorkflowStatus
    destination: ApprovedDestination
    scenario_instance: ScenarioInstance
    conversation_contract: ConversationContract
    vapi_configuration: VapiAssistantConfiguration
    source_scenario_id: NonEmptyString
    source_scenario_version: int = Field(ge=1)
    scenario_template_fingerprint: NonEmptyString
    scenario_instance_fingerprint: NonEmptyString | None
    conversation_contract_fingerprint: NonEmptyString | None
    vapi_configuration_fingerprint: NonEmptyString | None
    scenario_seed: NonEmptyString
    orchestrator_version: NonEmptyString
    orchestration_policy_version: NonEmptyString
    request_fingerprint: NonEmptyString
    warnings: tuple[CallPreparationWarning, ...] = Field(default_factory=tuple)
    metadata: dict[str, str] = Field(default_factory=dict)

    def provider_payload(self) -> dict[str, Any]:
        """Return the Vapi provider-facing payload for a future API client."""

        return self.vapi_configuration.to_vapi_payload()

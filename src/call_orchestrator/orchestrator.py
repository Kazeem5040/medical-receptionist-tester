"""Call preparation workflow coordinator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from conversation_contracts import ConversationContractBuilder
from scenarios import ScenarioManager
from vapi_adapter import VapiProviderAdapter

from .canonicalization import canonical_snapshot, stable_fingerprint
from .enums import CallWorkflowStatus
from .errors import (
    CallOrchestrationError,
    CallOrchestrationIssue,
    CallOrchestrationValidationResult,
)
from .models import CallPreparationRequest, CallPreparationWarning, PreparedCall
from .policies import DEFAULT_CALL_ORCHESTRATION_POLICY, CallOrchestrationPolicy
from .validation import (
    validate_call_preparation_request,
    validate_prepared_call,
)


@dataclass(frozen=True)
class _IdempotencyRecord:
    request_fingerprint: str
    prepared_call: PreparedCall


class CallOrchestrator:
    """Coordinates preparation of one future test call."""

    def __init__(
        self,
        *,
        scenario_manager: ScenarioManager | None = None,
        contract_builder: ConversationContractBuilder | None = None,
        vapi_adapter: VapiProviderAdapter | None = None,
        policy: CallOrchestrationPolicy = DEFAULT_CALL_ORCHESTRATION_POLICY,
    ) -> None:
        self._scenario_manager = scenario_manager or ScenarioManager()
        self._contract_builder = contract_builder or ConversationContractBuilder()
        self._vapi_adapter = vapi_adapter or VapiProviderAdapter()
        self._policy = policy
        self._idempotency_store: dict[str, _IdempotencyRecord] = {}

    @property
    def policy(self) -> CallOrchestrationPolicy:
        """Policy used by this orchestrator."""

        return self._policy

    def prepare_call(self, request: CallPreparationRequest) -> PreparedCall:
        """Prepare a call without contacting any external provider."""

        request_fingerprint = self.create_fingerprint(request)
        existing = self._idempotency_store.get(request.idempotency_key)
        if existing is not None:
            return self._handle_idempotent_request(
                request=request,
                request_fingerprint=request_fingerprint,
                existing=existing,
            )

        validation_result = validate_call_preparation_request(request, self._policy)
        validation_result.raise_if_invalid()

        scenario_template_fingerprint = self.create_fingerprint(
            request.scenario_template,
        )
        scenario_instance = self._scenario_manager.create_instance(
            request.scenario_template,
            seed=request.scenario_seed,
        )
        conversation_contract = self._contract_builder.build(scenario_instance)
        vapi_configuration = self._vapi_adapter.build(conversation_contract)

        warnings = self._request_warnings(request)
        prepared_call = PreparedCall(
            preparation_id=self._derive_preparation_id(
                request_fingerprint=request_fingerprint,
                vapi_configuration_fingerprint=(
                    vapi_configuration.configuration_fingerprint
                ),
            ),
            idempotency_key=request.idempotency_key,
            status=CallWorkflowStatus.PREPARED,
            destination=request.destination,
            scenario_instance=scenario_instance,
            conversation_contract=conversation_contract,
            vapi_configuration=vapi_configuration,
            source_scenario_id=scenario_instance.source_scenario_id,
            source_scenario_version=scenario_instance.source_scenario_version,
            scenario_template_fingerprint=scenario_template_fingerprint,
            scenario_instance_fingerprint=scenario_instance.fingerprint,
            conversation_contract_fingerprint=conversation_contract.fingerprint,
            vapi_configuration_fingerprint=(
                vapi_configuration.configuration_fingerprint
            ),
            scenario_seed=request.scenario_seed,
            orchestrator_version=self._policy.orchestrator_version,
            orchestration_policy_version=self._policy.policy_version,
            request_fingerprint=request_fingerprint,
            warnings=warnings,
            metadata=dict(request.metadata),
        )

        prepared_validation = validate_prepared_call(prepared_call)
        prepared_validation.raise_if_invalid()

        self._idempotency_store[request.idempotency_key] = _IdempotencyRecord(
            request_fingerprint=request_fingerprint,
            prepared_call=prepared_call,
        )
        return prepared_call

    def validate_request(
        self,
        request: CallPreparationRequest,
    ) -> CallOrchestrationValidationResult:
        """Validate orchestration-level request data."""

        return validate_call_preparation_request(request, self._policy)

    def create_canonical_snapshot(self, value: Any) -> dict[str, Any]:
        """Create a canonical JSON-compatible snapshot."""

        return canonical_snapshot(value)

    def create_fingerprint(self, value: Any) -> str:
        """Create a stable fingerprint for orchestration data."""

        return stable_fingerprint(value)

    def _handle_idempotent_request(
        self,
        *,
        request: CallPreparationRequest,
        request_fingerprint: str,
        existing: _IdempotencyRecord,
    ) -> PreparedCall:
        if existing.request_fingerprint != request_fingerprint:
            result = CallOrchestrationValidationResult.from_issues(
                (
                    CallOrchestrationIssue(
                        code="idempotency_key_reused_with_different_request",
                        message=(
                            "Idempotency key was reused with different request "
                            "content."
                        ),
                        path=("idempotency_key",),
                    ),
                ),
            )
            raise CallOrchestrationError(result)

        if not self._policy.allow_idempotent_replay:
            result = CallOrchestrationValidationResult.from_issues(
                (
                    CallOrchestrationIssue(
                        code="idempotent_replay_disabled",
                        message="Idempotent replay is disabled by policy.",
                        path=("idempotency_key",),
                    ),
                ),
            )
            raise CallOrchestrationError(result)

        replay_warning = CallPreparationWarning(
            code="idempotent_result_reused",
            message=(
                "A previously prepared call was returned for this idempotency key."
            ),
            path=("idempotency_key",),
        )
        return existing.prepared_call.model_copy(
            update={"warnings": existing.prepared_call.warnings + (replay_warning,)},
        )

    def _request_warnings(
        self,
        request: CallPreparationRequest,
    ) -> tuple[CallPreparationWarning, ...]:
        warnings: list[CallPreparationWarning] = []
        if request.requested_call_duration_seconds is not None:
            warnings.append(
                CallPreparationWarning(
                    code="requested_duration_recorded_not_applied",
                    message=(
                        "Requested call duration override was validated and recorded, "
                        "but provider duration remains derived by completed adapter "
                        "and scenario termination rules in this phase."
                    ),
                    path=("requested_call_duration_seconds",),
                ),
            )
        return tuple(warnings)

    @staticmethod
    def _derive_preparation_id(
        *,
        request_fingerprint: str,
        vapi_configuration_fingerprint: str | None,
    ) -> str:
        digest = stable_fingerprint(
            {
                "request_fingerprint": request_fingerprint,
                "vapi_configuration_fingerprint": vapi_configuration_fingerprint,
            },
        ).split(":", maxsplit=1)[1]
        return f"prepared-call-{digest[:16]}"

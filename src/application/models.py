"""Immutable application container models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from call_execution import CallExecutionService
from call_monitoring import CallSessionCollector
from call_orchestrator import CallOrchestrator
from conversation_contracts import ConversationContractBuilder
from runtime_config import RuntimeConfiguration
from scenarios import ScenarioManager
from vapi_adapter import VapiProviderAdapter
from vapi_client import VapiApiClient

from .enums import ApplicationMode, StartupState


class ApplicationModel(BaseModel):
    """Base class for immutable application composition models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )


class ApplicationStartupMetadata(ApplicationModel):
    """Metadata describing the assembled application container."""

    application_version: str = Field(min_length=1)
    bootstrap_policy_version: str = Field(min_length=1)
    mode: ApplicationMode
    startup_state: StartupState
    bootstrapped_at: datetime


class ApplicationServices(ApplicationModel):
    """Completed production services assembled by the composition root."""

    scenario_manager: ScenarioManager
    conversation_contract_builder: ConversationContractBuilder
    vapi_provider_adapter: VapiProviderAdapter
    call_orchestrator: CallOrchestrator
    vapi_client: VapiApiClient
    call_execution_service: CallExecutionService
    call_monitoring_collector: CallSessionCollector


class Application(ApplicationModel):
    """Immutable composition root result used by future entry points."""

    runtime_config: RuntimeConfiguration
    services: ApplicationServices
    startup_metadata: ApplicationStartupMetadata

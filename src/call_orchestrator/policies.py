"""Policy defaults for call preparation orchestration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CallOrchestrationPolicy(BaseModel):
    """Configurable orchestration-level safety and workflow rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    orchestrator_version: str = "1.0"
    policy_version: str = "1.0"
    allowed_destination_identifiers: tuple[str, ...] = Field(default_factory=tuple)
    allowed_destination_phone_numbers: tuple[str, ...] = Field(default_factory=tuple)
    min_requested_call_duration_seconds: int = Field(default=30, ge=1)
    max_requested_call_duration_seconds: int = Field(default=3600, ge=1)
    max_metadata_items: int = Field(default=20, ge=0)
    max_metadata_key_length: int = Field(default=64, ge=1)
    max_metadata_value_length: int = Field(default=256, ge=1)
    allow_idempotent_replay: bool = True


DEFAULT_CALL_ORCHESTRATION_POLICY = CallOrchestrationPolicy()

"""Policy defaults for call lifecycle session tracking."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import CallSessionState


class CallSessionPolicy(BaseModel):
    """Configurable lifecycle, metadata, and schema rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    service_version: str = "1.0"
    policy_version: str = "1.0"
    initial_state: CallSessionState = CallSessionState.REQUESTED
    terminal_states: tuple[CallSessionState, ...] = (
        CallSessionState.COMPLETED,
        CallSessionState.FAILED,
        CallSessionState.CANCELLED,
    )
    allow_artifact_updates_after_terminal: bool = True
    require_provider_call_id: bool = True
    require_traceability_fingerprints: bool = True
    max_processed_event_ids: int = Field(default=1000, ge=1)
    max_metadata_items: int = Field(default=20, ge=0)
    max_metadata_key_length: int = Field(default=64, ge=1)
    max_metadata_value_length: int = Field(default=256, ge=1)


DEFAULT_CALL_SESSION_POLICY = CallSessionPolicy()

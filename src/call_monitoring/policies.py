"""Policy defaults for collecting call monitoring events."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CallMonitoringPolicy(BaseModel):
    """Configurable monitoring-level collection and validation rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    monitoring_version: str = "1.0"
    policy_version: str = "1.0"
    max_events_per_session: int = Field(default=10_000, ge=1)
    max_transcript_text_length: int = Field(default=8_000, ge=1)
    max_metadata_items: int = Field(default=50, ge=0)
    max_metadata_key_length: int = Field(default=64, ge=1)
    max_metadata_value_length: int = Field(default=1_000, ge=1)
    require_submission_acceptance: bool = True
    require_traceability_fingerprints: bool = True


DEFAULT_CALL_MONITORING_POLICY = CallMonitoringPolicy()

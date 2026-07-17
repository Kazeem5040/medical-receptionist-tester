"""Policy defaults for real outbound call creation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OutboundCallCreationPolicy(BaseModel):
    """Safety and behavior rules for requesting real outbound calls."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    creation_version: str = "1.0"
    policy_version: str = "1.0"
    real_calls_enabled: bool = False
    require_accepted_submission: bool = True
    require_destination_e164: bool = True
    require_destination_allowlist: bool = True
    allowed_destination_phone_numbers: tuple[str, ...] = Field(default_factory=tuple)
    require_provider_call_id: bool = True
    require_traceability_fingerprints: bool = True
    max_metadata_items: int = Field(default=20, ge=0)
    max_metadata_key_length: int = Field(default=64, ge=1)
    max_metadata_value_length: int = Field(default=256, ge=1)


DEFAULT_OUTBOUND_CALL_CREATION_POLICY = OutboundCallCreationPolicy()

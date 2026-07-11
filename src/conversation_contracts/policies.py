"""Policy knobs for building conversation contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConversationContractPolicy(BaseModel):
    """Rules controlling the contract builder's deterministic defaults."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: str = "1.0"
    require_instance_fingerprint: bool = False
    min_objectives: int = Field(default=1, ge=1)
    min_knowledge_boundaries: int = Field(default=1, ge=1)
    min_forbidden_behaviors: int = Field(default=1, ge=1)
    min_termination_rules: int = Field(default=1, ge=1)
    include_default_unknown_boundaries: bool = True
    include_default_behavioral_constraints: bool = True
    include_default_recovery_rules: bool = True
    include_default_clarification_rules: bool = True
    include_default_steering_rules: bool = True


DEFAULT_CONTRACT_POLICY = ConversationContractPolicy()

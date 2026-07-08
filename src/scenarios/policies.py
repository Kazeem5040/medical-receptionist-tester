"""Validation policy knobs for the Scenario Manager."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScenarioValidationPolicy(BaseModel):
    """Rules that define what "complete enough to run" means."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    require_active_lifecycle_for_instantiation: bool = True
    require_synthetic_profile: bool = True
    min_objectives: int = Field(default=1, ge=1)
    min_expected_behaviors: int = Field(default=1, ge=0)
    min_evaluation_criteria: int = Field(default=1, ge=0)
    min_termination_rules: int = Field(default=1, ge=0)
    max_tags: int = Field(default=20, ge=1)
    max_call_seconds_limit: int = Field(default=3600, ge=60)


DEFAULT_VALIDATION_POLICY = ScenarioValidationPolicy()

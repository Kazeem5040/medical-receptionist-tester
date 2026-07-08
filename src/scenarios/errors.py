"""Structured validation errors for scenarios."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import ValidationSeverity


class ScenarioValidationIssue(BaseModel):
    """A machine-readable issue found while validating a scenario."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: ValidationSeverity = ValidationSeverity.ERROR


class ScenarioValidationResult(BaseModel):
    """Validation result containing errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[ScenarioValidationIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[ScenarioValidationIssue, ...]:
        """Return only error-severity issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[ScenarioValidationIssue, ...]:
        """Return only warning-severity issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether the scenario has no validation errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[ScenarioValidationIssue],
    ) -> "ScenarioValidationResult":
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise a ScenarioValidationError if validation failed."""

        if not self.is_valid:
            raise ScenarioValidationError(self)


class ScenarioValidationError(ValueError):
    """Raised when a scenario cannot be used safely or consistently."""

    def __init__(self, result: ScenarioValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Scenario validation failed.")

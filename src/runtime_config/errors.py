"""Structured errors for runtime configuration loading and validation."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import RuntimeValidationSeverity


class RuntimeConfigurationIssue(BaseModel):
    """Machine-readable runtime configuration issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: RuntimeValidationSeverity = RuntimeValidationSeverity.ERROR


class RuntimeConfigurationValidationResult(BaseModel):
    """Validation result containing runtime errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[RuntimeConfigurationIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[RuntimeConfigurationIssue, ...]:
        """Return only blocking runtime configuration issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == RuntimeValidationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[RuntimeConfigurationIssue, ...]:
        """Return only non-blocking runtime configuration warnings."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == RuntimeValidationSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether validation found no blocking errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[RuntimeConfigurationIssue],
    ) -> RuntimeConfigurationValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise RuntimeConfigurationError if validation failed."""

        if not self.is_valid:
            raise RuntimeConfigurationError(self)


class RuntimeConfigurationError(ValueError):
    """Raised when runtime configuration cannot be loaded safely."""

    def __init__(self, result: RuntimeConfigurationValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Runtime configuration validation failed.")

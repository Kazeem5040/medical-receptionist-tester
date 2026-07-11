"""Structured errors for call preparation orchestration."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import CallOrchestrationValidationSeverity


class CallOrchestrationIssue(BaseModel):
    """Machine-readable orchestration validation issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: CallOrchestrationValidationSeverity = (
        CallOrchestrationValidationSeverity.ERROR
    )


class CallOrchestrationValidationResult(BaseModel):
    """Validation result containing orchestration errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[CallOrchestrationIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[CallOrchestrationIssue, ...]:
        """Return only error-severity issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == CallOrchestrationValidationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[CallOrchestrationIssue, ...]:
        """Return only warning-severity issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == CallOrchestrationValidationSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether validation found no blocking errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[CallOrchestrationIssue],
    ) -> CallOrchestrationValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise CallOrchestrationError if validation failed."""

        if not self.is_valid:
            raise CallOrchestrationError(self)


class CallOrchestrationError(ValueError):
    """Raised when a call preparation request cannot be safely prepared."""

    def __init__(self, result: CallOrchestrationValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Call orchestration validation failed.")

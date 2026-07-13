"""Structured errors for call monitoring."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import MonitoringSeverity


class CallMonitoringIssue(BaseModel):
    """Machine-readable call monitoring validation issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: MonitoringSeverity = MonitoringSeverity.ERROR


class CallMonitoringValidationResult(BaseModel):
    """Validation result containing monitoring errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[CallMonitoringIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[CallMonitoringIssue, ...]:
        """Return only blocking monitoring issues."""

        return tuple(
            issue for issue in self.issues if issue.severity == MonitoringSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[CallMonitoringIssue, ...]:
        """Return only non-blocking monitoring warnings."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == MonitoringSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether validation found no blocking errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[CallMonitoringIssue],
    ) -> CallMonitoringValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise CallMonitoringError if validation failed."""

        if not self.is_valid:
            raise CallMonitoringError(self)


class CallMonitoringError(ValueError):
    """Raised when call events cannot be organized into a valid session."""

    def __init__(self, result: CallMonitoringValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Call monitoring validation failed.")

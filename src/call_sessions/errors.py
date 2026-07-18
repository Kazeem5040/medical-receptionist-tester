"""Structured errors for call lifecycle session tracking."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import CallSessionSeverity


class CallSessionIssue(BaseModel):
    """Machine-readable call session validation or processing issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: CallSessionSeverity = CallSessionSeverity.ERROR


class CallSessionValidationResult(BaseModel):
    """Validation result containing session errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[CallSessionIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[CallSessionIssue, ...]:
        """Return only blocking call session issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == CallSessionSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[CallSessionIssue, ...]:
        """Return only non-blocking call session issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == CallSessionSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether validation found no blocking errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[CallSessionIssue],
    ) -> CallSessionValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise CallSessionError if validation failed."""

        if not self.is_valid:
            raise CallSessionError(self)


class CallSessionError(ValueError):
    """Raised when a lifecycle session cannot be validated or processed."""

    def __init__(self, result: CallSessionValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Call session validation failed.")


class CallSessionNotFoundError(CallSessionError):
    """Raised when a repository cannot find the requested call session."""


class CallSessionConflictError(CallSessionError):
    """Raised when one provider call maps to conflicting sessions."""


class InvalidCallTransitionError(CallSessionError):
    """Raised when a lifecycle event requests an invalid state transition."""

"""Structured errors for the test-call workflow use case."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import TestCallWorkflowSeverity


class TestCallWorkflowIssue(BaseModel):
    """Machine-readable test-call workflow issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: TestCallWorkflowSeverity = TestCallWorkflowSeverity.ERROR


class TestCallWorkflowValidationResult(BaseModel):
    """Validation result containing workflow errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[TestCallWorkflowIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[TestCallWorkflowIssue, ...]:
        """Return only blocking workflow issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == TestCallWorkflowSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[TestCallWorkflowIssue, ...]:
        """Return only non-blocking workflow warnings."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == TestCallWorkflowSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether validation found no blocking errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[TestCallWorkflowIssue],
    ) -> TestCallWorkflowValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise TestCallWorkflowError if validation failed."""

        if not self.is_valid:
            raise TestCallWorkflowError(self)


class TestCallWorkflowError(RuntimeError):
    """Raised when the test-call workflow cannot complete safely."""

    def __init__(self, result: TestCallWorkflowValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Test-call workflow failed.")

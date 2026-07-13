"""Structured errors for call execution."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import ExecutionSeverity


class CallExecutionIssue(BaseModel):
    """Machine-readable issue produced by call execution validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: ExecutionSeverity = ExecutionSeverity.ERROR


class CallExecutionValidationResult(BaseModel):
    """Validation result containing execution errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[CallExecutionIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[CallExecutionIssue, ...]:
        """Return only blocking execution issues."""

        return tuple(
            issue for issue in self.issues if issue.severity == ExecutionSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[CallExecutionIssue, ...]:
        """Return only non-blocking execution warnings."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ExecutionSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether validation found no blocking errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[CallExecutionIssue],
    ) -> CallExecutionValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise CallExecutionError if validation failed."""

        if not self.is_valid:
            raise CallExecutionError(self)


class CallExecutionError(RuntimeError):
    """Raised when a prepared call cannot be submitted safely."""

    def __init__(self, result: CallExecutionValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Call execution failed.")

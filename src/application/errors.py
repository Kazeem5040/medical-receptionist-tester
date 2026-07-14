"""Structured errors for application bootstrap."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import BootstrapSeverity


class ApplicationBootstrapIssue(BaseModel):
    """Machine-readable issue produced during application bootstrap."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: BootstrapSeverity = BootstrapSeverity.ERROR


class ApplicationBootstrapValidationResult(BaseModel):
    """Validation result containing bootstrap errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[ApplicationBootstrapIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[ApplicationBootstrapIssue, ...]:
        """Return only blocking bootstrap issues."""

        return tuple(
            issue for issue in self.issues if issue.severity == BootstrapSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[ApplicationBootstrapIssue, ...]:
        """Return only non-blocking bootstrap warnings."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == BootstrapSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether validation found no blocking errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[ApplicationBootstrapIssue],
    ) -> ApplicationBootstrapValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise ApplicationBootstrapError if validation failed."""

        if not self.is_valid:
            raise ApplicationBootstrapError(self)


class ApplicationBootstrapError(RuntimeError):
    """Raised when the application dependency graph is invalid."""

    def __init__(self, result: ApplicationBootstrapValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Application bootstrap validation failed.")

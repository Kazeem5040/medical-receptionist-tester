"""Structured errors for real outbound call creation."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import OutboundCallCreationSeverity


class OutboundCallCreationIssue(BaseModel):
    """Machine-readable outbound call creation validation issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: OutboundCallCreationSeverity = OutboundCallCreationSeverity.ERROR


class OutboundCallCreationValidationResult(BaseModel):
    """Validation result containing outbound call errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[OutboundCallCreationIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[OutboundCallCreationIssue, ...]:
        """Return only blocking outbound call creation issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == OutboundCallCreationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[OutboundCallCreationIssue, ...]:
        """Return only non-blocking outbound call creation warnings."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == OutboundCallCreationSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether validation found no blocking errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[OutboundCallCreationIssue],
    ) -> OutboundCallCreationValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise OutboundCallCreationError if validation failed."""

        if not self.is_valid:
            raise OutboundCallCreationError(self)


class OutboundCallCreationError(ValueError):
    """Raised when a real outbound call cannot be safely created."""

    def __init__(self, result: OutboundCallCreationValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Outbound call creation validation failed.")

"""Structured errors for conversation contract building and validation."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import ContractValidationSeverity


class ContractValidationIssue(BaseModel):
    """A machine-readable issue found in a conversation contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: ContractValidationSeverity = ContractValidationSeverity.ERROR


class ContractValidationResult(BaseModel):
    """Validation result containing contract errors and warnings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[ContractValidationIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[ContractValidationIssue, ...]:
        """Return only error-severity issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ContractValidationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[ContractValidationIssue, ...]:
        """Return only warning-severity issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ContractValidationSeverity.WARNING
        )

    @property
    def is_valid(self) -> bool:
        """Whether the contract has no validation errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[ContractValidationIssue],
    ) -> ContractValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise ContractValidationError if validation failed."""

        if not self.is_valid:
            raise ContractValidationError(self)


class ContractValidationError(ValueError):
    """Raised when a conversation contract is incomplete or unsafe."""

    def __init__(self, result: ContractValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Conversation contract validation failed.")

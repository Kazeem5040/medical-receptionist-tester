"""Structured errors for Vapi adapter configuration validation."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .enums import VapiValidationSeverity


class VapiConfigurationIssue(BaseModel):
    """Machine-readable validation issue for Vapi configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: VapiValidationSeverity = VapiValidationSeverity.ERROR


class VapiConfigurationValidationResult(BaseModel):
    """Validation result containing errors, warnings, and unsupported features."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issues: tuple[VapiConfigurationIssue, ...] = Field(default_factory=tuple)

    @property
    def errors(self) -> tuple[VapiConfigurationIssue, ...]:
        """Return only error-severity issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == VapiValidationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[VapiConfigurationIssue, ...]:
        """Return only regular warning issues."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == VapiValidationSeverity.WARNING
        )

    @property
    def unsupported_features(self) -> tuple[VapiConfigurationIssue, ...]:
        """Return only unsupported-feature warnings."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == VapiValidationSeverity.UNSUPPORTED_FEATURE
        )

    @property
    def is_valid(self) -> bool:
        """Whether validation found no blocking errors."""

        return len(self.errors) == 0

    @classmethod
    def from_issues(
        cls,
        issues: Iterable[VapiConfigurationIssue],
    ) -> VapiConfigurationValidationResult:
        """Build a validation result from any iterable of issues."""

        return cls(issues=tuple(issues))

    def raise_if_invalid(self) -> None:
        """Raise VapiConfigurationError if validation failed."""

        if not self.is_valid:
            raise VapiConfigurationError(self)


class VapiConfigurationError(ValueError):
    """Raised when a generated Vapi configuration should not be used."""

    def __init__(self, result: VapiConfigurationValidationResult) -> None:
        self.result = result
        messages = "; ".join(issue.message for issue in result.errors)
        super().__init__(messages or "Vapi configuration validation failed.")

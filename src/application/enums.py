"""Controlled vocabulary for application bootstrap."""

from __future__ import annotations

from enum import StrEnum


class ApplicationMode(StrEnum):
    """Application operating mode derived from runtime configuration."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class StartupState(StrEnum):
    """High-level state of the assembled application container."""

    BOOTSTRAPPED = "bootstrapped"
    FAILED = "failed"


class BootstrapSeverity(StrEnum):
    """Severity level for bootstrap validation issues."""

    ERROR = "error"
    WARNING = "warning"

"""Controlled vocabulary for runtime configuration."""

from __future__ import annotations

from enum import StrEnum


class RuntimeEnvironment(StrEnum):
    """Supported application runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentTarget(StrEnum):
    """Supported deployment target categories."""

    LOCAL = "local"
    DOCKER = "docker"
    CLOUD = "cloud"
    CI = "ci"


class RuntimeValidationSeverity(StrEnum):
    """Severity level for runtime configuration validation issues."""

    ERROR = "error"
    WARNING = "warning"

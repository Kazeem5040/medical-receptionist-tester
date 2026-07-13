"""Runtime configuration loader.

This is the only package that should read operating-system environment
variables. Future components should receive RuntimeConfiguration through
dependency injection instead of calling os.getenv().
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import AnyUrl, SecretStr, TypeAdapter, ValidationError

from .enums import DeploymentTarget, RuntimeEnvironment
from .errors import (
    RuntimeConfigurationError,
    RuntimeConfigurationIssue,
    RuntimeConfigurationValidationResult,
)
from .models import (
    ApplicationConfiguration,
    FeatureFlagConfiguration,
    OpenAIConfiguration,
    ProviderRetryConfiguration,
    RuntimeConfiguration,
    VapiConfiguration,
)
from .policies import (
    DEFAULT_RUNTIME_CONFIGURATION_POLICY,
    RuntimeConfigurationPolicy,
)
from .validation import (
    validate_required_environment,
    validate_runtime_configuration,
)


def load_runtime_configuration(
    environ: Mapping[str, str] | None = None,
    *,
    policy: RuntimeConfigurationPolicy = DEFAULT_RUNTIME_CONFIGURATION_POLICY,
) -> RuntimeConfiguration:
    """Load, validate, and return immutable application runtime configuration."""

    source_environ = os.environ if environ is None else environ
    validate_required_environment(source_environ, policy).raise_if_invalid()

    try:
        configuration = RuntimeConfiguration(
            application=ApplicationConfiguration(
                service_name=_get(
                    source_environ,
                    "APP_SERVICE_NAME",
                    policy.default_service_name,
                ),
                environment=RuntimeEnvironment(
                    _get(
                        source_environ,
                        "APP_ENV",
                        policy.default_environment.value,
                    ),
                ),
                deployment_target=DeploymentTarget(
                    _get(
                        source_environ,
                        "APP_DEPLOYMENT_TARGET",
                        policy.default_deployment_target.value,
                    ),
                ),
                schema_version=policy.schema_version,
                debug_enabled=_get_bool(source_environ, "APP_DEBUG", False),
                deployment_region=_get_optional(
                    source_environ,
                    "APP_DEPLOYMENT_REGION",
                ),
                public_base_url=_get_optional_url(
                    source_environ,
                    "APP_PUBLIC_BASE_URL",
                ),
            ),
            vapi=VapiConfiguration(
                api_key=SecretStr(_get_required(source_environ, "VAPI_API_KEY")),
                base_url=_parse_url(
                    _get(
                        source_environ,
                        "VAPI_BASE_URL",
                        policy.default_vapi_base_url,
                    ),
                ),
                request_timeout_seconds=_get_float(
                    source_environ,
                    "VAPI_TIMEOUT_SECONDS",
                    policy.default_vapi_timeout_seconds,
                ),
                retry=_provider_retry_configuration(
                    source_environ,
                    prefix="VAPI",
                    policy=policy,
                ),
            ),
            openai=OpenAIConfiguration(
                api_key=SecretStr(_get_required(source_environ, "OPENAI_API_KEY")),
                base_url=_parse_url(
                    _get(
                        source_environ,
                        "OPENAI_BASE_URL",
                        policy.default_openai_base_url,
                    ),
                ),
                realtime_model=_get(
                    source_environ,
                    "OPENAI_REALTIME_MODEL",
                    policy.default_openai_realtime_model,
                ),
                responses_model=_get(
                    source_environ,
                    "OPENAI_RESPONSES_MODEL",
                    policy.default_openai_responses_model,
                ),
                request_timeout_seconds=_get_float(
                    source_environ,
                    "OPENAI_TIMEOUT_SECONDS",
                    policy.default_openai_timeout_seconds,
                ),
                retry=_provider_retry_configuration(
                    source_environ,
                    prefix="OPENAI",
                    policy=policy,
                ),
            ),
            features=FeatureFlagConfiguration(
                real_calls_enabled=_get_bool(
                    source_environ,
                    "FEATURE_REAL_CALLS_ENABLED",
                    False,
                ),
                call_monitoring_enabled=_get_bool(
                    source_environ,
                    "FEATURE_CALL_MONITORING_ENABLED",
                    True,
                ),
                transcript_evaluation_enabled=_get_bool(
                    source_environ,
                    "FEATURE_TRANSCRIPT_EVALUATION_ENABLED",
                    False,
                ),
                bug_reports_enabled=_get_bool(
                    source_environ,
                    "FEATURE_BUG_REPORTS_ENABLED",
                    False,
                ),
            ),
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise _configuration_error_from_exception(error) from error

    validate_runtime_configuration(configuration).raise_if_invalid()
    return configuration


def _provider_retry_configuration(
    environ: Mapping[str, str],
    *,
    prefix: str,
    policy: RuntimeConfigurationPolicy,
) -> ProviderRetryConfiguration:
    return ProviderRetryConfiguration(
        max_retries=_get_int(
            environ,
            f"{prefix}_MAX_RETRIES",
            policy.default_max_retries,
        ),
        backoff_initial_seconds=_get_float(
            environ,
            f"{prefix}_BACKOFF_INITIAL_SECONDS",
            policy.default_backoff_initial_seconds,
        ),
        backoff_multiplier=_get_float(
            environ,
            f"{prefix}_BACKOFF_MULTIPLIER",
            policy.default_backoff_multiplier,
        ),
    )


def _get(environ: Mapping[str, str], key: str, default: str) -> str:
    value = environ.get(key)
    if value is None or not value.strip():
        return default
    return value.strip()


def _get_required(environ: Mapping[str, str], key: str) -> str:
    value = environ.get(key, "").strip()
    if value:
        return value
    msg = f"Missing required environment variable: {key}."
    raise ValueError(msg)


def _get_optional(environ: Mapping[str, str], key: str) -> str | None:
    value = environ.get(key)
    if value is None or not value.strip():
        return None
    return value.strip()


def _get_optional_url(environ: Mapping[str, str], key: str) -> AnyUrl | None:
    value = _get_optional(environ, key)
    if value is None:
        return None
    return _parse_url(value)


def _parse_url(value: str) -> AnyUrl:
    return TypeAdapter(AnyUrl).validate_python(value)


def _get_bool(environ: Mapping[str, str], key: str, default: bool) -> bool:
    value = environ.get(key)
    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False

    msg = f"Environment variable {key} must be a boolean."
    raise ValueError(msg)


def _get_int(environ: Mapping[str, str], key: str, default: int) -> int:
    value = environ.get(key)
    if value is None or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError as error:
        msg = f"Environment variable {key} must be an integer."
        raise ValueError(msg) from error


def _get_float(environ: Mapping[str, str], key: str, default: float) -> float:
    value = environ.get(key)
    if value is None or not value.strip():
        return default
    try:
        return float(value.strip())
    except ValueError as error:
        msg = f"Environment variable {key} must be a number."
        raise ValueError(msg) from error


def _configuration_error_from_exception(error: Exception) -> RuntimeConfigurationError:
    result = _validation_result_from_exception(error)
    return RuntimeConfigurationError(result)


def _validation_result_from_exception(
    error: Exception,
) -> RuntimeConfigurationValidationResult:
    issues: list[RuntimeConfigurationIssue] = []

    if isinstance(error, ValidationError):
        for validation_error in error.errors():
            location = tuple(
                str(item) if isinstance(item, str) else int(item)
                for item in validation_error["loc"]
            )
            issues.append(
                RuntimeConfigurationIssue(
                    code="invalid_runtime_configuration",
                    message=str(validation_error["msg"]),
                    path=location,
                ),
            )
    else:
        issues.append(
            RuntimeConfigurationIssue(
                code="invalid_environment_value",
                message=str(error),
                path=("environment",),
            ),
        )

    return RuntimeConfigurationValidationResult.from_issues(issues)

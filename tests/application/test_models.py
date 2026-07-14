from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from application import (
    ApplicationMode,
    ApplicationStartupMetadata,
    StartupState,
    bootstrap_application,
)


def test_application_container_is_immutable() -> None:
    application = bootstrap_application(environ=_required_env())

    with pytest.raises(ValidationError):
        application.startup_metadata = application.startup_metadata.model_copy(
            update={"mode": ApplicationMode.PRODUCTION},
        )  # type: ignore[misc]


def test_application_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ApplicationStartupMetadata(
            application_version="0.1.0",
            bootstrap_policy_version="1.0",
            mode=ApplicationMode.DEVELOPMENT,
            startup_state=StartupState.BOOTSTRAPPED,
            bootstrapped_at=datetime.now(UTC),
            unexpected="nope",
        )


def test_startup_metadata_rejects_invalid_state() -> None:
    with pytest.raises(ValidationError):
        ApplicationStartupMetadata(
            application_version="0.1.0",
            bootstrap_policy_version="1.0",
            mode=ApplicationMode.DEVELOPMENT,
            startup_state="banana",
            bootstrapped_at=datetime.now(UTC),
        )


def test_startup_metadata_uses_controlled_values() -> None:
    application = bootstrap_application(environ=_required_env())

    assert application.startup_metadata.mode == ApplicationMode.DEVELOPMENT
    assert application.startup_metadata.startup_state == StartupState.BOOTSTRAPPED


def _required_env(**overrides: str) -> dict[str, str]:
    env = {
        "VAPI_API_KEY": "test-vapi-key",
        "OPENAI_API_KEY": "test-openai-key",
    }
    env.update(overrides)
    return env

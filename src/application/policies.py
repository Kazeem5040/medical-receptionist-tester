"""Policy defaults for application bootstrap."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ApplicationBootstrapPolicy(BaseModel):
    """Defaults and validation switches for assembling the application."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    application_version: str = "0.1.0"
    bootstrap_policy_version: str = "1.0"
    require_runtime_configuration: bool = True
    require_vapi_client: bool = True
    require_domain_services: bool = True
    require_workflow_services: bool = True
    require_monitoring_services: bool = True


DEFAULT_APPLICATION_BOOTSTRAP_POLICY = ApplicationBootstrapPolicy()

"""Ports for future provider clients.

The orchestrator prepares calls only. A future network client can implement
this protocol without changing orchestration logic.
"""

from __future__ import annotations

from typing import Protocol

from .models import PreparedCall


class CallProviderPort(Protocol):
    """Future boundary for provider clients that can consume prepared calls."""

    @property
    def provider_name(self) -> str:
        """Provider name, for example 'vapi'."""

    def build_provider_payload(self, prepared_call: PreparedCall) -> dict[str, object]:
        """Convert a prepared call into a provider-facing payload."""

"""Repository boundary for call lifecycle sessions.

This package intentionally defines only the Protocol. Concrete PostgreSQL,
Redis, or other infrastructure implementations belong in later infrastructure
packages, not in this domain component.
"""

from __future__ import annotations

from typing import Protocol

from call_execution import ProviderName

from .models import CallSession


class CallSessionRepository(Protocol):
    """Minimal storage behavior needed by the call session service."""

    def get_by_provider_call_id(
        self,
        provider: ProviderName,
        provider_call_id: str,
    ) -> CallSession | None:
        """Return the unique session for a provider call, if it exists."""

    def save(self, session: CallSession) -> None:
        """Persist or replace one call session record."""

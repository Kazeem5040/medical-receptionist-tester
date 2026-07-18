from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from call_execution import ProviderName
from call_sessions import (
    CallLifecycleEvent,
    CallLifecycleEventType,
    CallSession,
    CallSessionConflictError,
    CallSessionIssue,
    CallSessionPolicy,
    CallSessionService,
    CallSessionValidationResult,
)
from outbound_calls import OutboundCallStartResult
from tests.outbound_call_factories import (
    FakeVapiOutboundCallClient,
    valid_creation_request,
)
from tests.outbound_call_factories import (
    creator as outbound_creator,
)


def fixed_timestamp() -> datetime:
    return datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)


def timestamp_sequence() -> Iterator[datetime]:
    base = fixed_timestamp()
    yield base
    yield base + timedelta(seconds=1)
    yield base + timedelta(seconds=2)
    yield base + timedelta(seconds=3)
    yield base + timedelta(seconds=4)
    while True:
        yield base + timedelta(seconds=5)


def call_session_policy() -> CallSessionPolicy:
    return CallSessionPolicy()


def call_session_service(
    *,
    repository: InMemoryCallSessionRepository | None = None,
) -> CallSessionService:
    values = timestamp_sequence()
    return CallSessionService(
        repository=repository,
        policy=call_session_policy(),
        clock=lambda: next(values),
    )


async def outbound_call_start_result() -> OutboundCallStartResult:
    request = await valid_creation_request()
    return await outbound_creator(
        FakeVapiOutboundCallClient(),
    ).create_call(request)


async def call_session() -> CallSession:
    return call_session_service().create_session(await outbound_call_start_result())


def lifecycle_event(
    *,
    provider_call_id: str = "call_123",
    event_type: CallLifecycleEventType = CallLifecycleEventType.CALL_QUEUED,
    provider_event_id: str | None = "evt-1",
    occurred_at: datetime | None = None,
    received_at: datetime | None = None,
    failure_code: str | None = None,
    failure_message: str | None = None,
    ended_reason: str | None = None,
    transcript_artifact_uri: str | None = None,
    recording_artifact_uri: str | None = None,
    summary_artifact_uri: str | None = None,
    metadata: dict[str, str] | None = None,
) -> CallLifecycleEvent:
    timestamp = fixed_timestamp() + timedelta(minutes=1)
    return CallLifecycleEvent(
        provider=ProviderName.VAPI,
        provider_call_id=provider_call_id,
        event_type=event_type,
        occurred_at=occurred_at or timestamp,
        received_at=received_at or timestamp + timedelta(seconds=1),
        provider_event_id=provider_event_id,
        ended_reason=ended_reason,
        failure_code=failure_code,
        failure_message=failure_message,
        transcript_artifact_uri=transcript_artifact_uri,
        recording_artifact_uri=recording_artifact_uri,
        summary_artifact_uri=summary_artifact_uri,
        metadata=metadata or {},
    )


class InMemoryCallSessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[tuple[ProviderName, str], CallSession] = {}

    def get_by_provider_call_id(
        self,
        provider: ProviderName,
        provider_call_id: str,
    ) -> CallSession | None:
        return self._sessions.get((provider, provider_call_id))

    def save(self, session: CallSession) -> None:
        key = (session.provider, session.provider_call_id)
        existing = self._sessions.get(key)
        if existing is not None and existing.session_id != session.session_id:
            raise CallSessionConflictError(
                CallSessionValidationResult.from_issues(
                    (
                        CallSessionIssue(
                            code="provider_call_session_conflict",
                            message=(
                                "Provider call already belongs to a different "
                                "session."
                            ),
                            path=("provider_call_id",),
                        ),
                    ),
                ),
            )
        self._sessions[key] = session

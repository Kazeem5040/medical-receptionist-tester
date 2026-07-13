"""Primary collector for organizing observed call events into a CallSession."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from call_execution import CallSubmissionResult

from .canonicalization import stable_fingerprint
from .enums import (
    CallCompletionReason,
    CallLifecycleState,
    CallParticipant,
    CallSessionStatus,
    MonitoringEventKind,
)
from .models import (
    CallLifecycleEvent,
    CallSession,
    CallSessionArtifacts,
    CallSessionStatistics,
    CallSessionTraceability,
    InterruptionEvent,
    MonitoringInputEvent,
    ProviderEventMetadata,
    SilenceEvent,
    TranscriptUtterance,
)
from .policies import DEFAULT_CALL_MONITORING_POLICY, CallMonitoringPolicy
from .validation import (
    validate_call_session,
    validate_call_submission_for_monitoring,
    validate_monitoring_events,
)


class CallSessionCollector:
    """Collect provider-independent call events into an immutable CallSession."""

    def __init__(
        self,
        *,
        policy: CallMonitoringPolicy = DEFAULT_CALL_MONITORING_POLICY,
    ) -> None:
        self._policy = policy

    @property
    def policy(self) -> CallMonitoringPolicy:
        """Monitoring policy used by this collector."""

        return self._policy

    def collect(
        self,
        *,
        submission: CallSubmissionResult,
        events: Sequence[MonitoringInputEvent],
    ) -> CallSession:
        """Build a complete CallSession from a call submission and observed events."""

        validate_call_submission_for_monitoring(
            submission,
            self._policy,
        ).raise_if_invalid()
        validate_monitoring_events(events, self._policy).raise_if_invalid()

        ordered_events = tuple(
            sorted(
                events,
                key=lambda event: (
                    event.occurred_at,
                    event.sequence_index,
                    event.event_id,
                ),
            ),
        )

        provider_events = tuple(
            ProviderEventMetadata(
                event_id=event.event_id,
                provider_event_id=event.provider_event_id,
                provider_event_type=event.provider_event_type,
                kind=event.kind,
                occurred_at=event.occurred_at,
                sequence_index=event.sequence_index,
                values=event.metadata,
            )
            for event in ordered_events
        )
        lifecycle_events = self._collect_lifecycle_events(ordered_events)
        transcript = self._collect_transcript(ordered_events)
        interruptions = self._collect_interruptions(ordered_events)
        silence_events = self._collect_silence_events(ordered_events)
        artifacts = self._collect_artifacts(ordered_events)
        traceability = self._build_traceability(submission)
        started_at = self._started_at(ordered_events)
        ended_at = self._ended_at(lifecycle_events)
        completion_reason = self._completion_reason(lifecycle_events)
        statistics = self._build_statistics(
            provider_events=provider_events,
            lifecycle_events=lifecycle_events,
            transcript=transcript,
            interruptions=interruptions,
            silence_events=silence_events,
            started_at=started_at,
            ended_at=ended_at,
        )
        status = self._session_status(lifecycle_events)

        fingerprint_source = {
            "provider_name": submission.provider_name.value,
            "provider_events": provider_events,
            "lifecycle_events": lifecycle_events,
            "transcript": transcript,
            "interruptions": interruptions,
            "silence_events": silence_events,
            "artifacts": artifacts,
            "started_at": started_at,
            "ended_at": ended_at,
            "completion_reason": completion_reason,
            "traceability": traceability,
            "statistics": statistics,
            "monitoring_version": self._policy.monitoring_version,
            "monitoring_policy_version": self._policy.policy_version,
            "metadata": submission.metadata,
        }
        session_fingerprint = stable_fingerprint(
            fingerprint_source,
            prefix="call_session",
        )
        session_id = stable_fingerprint(
            {
                "submission_id": submission.submission_id,
                "session_fingerprint": session_fingerprint,
            },
            prefix="session",
        )

        session = CallSession(
            session_id=session_id,
            status=status,
            provider_name=submission.provider_name.value,
            provider_events=provider_events,
            lifecycle_events=lifecycle_events,
            transcript=transcript,
            interruptions=interruptions,
            silence_events=silence_events,
            artifacts=artifacts,
            started_at=started_at,
            ended_at=ended_at,
            completion_reason=completion_reason,
            traceability=traceability,
            statistics=statistics,
            monitoring_version=self._policy.monitoring_version,
            monitoring_policy_version=self._policy.policy_version,
            session_fingerprint=session_fingerprint,
            metadata=dict(submission.metadata),
        )
        validate_call_session(session, self._policy).raise_if_invalid()
        return session

    def _collect_lifecycle_events(
        self,
        events: Sequence[MonitoringInputEvent],
    ) -> tuple[CallLifecycleEvent, ...]:
        lifecycle_events: list[CallLifecycleEvent] = []
        for event in events:
            if event.kind != MonitoringEventKind.LIFECYCLE:
                continue
            if event.lifecycle_state is None:
                continue
            lifecycle_events.append(
                CallLifecycleEvent(
                    event_id=event.event_id,
                    state=event.lifecycle_state,
                    occurred_at=event.occurred_at,
                    provider_event_id=event.provider_event_id,
                    completion_reason=event.completion_reason,
                    metadata=event.metadata,
                ),
            )
        return tuple(lifecycle_events)

    def _collect_transcript(
        self,
        events: Sequence[MonitoringInputEvent],
    ) -> tuple[TranscriptUtterance, ...]:
        transcript: list[TranscriptUtterance] = []
        for event in events:
            if event.kind != MonitoringEventKind.TRANSCRIPT:
                continue
            if event.speaker is None or event.text is None:
                continue
            transcript.append(
                TranscriptUtterance(
                    turn_index=len(transcript),
                    event_id=event.event_id,
                    speaker=event.speaker,
                    text=event.text,
                    started_at=event.occurred_at,
                    ended_at=event.ended_at,
                    provider_event_id=event.provider_event_id,
                    interrupted=False,
                    metadata=event.metadata,
                ),
            )
        return tuple(transcript)

    def _collect_interruptions(
        self,
        events: Sequence[MonitoringInputEvent],
    ) -> tuple[InterruptionEvent, ...]:
        interruptions: list[InterruptionEvent] = []
        for event in events:
            if event.kind != MonitoringEventKind.INTERRUPTION:
                continue
            if event.interrupted_speaker is None or event.interrupting_speaker is None:
                continue
            interruptions.append(
                InterruptionEvent(
                    event_id=event.event_id,
                    occurred_at=event.occurred_at,
                    interrupted_speaker=event.interrupted_speaker,
                    interrupting_speaker=event.interrupting_speaker,
                    provider_event_id=event.provider_event_id,
                    reason=event.metadata.get("reason"),
                    metadata=event.metadata,
                ),
            )
        return tuple(interruptions)

    def _collect_silence_events(
        self,
        events: Sequence[MonitoringInputEvent],
    ) -> tuple[SilenceEvent, ...]:
        silence_events: list[SilenceEvent] = []
        for event in events:
            if event.kind != MonitoringEventKind.SILENCE:
                continue
            silence_events.append(
                SilenceEvent(
                    event_id=event.event_id,
                    started_at=event.occurred_at,
                    ended_at=event.ended_at,
                    duration_ms=event.silence_duration_ms,
                    speaker=event.speaker,
                    provider_event_id=event.provider_event_id,
                    metadata=event.metadata,
                ),
            )
        return tuple(silence_events)

    def _collect_artifacts(
        self,
        events: Sequence[MonitoringInputEvent],
    ) -> CallSessionArtifacts:
        recording_url: str | None = None
        transcript_url: str | None = None
        provider_recording_id: str | None = None
        provider_transcript_id: str | None = None

        for event in events:
            if event.kind != MonitoringEventKind.ARTIFACT:
                continue
            recording_url = event.recording_url or recording_url
            transcript_url = event.transcript_url or transcript_url
            provider_recording_id = (
                event.metadata.get("provider_recording_id") or provider_recording_id
            )
            provider_transcript_id = (
                event.metadata.get("provider_transcript_id") or provider_transcript_id
            )

        return CallSessionArtifacts(
            recording_url=recording_url,
            transcript_url=transcript_url,
            provider_recording_id=provider_recording_id,
            provider_transcript_id=provider_transcript_id,
        )

    def _build_traceability(
        self,
        submission: CallSubmissionResult,
    ) -> CallSessionTraceability:
        traceability = submission.traceability
        return CallSessionTraceability(
            submission_id=submission.submission_id,
            preparation_id=traceability.preparation_id,
            idempotency_key=traceability.idempotency_key,
            source_scenario_id=traceability.source_scenario_id,
            source_scenario_version=traceability.source_scenario_version,
            scenario_instance_fingerprint=(
                traceability.scenario_instance_fingerprint
            ),
            conversation_contract_fingerprint=(
                traceability.conversation_contract_fingerprint
            ),
            vapi_configuration_fingerprint=(
                traceability.vapi_configuration_fingerprint
            ),
            prepared_call_request_fingerprint=traceability.request_fingerprint,
            call_submission_fingerprint=submission.result_fingerprint,
            provider_resource_id=(
                submission.provider_response.provider_resource_id
            ),
            provider_call_id=submission.provider_response.provider_call_id,
        )

    def _started_at(
        self,
        events: Sequence[MonitoringInputEvent],
    ) -> datetime | None:
        if not events:
            return None
        return events[0].occurred_at

    def _ended_at(
        self,
        lifecycle_events: Sequence[CallLifecycleEvent],
    ) -> datetime | None:
        for event in reversed(lifecycle_events):
            if event.state in {
                CallLifecycleState.COMPLETED,
                CallLifecycleState.FAILED,
                CallLifecycleState.CANCELED,
            }:
                return event.occurred_at
        return None

    def _completion_reason(
        self,
        lifecycle_events: Sequence[CallLifecycleEvent],
    ) -> CallCompletionReason | None:
        for event in reversed(lifecycle_events):
            if event.completion_reason is not None:
                return event.completion_reason
        return None

    def _session_status(
        self,
        lifecycle_events: Sequence[CallLifecycleEvent],
    ) -> CallSessionStatus:
        if not lifecycle_events:
            return CallSessionStatus.UNKNOWN

        latest_state = lifecycle_events[-1].state
        if latest_state == CallLifecycleState.COMPLETED:
            return CallSessionStatus.COMPLETED
        if latest_state == CallLifecycleState.FAILED:
            return CallSessionStatus.FAILED
        if latest_state == CallLifecycleState.CANCELED:
            return CallSessionStatus.CANCELED
        if latest_state in {
            CallLifecycleState.SUBMITTED,
            CallLifecycleState.QUEUED,
            CallLifecycleState.RINGING,
            CallLifecycleState.IN_PROGRESS,
        }:
            return CallSessionStatus.ACTIVE
        return CallSessionStatus.UNKNOWN

    def _build_statistics(
        self,
        *,
        provider_events: Sequence[ProviderEventMetadata],
        lifecycle_events: Sequence[CallLifecycleEvent],
        transcript: Sequence[TranscriptUtterance],
        interruptions: Sequence[InterruptionEvent],
        silence_events: Sequence[SilenceEvent],
        started_at: datetime | None,
        ended_at: datetime | None,
    ) -> CallSessionStatistics:
        duration_ms = None
        if started_at is not None and ended_at is not None:
            duration_ms = max(
                0,
                int((ended_at.timestamp() - started_at.timestamp()) * 1000),
            )

        return CallSessionStatistics(
            provider_event_count=len(provider_events),
            lifecycle_event_count=len(lifecycle_events),
            transcript_turn_count=len(transcript),
            assistant_utterance_count=sum(
                1 for turn in transcript if turn.speaker == CallParticipant.AI_PATIENT
            ),
            receptionist_utterance_count=sum(
                1 for turn in transcript if turn.speaker == CallParticipant.RECEPTIONIST
            ),
            interruption_count=len(interruptions),
            silence_event_count=len(silence_events),
            duration_ms=duration_ms,
        )

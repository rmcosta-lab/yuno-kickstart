"""Twilio Call-update and Conference adapter for one live human handoff."""

from __future__ import annotations

import asyncio
import html
import json
import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Protocol, runtime_checkable
from urllib.parse import quote, urlencode
from uuid import UUID

import httpx
from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yuno_backend.integrations.twilio.config import (
    TwilioDestinationAllowlist,
    TwilioHumanHandoffConfig,
)
from yuno_backend.volta.persistence.tables import (
    _outbound_call_attempts,
    _twilio_handoff_bindings,
)
from yuno_backend.volta.telephony import (
    HumanHandoff,
    HumanHandoffAuthenticationError,
    HumanHandoffDestinationError,
    HumanHandoffOutcomeUncertain,
    HumanHandoffPermissionError,
    HumanHandoffProviderError,
    HumanHandoffRateLimitError,
    HumanHandoffStatus,
    HumanHandoffStatusEvent,
    HumanHandoffTimeoutError,
)

__all__ = [
    "InMemoryTwilioHandoffBindingStore",
    "SqlAlchemyTwilioExistingCallResolver",
    "SqlAlchemyTwilioHandoffBindingStore",
    "TwilioExistingCallResolver",
    "TwilioHandoffBindingStore",
    "TwilioHandoffStatusCallback",
    "TwilioHumanHandoffGateway",
]

_ACCOUNT_SID = re.compile(r"^AC[0-9a-fA-F]{32}$")
_CALL_SID = re.compile(r"^CA[0-9a-fA-F]{32}$")
_CONFERENCE_SID = re.compile(r"^CF[0-9a-fA-F]{32}$")
_EVENT_ID = re.compile(r"^[a-f0-9]{64}$")
_MAX_RESPONSE_BYTES = 65_536


@dataclass(frozen=True, slots=True)
class TwilioHandoffStatusCallback:
    provider_event_id: str
    account_sid: str = field(repr=False)
    participant_call_sid: str = field(repr=False)
    conference_sid: str = field(repr=False)
    callback_event: str
    sequence_number: int
    observed_at: datetime

    def __post_init__(self) -> None:
        if _EVENT_ID.fullmatch(self.provider_event_id) is None:
            raise ValueError("provider event ID must be a SHA-256 hex digest")
        if _ACCOUNT_SID.fullmatch(self.account_sid) is None:
            raise ValueError("invalid account SID")
        if _CALL_SID.fullmatch(self.participant_call_sid) is None:
            raise ValueError("invalid participant Call SID")
        if _CONFERENCE_SID.fullmatch(self.conference_sid) is None:
            raise ValueError("invalid Conference SID")
        if self.callback_event not in {"participant-join", "participant-leave"}:
            raise ValueError("unsupported conference callback event")
        if (
            not isinstance(self.sequence_number, int)
            or isinstance(self.sequence_number, bool)
            or self.sequence_number < 0
        ):
            raise ValueError("sequence number must be non-negative")
        if self.observed_at.utcoffset() is None:
            raise ValueError("callback timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class _Binding:
    handoff_id: UUID
    call_id: UUID
    remote_call_sid: str = field(repr=False)
    conference_name: str
    conference_sid: str | None = field(default=None, repr=False)
    coordinator_call_sid: str | None = field(default=None, repr=False)
    remote_present: bool = False
    coordinator_present: bool = False
    remote_last_sequence: int | None = None
    coordinator_last_sequence: int | None = None


@runtime_checkable
class TwilioExistingCallResolver(Protocol):
    async def provider_call_sid(self, call_id: UUID) -> str | None: ...


@runtime_checkable
class TwilioHandoffBindingStore(Protocol):
    async def reserve(self, binding: _Binding) -> _Binding: ...

    async def attach_coordinator(
        self, handoff_id: UUID, conference_sid: str, coordinator_call_sid: str
    ) -> _Binding: ...

    async def apply_callback(
        self, callback: TwilioHandoffStatusCallback
    ) -> tuple[_Binding, bool]: ...


class InMemoryTwilioHandoffBindingStore:
    """Deterministic binding store for tests; production wiring must persist it."""

    def __init__(self) -> None:
        self._bindings: dict[UUID, _Binding] = {}
        self._events: set[str] = set()
        self._lock = asyncio.Lock()

    async def reserve(self, binding: _Binding) -> _Binding:
        async with self._lock:
            existing = self._bindings.get(binding.handoff_id)
            if existing is not None:
                return existing
            self._bindings[binding.handoff_id] = binding
            return binding

    async def attach_coordinator(
        self, handoff_id: UUID, conference_sid: str, coordinator_call_sid: str
    ) -> _Binding:
        async with self._lock:
            binding = self._bindings[handoff_id]
            if binding.conference_sid not in {None, conference_sid} or (
                binding.coordinator_call_sid not in {None, coordinator_call_sid}
            ):
                raise HumanHandoffPermissionError(call_id=binding.call_id)
            updated = replace(
                binding,
                conference_sid=conference_sid,
                coordinator_call_sid=coordinator_call_sid,
            )
            self._bindings[handoff_id] = updated
            return updated

    async def apply_callback(self, callback: TwilioHandoffStatusCallback) -> tuple[_Binding, bool]:
        async with self._lock:
            binding = next(
                (
                    item
                    for item in self._bindings.values()
                    if callback.participant_call_sid
                    in {item.remote_call_sid, item.coordinator_call_sid}
                ),
                None,
            )
            if binding is None:
                raise HumanHandoffPermissionError()
            if binding.conference_sid is None:
                if callback.participant_call_sid != binding.remote_call_sid:
                    raise HumanHandoffPermissionError(call_id=binding.call_id)
                binding = replace(binding, conference_sid=callback.conference_sid)
            elif binding.conference_sid != callback.conference_sid:
                raise HumanHandoffPermissionError(call_id=binding.call_id)
            if callback.provider_event_id in self._events:
                return binding, False
            joined = callback.callback_event == "participant-join"
            if callback.participant_call_sid == binding.remote_call_sid:
                if (
                    binding.remote_last_sequence is not None
                    and callback.sequence_number <= binding.remote_last_sequence
                ):
                    return binding, False
                binding = replace(
                    binding,
                    remote_present=joined,
                    remote_last_sequence=callback.sequence_number,
                )
            else:
                if (
                    binding.coordinator_last_sequence is not None
                    and callback.sequence_number <= binding.coordinator_last_sequence
                ):
                    return binding, False
                binding = replace(
                    binding,
                    coordinator_present=joined,
                    coordinator_last_sequence=callback.sequence_number,
                )
            self._bindings[binding.handoff_id] = binding
            self._events.add(callback.provider_event_id)
            return binding, True


class SqlAlchemyTwilioExistingCallResolver:
    """Resolve the private provider Call SID only inside server-side wiring."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def provider_call_sid(self, call_id: UUID) -> str | None:
        async with self._session_factory() as session:
            return (
                await session.execute(
                    select(_outbound_call_attempts.c.provider_call_id)
                    .where(
                        _outbound_call_attempts.c.call_session_id == call_id,
                        _outbound_call_attempts.c.state == "SUCCEEDED",
                        _outbound_call_attempts.c.call_status == "IN_PROGRESS",
                    )
                    .order_by(_outbound_call_attempts.c.updated_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()


class SqlAlchemyTwilioHandoffBindingStore:
    """Persist private Call/Conference bindings and accumulated presence."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def reserve(self, binding: _Binding) -> _Binding:
        async with self._session_factory.begin() as session:
            await session.execute(
                postgresql_insert(_twilio_handoff_bindings)
                .values(**_binding_values(binding))
                .on_conflict_do_nothing(index_elements=["handoff_id"])
            )
            return await self._get(session, binding.handoff_id)

    async def attach_coordinator(
        self, handoff_id: UUID, conference_sid: str, coordinator_call_sid: str
    ) -> _Binding:
        async with self._session_factory.begin() as session:
            result = await session.execute(
                update(_twilio_handoff_bindings)
                .where(
                    _twilio_handoff_bindings.c.handoff_id == handoff_id,
                    or_(
                        _twilio_handoff_bindings.c.conference_sid.is_(None),
                        _twilio_handoff_bindings.c.conference_sid == conference_sid,
                    ),
                    or_(
                        _twilio_handoff_bindings.c.coordinator_call_sid.is_(None),
                        _twilio_handoff_bindings.c.coordinator_call_sid == coordinator_call_sid,
                    ),
                )
                .values(
                    conference_sid=conference_sid,
                    coordinator_call_sid=coordinator_call_sid,
                )
            )
            if result.rowcount != 1:
                raise HumanHandoffPermissionError()
            return await self._get(session, handoff_id)

    async def apply_callback(self, callback: TwilioHandoffStatusCallback) -> tuple[_Binding, bool]:
        async with self._session_factory.begin() as session:
            row = (
                await session.execute(
                    select(_twilio_handoff_bindings)
                    .where(
                        or_(
                            and_(
                                _twilio_handoff_bindings.c.conference_sid
                                == callback.conference_sid,
                                or_(
                                    _twilio_handoff_bindings.c.remote_call_sid
                                    == callback.participant_call_sid,
                                    _twilio_handoff_bindings.c.coordinator_call_sid
                                    == callback.participant_call_sid,
                                ),
                            ),
                            and_(
                                _twilio_handoff_bindings.c.conference_sid.is_(None),
                                _twilio_handoff_bindings.c.remote_call_sid
                                == callback.participant_call_sid,
                            ),
                        ),
                    )
                    .with_for_update()
                )
            ).first()
            if row is None:
                raise HumanHandoffPermissionError()
            binding = _binding_from_row(row._mapping)  # noqa: SLF001
            if binding.conference_sid is None:
                binding = replace(binding, conference_sid=callback.conference_sid)
            joined = callback.callback_event == "participant-join"
            field_name = (
                "remote_present"
                if callback.participant_call_sid == binding.remote_call_sid
                else "coordinator_present"
            )
            sequence_field = (
                "remote_last_sequence"
                if field_name == "remote_present"
                else "coordinator_last_sequence"
            )
            last_sequence = getattr(binding, sequence_field)
            if last_sequence is not None and callback.sequence_number <= last_sequence:
                return binding, False
            changed = True
            if changed:
                await session.execute(
                    update(_twilio_handoff_bindings)
                    .where(_twilio_handoff_bindings.c.handoff_id == binding.handoff_id)
                    .values(
                        **{
                            "conference_sid": binding.conference_sid,
                            field_name: joined,
                            sequence_field: callback.sequence_number,
                        }
                    )
                )
                binding = replace(
                    binding,
                    **{
                        field_name: joined,
                        sequence_field: callback.sequence_number,
                    },
                )
            return binding, changed

    @staticmethod
    async def _get(session: AsyncSession, handoff_id: UUID) -> _Binding:
        row = (
            await session.execute(
                select(_twilio_handoff_bindings).where(
                    _twilio_handoff_bindings.c.handoff_id == handoff_id
                )
            )
        ).one()
        return _binding_from_row(row._mapping)  # noqa: SLF001


class TwilioHumanHandoffGateway:
    def __init__(
        self,
        client: httpx.AsyncClient,
        config: TwilioHumanHandoffConfig,
        allowlist: TwilioDestinationAllowlist,
        call_resolver: TwilioExistingCallResolver,
        binding_store: TwilioHandoffBindingStore,
    ) -> None:
        self._client = client
        self._config = config
        self._allowlist = allowlist
        self._call_resolver = call_resolver
        self._binding_store = binding_store

    async def begin_handoff(self, handoff: HumanHandoff) -> None:
        destination = self._allowlist.resolve(handoff.coordinator_destination_label)
        if destination is None:
            raise HumanHandoffDestinationError(call_id=handoff.call_id)
        remote_call_sid = await self._call_resolver.provider_call_sid(handoff.call_id)
        if remote_call_sid is None or _CALL_SID.fullmatch(remote_call_sid) is None:
            raise HumanHandoffProviderError(call_id=handoff.call_id)
        conference_name = f"volta-handoff-{handoff.handoff_id.hex}"
        binding = await self._binding_store.reserve(
            _Binding(
                handoff_id=handoff.handoff_id,
                call_id=handoff.call_id,
                remote_call_sid=remote_call_sid,
                conference_name=conference_name,
            )
        )
        if binding.coordinator_call_sid is not None:
            return
        twiml = self._conference_twiml(conference_name)
        await self._post_form(
            self._config.call_url(remote_call_sid),
            [("Twiml", twiml)],
            handoff.call_id,
            expect_json=False,
        )
        payload = await self._post_form(
            self._config.participants_url(quote(conference_name, safe="")),
            [
                ("From", self._config.coordinator_caller_id_e164),
                ("To", destination),
                ("EarlyMedia", "false"),
                ("EndConferenceOnExit", "false"),
            ],
            handoff.call_id,
            expect_json=True,
        )
        if not isinstance(payload, dict):
            raise HumanHandoffOutcomeUncertain(call_id=handoff.call_id)
        coordinator_sid = payload.get("call_sid")
        conference_sid = payload.get("conference_sid")
        if (
            not isinstance(coordinator_sid, str)
            or _CALL_SID.fullmatch(coordinator_sid) is None
            or not isinstance(conference_sid, str)
            or _CONFERENCE_SID.fullmatch(conference_sid) is None
        ):
            raise HumanHandoffOutcomeUncertain(call_id=handoff.call_id)
        await self._binding_store.attach_coordinator(
            handoff.handoff_id, conference_sid, coordinator_sid
        )

    async def map_status_callback(
        self, callback: TwilioHandoffStatusCallback
    ) -> HumanHandoffStatusEvent:
        if callback.account_sid != self._config.account_sid:
            raise HumanHandoffPermissionError()
        binding, _created = await self._binding_store.apply_callback(callback)
        if binding.remote_present and binding.coordinator_present:
            status = HumanHandoffStatus.JOINED
        elif callback.callback_event == "participant-leave":
            status = HumanHandoffStatus.FAILED_SAFE
        else:
            status = HumanHandoffStatus.CONNECTING
        return HumanHandoffStatusEvent(
            provider_event_id=callback.provider_event_id,
            handoff_id=binding.handoff_id,
            call_id=binding.call_id,
            status=status,
            sequence_number=callback.sequence_number,
            observed_at=callback.observed_at,
            remote_participant_present=binding.remote_present,
            coordinator_participant_present=binding.coordinator_present,
        )

    def _conference_twiml(self, conference_name: str) -> str:
        callback_url = html.escape(self._config.status_callback_url, quote=True)
        name = html.escape(conference_name)
        return (
            '<Response><Dial><Conference startConferenceOnEnter="true" '
            'endConferenceOnExit="false" statusCallbackEvent="join leave" '
            f'statusCallback="{callback_url}" statusCallbackMethod="POST">'
            f"{name}</Conference></Dial></Response>"
        )

    async def _post_form(
        self,
        url: str,
        form: list[tuple[str, str]],
        call_id: UUID,
        *,
        expect_json: bool,
    ) -> object | None:
        try:
            response = await self._client.post(
                url,
                auth=httpx.BasicAuth(self._config.api_key_sid, self._config.api_key_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                content=urlencode(form).encode("ascii"),
                timeout=httpx.Timeout(self._config.timeout_seconds),
            )
        except httpx.TimeoutException:
            raise HumanHandoffTimeoutError(call_id=call_id) from None
        except httpx.RequestError:
            raise HumanHandoffOutcomeUncertain(call_id=call_id) from None
        if response.status_code == 401:
            raise HumanHandoffAuthenticationError(call_id=call_id)
        if response.status_code == 403:
            raise HumanHandoffPermissionError(call_id=call_id)
        if response.status_code == 429:
            raise HumanHandoffRateLimitError(call_id=call_id)
        if response.status_code >= 500:
            raise HumanHandoffOutcomeUncertain(call_id=call_id)
        if not response.is_success:
            raise HumanHandoffProviderError(call_id=call_id)
        if not expect_json:
            return None
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise HumanHandoffOutcomeUncertain(call_id=call_id)
        try:
            return json.loads(response.content)
        except (UnicodeError, ValueError):
            raise HumanHandoffOutcomeUncertain(call_id=call_id) from None


def _binding_values(binding: _Binding) -> dict[str, object]:
    return {
        "handoff_id": binding.handoff_id,
        "call_id": binding.call_id,
        "remote_call_sid": binding.remote_call_sid,
        "conference_name": binding.conference_name,
        "conference_sid": binding.conference_sid,
        "coordinator_call_sid": binding.coordinator_call_sid,
        "remote_present": binding.remote_present,
        "coordinator_present": binding.coordinator_present,
        "remote_last_sequence": binding.remote_last_sequence,
        "coordinator_last_sequence": binding.coordinator_last_sequence,
    }


def _binding_from_row(row) -> _Binding:
    return _Binding(
        handoff_id=row["handoff_id"],
        call_id=row["call_id"],
        remote_call_sid=row["remote_call_sid"],
        conference_name=row["conference_name"],
        conference_sid=row["conference_sid"],
        coordinator_call_sid=row["coordinator_call_sid"],
        remote_present=row["remote_present"],
        coordinator_present=row["coordinator_present"],
        remote_last_sequence=row["remote_last_sequence"],
        coordinator_last_sequence=row["coordinator_last_sequence"],
    )

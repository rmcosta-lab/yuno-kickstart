from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine
from yuno_backend.volta.text_slice import create_demo_evidence_storage

ROOT = Path(__file__).resolve().parents[2]
AUTH = {"Authorization": "Bearer synthetic-test-token"}


class _RedactedDatabaseUrl(str):
    def __repr__(self) -> str:
        return "<isolated PostgreSQL API URL redacted>"


def _render_url(url: URL) -> str:
    return url.render_as_string(hide_password=False)


async def _create_database(admin_url: str, database_name: str) -> None:
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT", hide_parameters=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    finally:
        await engine.dispose()


async def _drop_database(admin_url: str, database_name: str) -> None:
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT", hide_parameters=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'DROP DATABASE "{database_name}" WITH (FORCE)'))
    finally:
        await engine.dispose()


async def _delete_evidence(database_url: str, evidence_id: str) -> None:
    engine = create_async_engine(database_url, hide_parameters=True)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM volta_agreement_evidence WHERE id=:evidence_id"),
                {"evidence_id": evidence_id},
            )
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def isolated_api_database_url() -> Iterator[str]:
    configured_url = os.environ.get("TEST_DATABASE_URL")
    if not configured_url:
        pytest.skip("TEST_DATABASE_URL is required for isolated PostgreSQL API tests")
    parsed = make_url(configured_url)
    if parsed.drivername != "postgresql+asyncpg":
        pytest.skip("isolated PostgreSQL API URL must use asyncpg")
    if parsed.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.skip("isolated PostgreSQL API tests require a loopback host")

    database_name = f"volta_api_phase10_{uuid4().hex}"
    test_url = parsed.set(database=database_name)
    admin_url = _render_url(parsed)
    rendered_test_url = _render_url(test_url)
    asyncio.run(_create_database(admin_url, database_name))
    alembic_config = Config(str(ROOT / "backend" / "alembic.ini"))
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = rendered_test_url
    try:
        command.upgrade(alembic_config, "head")
        yield _RedactedDatabaseUrl(rendered_test_url)
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        asyncio.run(_drop_database(admin_url, database_name))


@pytest.fixture
def demo_evidence_references() -> Iterator[tuple[str, str]]:
    storage = create_demo_evidence_storage()
    references = (
        asyncio.run(
            storage.store(uuid4(), b"RIFF\x00\x00\x00\x00WAVEagreement-fixture-one")
        ),
        asyncio.run(
            storage.store(uuid4(), b"RIFF\x00\x00\x00\x00WAVEagreement-fixture-two")
        ),
    )
    try:
        yield references
    finally:
        for reference in references:
            asyncio.run(storage.delete(reference))


def mutation_headers(key: str) -> dict[str, str]:
    return {**AUTH, "Idempotency-Key": key}


def test_postgres_text_slice_persists_replays_and_reloads(
    isolated_api_database_url: str,
    demo_evidence_references: tuple[str, str],
) -> None:
    application = create_app(
        Settings(
            app_env="test",
            database_url=isolated_api_database_url,
            volta_demo_bearer_token="synthetic-test-token",
            cors_origins=["http://localhost:3000"],
            volta_mutation_rate_limit_requests=100,
        )
    )
    prompt = (
        "Move a 40ft dry container from Manzanillo to Guadalajara on Thursday "
        "with a maximum of MXN 9,000."
    )
    with TestClient(application, raise_server_exceptions=False) as client:
        correction = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("postgres-correction-001"),
            json={
                "source_prompt": "Move synthetic cargo from Manzanillo to Guadalajara.",
                "requested_language": "EN_US",
            },
        )
        assert correction.status_code == 201, correction.text
        assert correction.json()["approval_eligible"] is False

        draft = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("postgres-draft-001"),
            json={"source_prompt": prompt, "requested_language": "EN_US"},
        )
        assert draft.status_code == 201, draft.text
        assert draft.json()["approval_eligible"] is True

        stale_draft = client.post(
            "/v1/operations",
            headers=mutation_headers("postgres-stale-draft-001"),
            json={
                "draft_id": draft.json()["draft_id"],
                "expected_draft_version": draft.json()["draft_version"] + 1,
                "approval_actor": "demo-coordinator",
            },
        )
        assert stale_draft.status_code == 409, stale_draft.text
        assert stale_draft.json()["code"] == "STALE_DRAFT_VERSION"

        approved = client.post(
            "/v1/operations",
            headers=mutation_headers("postgres-approve-001"),
            json={
                "draft_id": draft.json()["draft_id"],
                "expected_draft_version": draft.json()["draft_version"],
                "approval_actor": "demo-coordinator",
            },
        )
        assert approved.status_code == 201, approved.text
        operation = approved.json()
        assert operation["cargo_label"] == "40ft dry container"

        stale_start = client.post(
            f"/v1/operations/{operation['operation_id']}/negotiations",
            headers=mutation_headers("postgres-stale-start-001"),
            json={
                "expected_operation_version": operation["operation_version"] + 1,
                "channel": "BROWSER_TEXT",
            },
        )
        assert stale_start.status_code == 409, stale_start.text
        assert stale_start.json()["code"] == "STALE_OPERATION_VERSION"

        started = client.post(
            f"/v1/operations/{operation['operation_id']}/negotiations",
            headers=mutation_headers("postgres-start-001"),
            json={
                "expected_operation_version": operation["operation_version"],
                "channel": "BROWSER_TEXT",
            },
        )
        assert started.status_code == 201, started.text
        selected = started.json()["sessions"][0]

        quote_body = {
            "expected_operation_version": started.json()["operation_version"],
            "carrier_id": selected["carrier"]["carrier_id"],
            "mandate_version": operation["active_mandate"]["version"],
            "terms": {
                "amount_minor": 850000,
                "currency": "MXN",
                "pickup_window": {"start_date": "2026-09-03", "end_date": "2026-09-03"},
                "conditions": ["40ft dry container"],
            },
            "valid_until": "2030-09-03T18:00:00Z",
        }
        first_quote = client.post(
            f"/v1/calls/{selected['call_id']}/quotes",
            headers=mutation_headers("postgres-quote-001"),
            json=quote_body,
        )
        replay = client.post(
            f"/v1/calls/{selected['call_id']}/quotes",
            headers=mutation_headers("postgres-quote-001"),
            json=quote_body,
        )
        assert first_quote.status_code == 201, first_quote.text
        assert replay.status_code == 201, replay.text
        assert replay.headers["idempotency-replayed"] == "true"
        assert replay.json() == first_quote.json()

        changed_reuse = client.post(
            f"/v1/calls/{selected['call_id']}/quotes",
            headers=mutation_headers("postgres-quote-001"),
            json={
                **quote_body,
                "terms": {**quote_body["terms"], "amount_minor": 840000},
            },
        )
        assert changed_reuse.status_code == 409, changed_reuse.text
        assert changed_reuse.json()["code"] == "IDEMPOTENCY_KEY_REUSED"

        reloaded = client.get(f"/v1/operations/{operation['operation_id']}", headers=AUTH)
        assert reloaded.status_code == 200, reloaded.text
        second_session = started.json()["sessions"][1]
        stale_mandate = client.post(
            f"/v1/calls/{second_session['call_id']}/quotes",
            headers=mutation_headers("postgres-stale-mandate-001"),
            json={
                **quote_body,
                "expected_operation_version": reloaded.json()["operation_version"],
                "carrier_id": second_session["carrier"]["carrier_id"],
                "mandate_version": operation["active_mandate"]["version"] + 1,
            },
        )
        assert stale_mandate.status_code == 409, stale_mandate.text
        assert stale_mandate.json()["code"] == "MANDATE_CONFLICT"

        rejected_quote = client.post(
            f"/v1/calls/{second_session['call_id']}/quotes",
            headers=mutation_headers("postgres-rejected-quote-001"),
            json={
                **quote_body,
                "expected_operation_version": reloaded.json()["operation_version"],
                "carrier_id": second_session["carrier"]["carrier_id"],
                "terms": {**quote_body["terms"], "amount_minor": 950000},
            },
        )
        assert rejected_quote.status_code == 201, rejected_quote.text
        assert rejected_quote.json()["eligibility"] == "REJECTED"

        reloaded = client.get(f"/v1/operations/{operation['operation_id']}", headers=AUTH)
        assert reloaded.status_code == 200, reloaded.text
        assert len(reloaded.json()["quotes"]) == 2

        rejected_commitment = client.post(
            f"/v1/calls/{second_session['call_id']}/commitments",
            headers=mutation_headers("postgres-rejected-commitment-001"),
            json={
                "expected_operation_version": reloaded.json()["operation_version"],
                "quote_id": rejected_quote.json()["quote_id"],
                "mandate_version": operation["active_mandate"]["version"],
                "evidence_id": rejected_quote.json()["quote_id"],
            },
        )
        assert rejected_commitment.status_code == 404, rejected_commitment.text
        assert rejected_commitment.json()["code"] == "RESOURCE_NOT_FOUND"

        mismatched_evidence = client.post(
            f"/v1/calls/{selected['call_id']}/commitments",
            headers=mutation_headers("postgres-mismatched-evidence-001"),
            json={
                "expected_operation_version": reloaded.json()["operation_version"],
                "quote_id": first_quote.json()["quote_id"],
                "mandate_version": operation["active_mandate"]["version"],
                "evidence_id": rejected_quote.json()["quote_id"],
            },
        )
        assert mismatched_evidence.status_code == 404, mismatched_evidence.text
        assert mismatched_evidence.json()["code"] == "RESOURCE_NOT_FOUND"

        attached_evidence_body = {
            "expected_operation_version": reloaded.json()["operation_version"],
            "recording_reference": demo_evidence_references[0],
            "audio_start_ms": 4200,
            "item_id": "synthetic-item-001",
            "event_id": "synthetic-event-001",
        }
        missing_artifact = client.post(
            f"/v1/calls/{selected['call_id']}/evidence",
            headers=mutation_headers("postgres-evidence-001"),
            json={
                **attached_evidence_body,
                "recording_reference": "private/missing-recording.wav",
            },
        )
        assert missing_artifact.status_code == 404, missing_artifact.text
        assert missing_artifact.json()["code"] == "RESOURCE_NOT_FOUND"
        assert "missing-recording" not in missing_artifact.text

        attached_evidence = client.post(
            f"/v1/calls/{selected['call_id']}/evidence",
            headers=mutation_headers("postgres-evidence-001"),
            json=attached_evidence_body,
        )
        attached_evidence_replay = client.post(
            f"/v1/calls/{selected['call_id']}/evidence",
            headers=mutation_headers("postgres-evidence-001"),
            json=attached_evidence_body,
        )
        assert attached_evidence.status_code == 201, attached_evidence.text
        assert attached_evidence_replay.status_code == 201, attached_evidence_replay.text
        assert attached_evidence_replay.headers["idempotency-replayed"] == "true"
        assert attached_evidence_replay.json() == attached_evidence.json()

        stale_commitment = client.post(
            f"/v1/calls/{selected['call_id']}/commitments",
            headers=mutation_headers("postgres-stale-commitment-001"),
            json={
                "expected_operation_version": reloaded.json()["operation_version"] + 1,
                "quote_id": first_quote.json()["quote_id"],
                "mandate_version": operation["active_mandate"]["version"],
                "evidence_id": attached_evidence.json()["evidence_id"],
            },
        )
        assert stale_commitment.status_code == 409, stale_commitment.text
        assert stale_commitment.json()["code"] == "STALE_OPERATION_VERSION"

        first_commitment_body = {
            "expected_operation_version": reloaded.json()["operation_version"],
            "quote_id": first_quote.json()["quote_id"],
            "mandate_version": operation["active_mandate"]["version"],
            "evidence_id": attached_evidence.json()["evidence_id"],
        }
        first_commitment = client.post(
            f"/v1/calls/{selected['call_id']}/commitments",
            headers=mutation_headers("postgres-commitment-001"),
            json=first_commitment_body,
        )
        first_commitment_replay = client.post(
            f"/v1/calls/{selected['call_id']}/commitments",
            headers=mutation_headers("postgres-commitment-001"),
            json=first_commitment_body,
        )
        assert first_commitment.status_code == 201, first_commitment.text
        assert first_commitment_replay.status_code == 201, first_commitment_replay.text
        assert first_commitment_replay.headers["idempotency-replayed"] == "true"
        assert first_commitment_replay.json() == first_commitment.json()
        assert first_commitment.json()["evidence"]["recording_reference"]

        after_first_commitment = client.get(
            f"/v1/operations/{operation['operation_id']}", headers=AUTH
        )
        assert after_first_commitment.status_code == 200, after_first_commitment.text
        assert after_first_commitment.json()["active_commitment"] == first_commitment.json()
        consumed_evidence_reuse = client.post(
            f"/v1/calls/{selected['call_id']}/commitments",
            headers=mutation_headers("postgres-consumed-evidence-001"),
            json={
                **first_commitment_body,
                "expected_operation_version": after_first_commitment.json()[
                    "operation_version"
                ],
            },
        )
        assert consumed_evidence_reuse.status_code == 404, consumed_evidence_reuse.text
        assert consumed_evidence_reuse.json()["code"] == "RESOURCE_NOT_FOUND"

        third_session = started.json()["sessions"][2]
        better_quote = client.post(
            f"/v1/calls/{third_session['call_id']}/quotes",
            headers=mutation_headers("postgres-better-quote-001"),
            json={
                **quote_body,
                "expected_operation_version": after_first_commitment.json()["operation_version"],
                "carrier_id": third_session["carrier"]["carrier_id"],
                "terms": {**quote_body["terms"], "amount_minor": 800000},
            },
        )
        assert better_quote.status_code == 201, better_quote.text

        before_replacement = client.get(f"/v1/operations/{operation['operation_id']}", headers=AUTH)
        replacement_evidence = client.post(
            f"/v1/calls/{third_session['call_id']}/evidence",
            headers=mutation_headers("postgres-evidence-002"),
            json={
                "expected_operation_version": before_replacement.json()["operation_version"],
                "recording_reference": demo_evidence_references[1],
                "audio_start_ms": 9100,
                "item_id": "synthetic-item-002",
                "event_id": "synthetic-event-002",
            },
        )
        assert replacement_evidence.status_code == 201, replacement_evidence.text
        replacement_body = {
            "expected_operation_version": before_replacement.json()["operation_version"],
            "quote_id": better_quote.json()["quote_id"],
            "mandate_version": operation["active_mandate"]["version"],
            "evidence_id": replacement_evidence.json()["evidence_id"],
        }
        replacement = client.post(
            f"/v1/calls/{third_session['call_id']}/commitments",
            headers=mutation_headers("postgres-replacement-001"),
            json=replacement_body,
        )
        replacement_replay = client.post(
            f"/v1/calls/{third_session['call_id']}/commitments",
            headers=mutation_headers("postgres-replacement-001"),
            json=replacement_body,
        )
        assert replacement.status_code == 201, replacement.text
        assert replacement_replay.status_code == 201, replacement_replay.text
        assert replacement_replay.headers["idempotency-replayed"] == "true"

        final_operation = client.get(f"/v1/operations/{operation['operation_id']}", headers=AUTH)
        audit = client.get(f"/v1/operations/{operation['operation_id']}/audit", headers=AUTH)
        assert final_operation.status_code == 200, final_operation.text
        assert final_operation.json()["active_commitment"] == replacement.json()
        assert audit.status_code == 200, audit.text
        assert audit.json()["quote_comparison"][0]["quote_id"] == better_quote.json()["quote_id"]
        assert any(
            row["quote_id"] == rejected_quote.json()["quote_id"]
            and row["eligibility"] == "REJECTED"
            for row in audit.json()["quote_comparison"]
        )
        assert [item["disposition"] for item in audit.json()["commitment_history"]] == [
            "SUPERSEDED",
            "ACTIVE",
        ]

        recap_body = {
            "expected_operation_version": final_operation.json()["operation_version"],
            "commitment_id": replacement.json()["commitment_id"],
            "rendered_content": "Confirmed terms for the simulated agreement recap.",
        }
        recap = client.post(
            f"/v1/calls/{third_session['call_id']}/recaps",
            headers=mutation_headers("postgres-recap-001"),
            json=recap_body,
        )
        recap_replay = client.post(
            f"/v1/calls/{third_session['call_id']}/recaps",
            headers=mutation_headers("postgres-recap-001"),
            json=recap_body,
        )
        assert recap.status_code == 201, recap.text
        assert recap.json()["channel"] == "SIMULATED"
        assert recap_replay.status_code == 201, recap_replay.text
        assert recap_replay.headers["idempotency-replayed"] == "true"
        assert recap_replay.json() == recap.json()
        recap_conflict = client.post(
            f"/v1/calls/{third_session['call_id']}/recaps",
            headers=mutation_headers("postgres-recap-001"),
            json={**recap_body, "rendered_content": "Changed recap content."},
        )
        assert recap_conflict.status_code == 409, recap_conflict.text
        assert recap_conflict.json()["code"] == "IDEMPOTENCY_KEY_REUSED"

        brief_body = {
            "expected_operation_version": final_operation.json()["operation_version"],
            "facts": ["Carrier reconfirmed availability"],
            "objections": [],
            "changes": ["Rate improved during comparison"],
            "unresolved_items": [],
        }
        brief = client.post(
            f"/v1/calls/{third_session['call_id']}/briefs",
            headers=mutation_headers("postgres-brief-001"),
            json=brief_body,
        )
        brief_replay = client.post(
            f"/v1/calls/{third_session['call_id']}/briefs",
            headers=mutation_headers("postgres-brief-001"),
            json=brief_body,
        )
        assert brief.status_code == 201, brief.text
        assert brief.json()["changes"] == ["Rate improved during comparison"]
        assert brief_replay.status_code == 201, brief_replay.text
        assert brief_replay.headers["idempotency-replayed"] == "true"
        assert brief_replay.json() == brief.json()

        safe_recovery_body = {
            "expected_operation_version": final_operation.json()["operation_version"],
            "scenario": "MANDATE_SAFE",
            "active_commitment_id": replacement.json()["commitment_id"],
        }
        safe_recovery = client.post(
            f"/v1/operations/{operation['operation_id']}/inbound-simulations",
            headers=mutation_headers("postgres-recovery-safe-001"),
            json=safe_recovery_body,
        )
        safe_recovery_replay = client.post(
            f"/v1/operations/{operation['operation_id']}/inbound-simulations",
            headers=mutation_headers("postgres-recovery-safe-001"),
            json=safe_recovery_body,
        )
        assert safe_recovery.status_code == 201, safe_recovery.text
        assert safe_recovery.json()["scenario"] == "MANDATE_SAFE"
        assert safe_recovery.json()["active_commitment"] is not None
        assert safe_recovery.json()["escalation"] is None
        assert safe_recovery_replay.status_code == 201, safe_recovery_replay.text
        assert safe_recovery_replay.headers["idempotency-replayed"] == "true"
        assert safe_recovery_replay.json() == safe_recovery.json()

        bad_recovery = client.post(
            f"/v1/operations/{operation['operation_id']}/inbound-simulations",
            headers=mutation_headers("postgres-recovery-bad-001"),
            json={
                "expected_operation_version": safe_recovery.json()[
                    "after_operation_version"
                ],
                "scenario": "OUT_OF_MANDATE",
                "active_commitment_id": safe_recovery.json()["active_commitment"][
                    "commitment_id"
                ],
            },
        )
        assert bad_recovery.status_code == 201, bad_recovery.text
        assert bad_recovery.json()["active_commitment"] is None
        assert bad_recovery.json()["escalation"]["resolution_state"] == "OPEN"

        after_bad = client.get(
            f"/v1/operations/{operation['operation_id']}", headers=AUTH
        )
        assert after_bad.status_code == 200, after_bad.text
        assert after_bad.json()["open_escalation"]["escalation_id"] == (
            bad_recovery.json()["escalation"]["escalation_id"]
        )
        assert len(after_bad.json()["notifications"]) == 1
        notification_id = after_bad.json()["notifications"][0]["notification_id"]

        mandate_body = {
            "expected_operation_version": after_bad.json()["operation_version"],
            "resolved_escalation_id": bad_recovery.json()["escalation"]["escalation_id"],
            "maximum_amount_minor": after_bad.json()["active_mandate"][
                "maximum_amount_minor"
            ],
            "currency": after_bad.json()["active_mandate"]["currency"],
            "pickup_window": after_bad.json()["active_mandate"]["pickup_window"],
            "allowed_conditions": after_bad.json()["active_mandate"][
                "allowed_conditions"
            ],
            "escalation_conditions": after_bad.json()["active_mandate"][
                "escalation_conditions"
            ],
            "approval_actor": "demo-coordinator",
        }
        replaced_mandate = client.post(
            f"/v1/operations/{operation['operation_id']}/mandates",
            headers=mutation_headers("postgres-mandate-001"),
            json=mandate_body,
        )
        replaced_mandate_replay = client.post(
            f"/v1/operations/{operation['operation_id']}/mandates",
            headers=mutation_headers("postgres-mandate-001"),
            json=mandate_body,
        )
        assert replaced_mandate.status_code == 201, replaced_mandate.text
        assert replaced_mandate.json()["open_escalation"] is None
        assert replaced_mandate_replay.status_code == 201, replaced_mandate_replay.text
        assert replaced_mandate_replay.headers["idempotency-replayed"] == "true"

        explicit_escalation_body = {
            "expected_operation_version": replaced_mandate.json()["operation_version"],
            "conflict": "Coordinator review requested for synthetic terms.",
            "attempted_alternatives": ["Keep active commitment"],
            "recommended_action": "Review current carrier terms",
        }
        explicit_escalation = client.post(
            f"/v1/calls/{third_session['call_id']}/escalations",
            headers=mutation_headers("postgres-escalation-001"),
            json=explicit_escalation_body,
        )
        explicit_escalation_replay = client.post(
            f"/v1/calls/{third_session['call_id']}/escalations",
            headers=mutation_headers("postgres-escalation-001"),
            json=explicit_escalation_body,
        )
        assert explicit_escalation.status_code == 201, explicit_escalation.text
        assert explicit_escalation.json()["call_id"] == third_session["call_id"]
        assert explicit_escalation_replay.status_code == 201
        assert explicit_escalation_replay.headers["idempotency-replayed"] == "true"
        assert explicit_escalation_replay.json() == explicit_escalation.json()

        before_ack = client.get(
            f"/v1/operations/{operation['operation_id']}", headers=AUTH
        )
        acknowledgement_body = {
            "expected_operation_version": before_ack.json()["operation_version"],
            "acknowledged_by": "demo-coordinator",
        }
        acknowledgement = client.post(
            f"/v1/notifications/{notification_id}/acknowledgements",
            headers=mutation_headers("postgres-notification-001"),
            json=acknowledgement_body,
        )
        acknowledgement_replay = client.post(
            f"/v1/notifications/{notification_id}/acknowledgements",
            headers=mutation_headers("postgres-notification-001"),
            json=acknowledgement_body,
        )
        assert acknowledgement.status_code == 200, acknowledgement.text
        assert acknowledgement.json()["acknowledged"] is True
        assert acknowledgement_replay.status_code == 200, acknowledgement_replay.text
        assert acknowledgement_replay.headers["idempotency-replayed"] == "true"
        assert acknowledgement_replay.json() == acknowledgement.json()
        conflicting_actor = client.post(
            f"/v1/notifications/{notification_id}/acknowledgements",
            headers=mutation_headers("postgres-notification-002"),
            json={**acknowledgement_body, "acknowledged_by": "another-coordinator"},
        )
        assert conflicting_actor.status_code == 409, conflicting_actor.text
        assert conflicting_actor.json()["code"] == "STATE_CONFLICT"

        complete_audit = client.get(
            f"/v1/operations/{operation['operation_id']}/audit?limit=100",
            headers=AUTH,
        )
        assert complete_audit.status_code == 200, complete_audit.text
        assert any(
            item["recap_id"] == recap.json()["recap_id"]
            for item in complete_audit.json()["recaps"]
        )
        assert any(
            item["brief_id"] == brief.json()["brief_id"]
            for item in complete_audit.json()["briefs"]
        )
        assert len(complete_audit.json()["recoveries"]) == 2
        assert len(complete_audit.json()["escalations"]) >= 2
        assert complete_audit.json()["notifications"][0]["acknowledged"] is True

        first_page = client.get(
            f"/v1/operations/{operation['operation_id']}/audit",
            headers=AUTH,
            params={"limit": 2},
        )
        assert first_page.status_code == 200, first_page.text
        assert first_page.json()["next_cursor"]
        second_page = client.get(
            f"/v1/operations/{operation['operation_id']}/audit",
            headers=AUTH,
            params={"limit": 2, "cursor": first_page.json()["next_cursor"]},
        )
        assert second_page.status_code == 200, second_page.text
        malformed_cursor = client.get(
            f"/v1/operations/{operation['operation_id']}/audit",
            headers=AUTH,
            params={"cursor": "submitted-private-cursor", "limit": 2},
        )
        assert malformed_cursor.status_code == 422, malformed_cursor.text
        assert malformed_cursor.json()["code"] == "VALIDATION_ERROR"
        assert "submitted-private-cursor" not in malformed_cursor.text

        no_carrier_draft = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("postgres-no-carrier-draft-001"),
            json={
                "source_prompt": "Move a 40ft container from Veracruz to Puebla.",
                "requested_language": "EN_US",
            },
        )
        assert no_carrier_draft.status_code == 201, no_carrier_draft.text
        no_carrier_operation = client.post(
            "/v1/operations",
            headers=mutation_headers("postgres-no-carrier-approve-001"),
            json={
                "draft_id": no_carrier_draft.json()["draft_id"],
                "expected_draft_version": no_carrier_draft.json()["draft_version"],
                "approval_actor": "demo-coordinator",
            },
        )
        assert no_carrier_operation.status_code == 201, no_carrier_operation.text
        no_carrier = client.post(
            f"/v1/operations/{no_carrier_operation.json()['operation_id']}/negotiations",
            headers=mutation_headers("postgres-no-carrier-start-001"),
            json={
                "expected_operation_version": no_carrier_operation.json()["operation_version"],
                "channel": "BROWSER_TEXT",
            },
        )
        assert no_carrier.status_code == 201, no_carrier.text
        assert no_carrier.json()["sessions"] == []
        assert no_carrier.json()["pre_contact_escalation"]["conflict"] == (
            "No eligible synthetic carrier passed route and availability checks."
        )

        asyncio.run(
            _delete_evidence(
                isolated_api_database_url,
                replacement.json()["evidence"]["evidence_id"],
            )
        )
        missing_evidence = client.post(
            f"/v1/calls/{third_session['call_id']}/commitments",
            headers=mutation_headers("postgres-replacement-001"),
            json=replacement_body,
        )
        assert missing_evidence.status_code == 409, missing_evidence.text
        assert missing_evidence.json()["code"] == "STATE_CONFLICT"

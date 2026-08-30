from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from . import conftest as persistence_conftest


@pytest.fixture(scope="module")
def isolated_database_url() -> Iterator[str]:
    """Keep reversible migration tests independent from durable F25 facts."""
    configured_url = os.environ.get("TEST_DATABASE_URL")
    if not configured_url:
        pytest.skip("TEST_DATABASE_URL is required for isolated PostgreSQL tests")
    parsed = make_url(configured_url)
    if parsed.drivername != "postgresql+asyncpg" or parsed.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        pytest.skip("isolated PostgreSQL tests require asyncpg on loopback")

    database_name = f"volta_migrations_{uuid4().hex}"
    test_url = parsed.set(database=database_name)
    rendered_admin_url = persistence_conftest._render_url(parsed)
    rendered_test_url = persistence_conftest._render_url(test_url)
    asyncio.run(persistence_conftest._create_database(rendered_admin_url, database_name))
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = rendered_test_url
    config = Config(str(persistence_conftest.ROOT / "backend" / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        yield rendered_test_url
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        asyncio.run(persistence_conftest._drop_database(rendered_admin_url, database_name))

PHASE08_TABLES = {
    "volta_audit_events",
    "volta_intake_drafts",
    "volta_mandates",
    "volta_operation_status_history",
    "volta_operations",
    "volta_negotiations",
    "volta_carrier_sessions",
    "volta_pre_contact_escalations",
    "volta_quotes",
    "volta_commitments",
    "volta_mutation_idempotency",
}
PHASE14_TABLES = PHASE08_TABLES | {
    "volta_agreement_evidence",
    "volta_call_briefs",
    "volta_recaps",
    "volta_post_contact_escalations",
    "volta_recovery_attempts",
    "volta_notifications",
}
PRE_PHASE18_TABLES = PHASE14_TABLES | {
    "volta_evidence_reservations",
    "volta_text_mutation_idempotency",
}
PRE_PHASE28_TABLES = PRE_PHASE18_TABLES | {
    "volta_outbound_call_attempts",
    "volta_inbound_caller_correlations",
    "volta_inbound_call_attempts",
}
EXPECTED_TABLES = PRE_PHASE28_TABLES | {
    "volta_human_handoffs",
    "volta_ai_authority_fences",
    "volta_twilio_handoff_bindings",
}
PHASE06_TABLES = {
    "volta_audit_events",
    "volta_intake_drafts",
    "volta_mandates",
    "volta_operation_status_history",
    "volta_operations",
}
EXPECTED_CONSTRAINTS = {
    "volta_intake_drafts": {
        "pk_volta_intake_drafts",
        "ck_volta_intake_drafts_version_positive",
        "ck_volta_intake_drafts_amount_finite",
        "ck_volta_intake_drafts_validation_issues_array",
        "ck_volta_intake_drafts_approval_eligibility",
        "ck_volta_intake_drafts_cargo_label",
    },
    "volta_operations": {
        "pk_volta_operations",
        "fk_volta_operations_source_draft_id",
        "fk_volta_operations_active_mandate",
        "uq_volta_operations_source_draft_id",
        "ck_volta_operations_version_positive",
        "ck_volta_operations_source_draft_version_positive",
        "ck_volta_operations_cargo_label",
    },
    "volta_mandates": {
        "pk_volta_mandates",
        "fk_volta_mandates_operation_id",
        "uq_volta_mandates_operation_id_id",
        "uq_volta_mandates_operation_version",
        "ck_volta_mandates_version_positive",
        "ck_volta_mandates_amount_finite_non_negative",
        "ck_volta_mandates_pickup_window_order",
        "ck_volta_mandates_authorized_actions",
    },
    "volta_operation_status_history": {
        "pk_volta_operation_status_history",
        "fk_volta_operation_status_history_operation",
        "ck_volta_operation_status_history_version_positive",
        "ck_volta_operation_status_history_status",
    },
    "volta_audit_events": {
        "pk_volta_audit_events",
        "fk_volta_audit_events_operation",
        "ck_volta_audit_events_version_positive",
        "ck_volta_audit_events_actor_kind",
        "ck_volta_audit_events_event_type",
        "ck_volta_audit_events_metadata_object",
        "ck_volta_audit_events_metadata_size",
        "ck_volta_audit_events_metadata_schema",
    },
    "volta_negotiations": {
        "pk_volta_negotiations",
        "uq_volta_negotiations_operation",
        "uq_volta_negotiations_id_operation",
        "fk_volta_negotiations_operation",
        "ck_volta_negotiations_operation_version",
        "ck_volta_negotiations_mandate_version",
    },
    "volta_carrier_sessions": {
        "pk_volta_carrier_sessions",
        "uq_volta_sessions_negotiation_carrier",
        "uq_volta_sessions_call_operation_carrier",
        "uq_volta_sessions_call_operation",
        "fk_volta_sessions_negotiation_operation",
        "ck_volta_sessions_priority_positive",
        "ck_volta_sessions_rank",
        "ck_volta_sessions_channel",
        "ck_volta_sessions_state",
    },
    "volta_pre_contact_escalations": {
        "pk_volta_pre_contact_escalations",
        "uq_volta_pre_contact_escalations_operation",
        "fk_volta_pre_contact_escalations_negotiation_operation",
        "ck_volta_pre_contact_escalations_reason",
    },
    "volta_quotes": {
        "pk_volta_quotes",
        "uq_volta_quotes_id_operation",
        "uq_volta_quotes_identity_scope",
        "fk_volta_quotes_session_scope",
        "ck_volta_quotes_priority_positive",
        "ck_volta_quotes_mandate_version",
        "ck_volta_quotes_amount_finite",
        "ck_volta_quotes_window_order",
        "ck_volta_quotes_eligibility",
        "ck_volta_quotes_rejection_consistency",
    },
    "volta_commitments": {
        "pk_volta_commitments",
        "uq_volta_commitments_id_operation",
        "uq_volta_commitments_id_operation_call",
        "uq_volta_commitments_id_evidence",
        "uq_volta_commitments_quote",
        "fk_volta_commitments_quote_scope",
        "fk_volta_commitments_replaces_operation",
        "fk_volta_commitments_replaced_by_operation",
        "ck_volta_commitments_mandate_version",
        "ck_volta_commitments_amount_finite",
        "ck_volta_commitments_window_order",
        "ck_volta_commitments_lifecycle",
        "ck_volta_commitments_disposition",
        "ck_volta_commitments_disposition_state",
        "ck_volta_commitments_not_self_replacing",
        "ck_volta_commitments_not_self_replaced",
    },
    "volta_mutation_idempotency": {
        "pk_volta_mutation_idempotency",
        "uq_volta_mutation_idempotency_negotiation",
        "uq_volta_mutation_idempotency_quote",
        "uq_volta_mutation_idempotency_commitment",
        "fk_volta_mutation_idempotency_operation",
        "fk_volta_mutation_idempotency_negotiation_operation",
        "fk_volta_mutation_idempotency_quote_operation",
        "fk_volta_mutation_idempotency_commitment_operation",
        "ck_volta_mutation_idempotency_operation_name",
        "ck_volta_mutation_idempotency_result_mapping",
        "ck_volta_mutation_idempotency_key",
        "ck_volta_mutation_idempotency_fingerprint",
    },
    "volta_agreement_evidence": {
        "pk_volta_agreement_evidence",
        "uq_volta_agreement_evidence_commitment",
        "uq_volta_agreement_evidence_id_commitment",
        "fk_volta_agreement_evidence_commitment",
        "fk_volta_agreement_evidence_commitment_artifact",
        "ck_volta_agreement_evidence_audio_start_ms",
        "ck_volta_agreement_evidence_recording_reference",
        "ck_volta_agreement_evidence_item_id",
        "ck_volta_agreement_evidence_event_id",
    },
    "volta_evidence_reservations": {
        "pk_volta_evidence_reservations",
        "uq_volta_evidence_reservations_quote",
        "uq_volta_evidence_reservations_consumed_commitment",
        "fk_volta_evidence_reservations_quote_operation",
        "fk_volta_evidence_reservations_commitment_operation",
        "ck_volta_evidence_reservations_offset",
        "ck_volta_evidence_reservations_reference",
        "ck_volta_evidence_reservations_event_ids",
    },
    "volta_call_briefs": {
        "pk_volta_call_briefs",
        "uq_volta_call_briefs_commitment",
        "fk_volta_call_briefs_commitment_operation_call",
        "fk_volta_call_briefs_call_operation",
        "ck_volta_call_briefs_mandate_version",
        "ck_volta_call_briefs_structured_fields",
    },
    "volta_recaps": {
        "pk_volta_recaps",
        "uq_volta_recaps_commitment",
        "fk_volta_recaps_commitment_operation_call",
        "fk_volta_recaps_call_operation",
        "ck_volta_recaps_disclosure_state",
        "ck_volta_recaps_content",
    },
    "volta_post_contact_escalations": {
        "pk_volta_post_contact_escalations",
        "uq_volta_post_contact_escalations_id_operation",
        "fk_volta_post_contact_escalations_commitment_operation",
        "fk_volta_post_contact_escalations_call_operation",
        "ck_volta_post_contact_escalations_op_version",
        "ck_volta_post_contact_escalations_mandate_version",
        "ck_volta_post_contact_escalations_resolved_state",
        "ck_volta_post_contact_escalations_context",
    },
    "volta_recovery_attempts": {
        "pk_volta_recovery_attempts",
        "fk_volta_recovery_attempts_commitment_operation",
        "fk_volta_recovery_attempts_resulting_commitment_operation",
        "fk_volta_recovery_attempts_resulting_evidence_commitment",
        "fk_volta_recovery_attempts_escalation_operation",
        "ck_volta_recovery_attempts_outcome",
        "ck_volta_recovery_attempts_outcome_state",
        "ck_volta_recovery_attempts_complete_decision",
        "ck_volta_recovery_attempts_scenario_outcome",
    },
    "volta_notifications": {
        "pk_volta_notifications",
        "fk_volta_notifications_commitment_operation",
        "ck_volta_notifications_acknowledgement",
        "ck_volta_notifications_recovery_context",
    },
    "volta_text_mutation_idempotency": {
        "pk_volta_text_mutation_idempotency",
        "fk_volta_text_idempotency_draft",
        "fk_volta_text_idempotency_operation",
        "ck_volta_text_idempotency_operation_name",
        "ck_volta_text_idempotency_result_mapping",
        "ck_volta_text_idempotency_key",
        "ck_volta_text_idempotency_fingerprint",
        "ck_volta_text_idempotency_result_kind",
        "ck_volta_text_idempotency_result_snapshot",
    },
    "volta_outbound_call_attempts": {
        "pk_volta_outbound_call_attempts",
        "fk_volta_outbound_call_attempts_operation",
        "uq_volta_outbound_call_attempts_provider_call",
        "ck_volta_outbound_call_attempts_key",
        "ck_volta_outbound_call_attempts_fingerprint",
        "ck_volta_outbound_call_attempts_state",
        "ck_volta_outbound_call_attempts_payload",
        "ck_volta_outbound_call_attempts_call_status",
        "ck_volta_outbound_call_attempts_provider_call",
        "ck_volta_outbound_call_attempts_cursor",
        "ck_volta_outbound_call_attempts_processed_events",
        "ck_volta_outbound_call_attempts_uncertainty",
        "ck_volta_outbound_call_attempts_failure",
        "ck_volta_outbound_call_attempts_failure_status",
        "ck_volta_outbound_call_attempts_call_timestamps",
        "ck_volta_outbound_call_attempts_timestamps",
    },
    "volta_inbound_caller_correlations": {
        "pk_volta_inbound_caller_correlations",
        "fk_volta_inbound_caller_correlations_operation",
        "uq_volta_inbound_caller_correlations_caller_operation",
        "ck_volta_inbound_caller_correlations_label",
    },
    "volta_inbound_call_attempts": {
        "pk_volta_inbound_call_attempts",
        "uq_volta_inbound_call_attempts_provider_call",
        "fk_volta_inbound_attempt_operation",
        "fk_volta_inbound_attempt_commitment",
        "fk_volta_inbound_attempt_result_commitment",
        "fk_volta_inbound_attempt_result_evidence",
        "fk_volta_inbound_attempt_result_brief",
        "fk_volta_inbound_attempt_recovery",
        "ck_volta_inbound_attempt_status",
        "ck_volta_inbound_attempt_identifiers",
        "ck_volta_inbound_attempt_payload",
    },
    "volta_human_handoffs": {
        "pk_volta_human_handoffs",
        "uq_volta_human_handoffs_idempotency",
        "fk_volta_handoffs_operation",
        "ck_volta_handoffs_key",
        "ck_volta_handoffs_fingerprint",
        "ck_volta_handoffs_operation_version",
        "ck_volta_handoffs_status",
        "ck_volta_handoffs_context",
        "ck_volta_handoffs_processed_events",
        "ck_volta_handoffs_cursor",
        "ck_volta_handoffs_timestamps",
    },
    "volta_ai_authority_fences": {
        "pk_volta_ai_authority_fences",
        "uq_volta_fence_handoff",
        "fk_volta_fence_handoff",
    },
    "volta_twilio_handoff_bindings": {
        "pk_volta_twilio_handoff_bindings",
        "fk_volta_twilio_binding_handoff",
        "uq_volta_twilio_binding_conference_name",
        "uq_volta_twilio_binding_conference_sid",
        "uq_volta_twilio_binding_coordinator_call",
        "ck_volta_twilio_binding_sids",
        "ck_volta_twilio_binding_sequences",
    },
}


async def _schema_evidence(database_url: str) -> dict[str, object]:
    engine = create_async_engine(database_url, hide_parameters=True)
    try:
        async with engine.connect() as connection:
            tables = await connection.run_sync(
                lambda sync_connection: {
                    table
                    for table in inspect(sync_connection).get_table_names()
                    if table.startswith("volta_")
                }
            )
            constraints = await connection.run_sync(
                lambda sync_connection: {
                    table: {
                        inspect(sync_connection).get_pk_constraint(table)["name"],
                        *(
                            item["name"]
                            for item in inspect(sync_connection).get_foreign_keys(table)
                        ),
                        *(
                            item["name"]
                            for item in inspect(sync_connection).get_unique_constraints(table)
                        ),
                        *(
                            item["name"]
                            for item in inspect(sync_connection).get_check_constraints(table)
                        ),
                    }
                    for table in EXPECTED_TABLES
                }
            )
            indexes = await connection.run_sync(
                lambda sync_connection: {
                    table: {item["name"] for item in inspect(sync_connection).get_indexes(table)}
                    for table in EXPECTED_TABLES
                }
            )
            active_fk = (
                await connection.execute(
                    text(
                        "SELECT condeferrable, condeferred FROM pg_constraint "
                        "WHERE conname = 'fk_volta_operations_active_mandate'"
                    )
                )
            ).one()
            trigger_count = (
                await connection.execute(
                    text(
                        "SELECT count(*) FROM pg_trigger "
                        "WHERE tgname IN ('trg_volta_status_history_append_only', "
                        "'trg_volta_audit_events_append_only') AND NOT tgisinternal"
                    )
                )
            ).scalar_one()
        return {
            "tables": tables,
            "constraints": constraints,
            "indexes": indexes,
            "active_fk": tuple(active_fk),
            "trigger_count": trigger_count,
        }
    finally:
        await engine.dispose()


async def _volta_tables_and_function(database_url: str) -> tuple[set[str], str | None]:
    engine = create_async_engine(database_url, hide_parameters=True)
    try:
        async with engine.connect() as connection:
            tables = await connection.run_sync(
                lambda sync_connection: {
                    table
                    for table in inspect(sync_connection).get_table_names()
                    if table.startswith("volta_")
                }
            )
            function = (
                await connection.execute(
                    text("SELECT to_regprocedure('volta_reject_append_only_mutation()')::text")
                )
            ).scalar_one_or_none()
        return tables, function
    finally:
        await engine.dispose()


async def _insert_phase06_sentinel(database_url: str) -> None:
    engine = create_async_engine(database_url, hide_parameters=True)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO volta_intake_drafts "
                    "(id, source_prompt, requested_language, extraction_policy_version, "
                    "route_origin, route_destination, pickup_date, maximum_amount, currency, "
                    "cargo_label, "
                    "pickup_window_start_date, pickup_window_end_date, allowed_conditions, "
                    "escalation_conditions, validation_issues, approval_eligible, version, "
                    "created_at, updated_at) VALUES "
                    "('00000000-0000-0000-0000-00000000f006', 'synthetic', 'EN_US', "
                    "'intake-v1', 'A', 'B', '2026-09-01', 1, 'MXN', "
                    "'Synthetic drayage cargo', '2026-09-01', "
                    "'2026-09-01', ARRAY[]::text[], ARRAY[]::text[], '[]'::jsonb, true, 1, "
                    "'2026-09-01T12:00:00Z', '2026-09-01T12:00:00Z')"
                )
            )
    finally:
        await engine.dispose()


async def _phase06_preservation(database_url: str) -> tuple[int, str]:
    engine = create_async_engine(database_url, hide_parameters=True)
    try:
        async with engine.connect() as connection:
            sentinel_count = (
                await connection.execute(
                    text(
                        "SELECT count(*) FROM volta_intake_drafts "
                        "WHERE id = '00000000-0000-0000-0000-00000000f006'"
                    )
                )
            ).scalar_one()
            definition = (
                await connection.execute(
                    text(
                        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conname = 'ck_volta_audit_events_metadata_schema'"
                    )
                )
            ).scalar_one()
        return sentinel_count, definition
    finally:
        await engine.dispose()


def test_upgrade_downgrade_upgrade_is_reversible_and_schema_is_named(
    isolated_database_url: str,
    alembic_config: Config,
) -> None:
    evidence = asyncio.run(_schema_evidence(isolated_database_url))
    assert evidence["tables"] == EXPECTED_TABLES
    assert evidence["constraints"] == EXPECTED_CONSTRAINTS
    assert evidence["active_fk"] == (True, True)
    assert evidence["trigger_count"] == 2
    indexes = evidence["indexes"]
    assert indexes["volta_operation_status_history"] == {  # type: ignore[index]
        "ix_volta_operation_status_history_ordered"
    }
    assert indexes["volta_audit_events"] == {  # type: ignore[index]
        "ix_volta_audit_events_correlation_id",
        "ix_volta_audit_events_operation_ordered",
    }
    assert indexes["volta_carrier_sessions"] == {  # type: ignore[index]
        "ix_volta_sessions_negotiation",
        "uq_volta_sessions_call_operation_carrier",
        "uq_volta_sessions_call_operation",
        "uq_volta_sessions_negotiation_carrier",
    }
    assert indexes["volta_pre_contact_escalations"] == {  # type: ignore[index]
        "ix_volta_pre_contact_escalations_negotiation",
        "uq_volta_pre_contact_escalations_operation",
    }
    assert indexes["volta_quotes"] == {  # type: ignore[index]
        "ix_volta_quotes_call",
        "ix_volta_quotes_operation_comparison",
        "uq_volta_quotes_identity_scope",
        "uq_volta_quotes_id_operation",
    }
    assert indexes["volta_commitments"] == {  # type: ignore[index]
        "ix_volta_commitments_operation_history",
        "ix_volta_commitments_replaced_by",
        "ix_volta_commitments_replaces",
        "uq_volta_commitments_one_active",
        "uq_volta_commitments_quote",
        "uq_volta_commitments_id_operation",
        "uq_volta_commitments_id_operation_call",
        "uq_volta_commitments_id_evidence",
    }
    assert indexes["volta_mutation_idempotency"] == {  # type: ignore[index]
        "ix_volta_mutation_idempotency_operation",
        "ix_volta_mutation_idempotency_negotiation",
        "ix_volta_mutation_idempotency_quote",
        "ix_volta_mutation_idempotency_commitment",
        "uq_volta_mutation_idempotency_negotiation",
        "uq_volta_mutation_idempotency_quote",
        "uq_volta_mutation_idempotency_commitment",
    }
    assert indexes["volta_agreement_evidence"] == {  # type: ignore[index]
        "uq_volta_agreement_evidence_commitment",
        "uq_volta_agreement_evidence_id_commitment",
    }
    assert indexes["volta_call_briefs"] == {  # type: ignore[index]
        "ix_volta_call_briefs_operation_order",
        "uq_volta_call_briefs_commitment",
    }
    assert indexes["volta_recaps"] == {  # type: ignore[index]
        "ix_volta_recaps_operation_order",
        "uq_volta_recaps_commitment",
    }
    assert indexes["volta_post_contact_escalations"] == {  # type: ignore[index]
        "ix_volta_post_contact_escalations_call",
        "ix_volta_post_contact_escalations_operation_order",
        "uq_volta_post_contact_escalations_one_unresolved",
        "uq_volta_post_contact_escalations_id_operation",
    }
    assert indexes["volta_recovery_attempts"] == {  # type: ignore[index]
        "ix_volta_recovery_attempts_operation"
    }
    assert indexes["volta_notifications"] == {  # type: ignore[index]
        "ix_volta_notifications_operation_order",
    }
    assert indexes["volta_text_mutation_idempotency"] == {  # type: ignore[index]
        "ix_volta_text_idempotency_draft",
        "ix_volta_text_idempotency_operation",
    }
    assert indexes["volta_outbound_call_attempts"] == {  # type: ignore[index]
        "ix_volta_outbound_call_attempts_operation",
        "uq_volta_outbound_call_attempts_provider_call",
    }
    assert indexes["volta_inbound_caller_correlations"] == {  # type: ignore[index]
        "ix_volta_inbound_caller_correlations_label",
        "uq_volta_inbound_caller_correlations_caller_operation",
    }
    assert indexes["volta_inbound_call_attempts"] == {  # type: ignore[index]
        "uq_volta_inbound_attempt_one_active_operation",
        "uq_volta_inbound_call_attempts_provider_call",
    }
    assert indexes["volta_human_handoffs"] == {  # type: ignore[index]
        "ix_volta_handoffs_call",
        "ix_volta_handoffs_operation",
        "uq_volta_handoffs_one_connecting_per_call",
        "uq_volta_human_handoffs_idempotency",
    }
    assert indexes["volta_ai_authority_fences"] == {  # type: ignore[index]
        "uq_volta_fence_handoff"
    }
    assert indexes["volta_twilio_handoff_bindings"] == {  # type: ignore[index]
        "uq_volta_twilio_binding_conference_name",
        "uq_volta_twilio_binding_conference_sid",
        "uq_volta_twilio_binding_coordinator_call",
    }

    command.downgrade(alembic_config, "-1")
    tables_after_one_downgrade, _ = asyncio.run(_volta_tables_and_function(isolated_database_url))
    assert tables_after_one_downgrade == PRE_PHASE28_TABLES
    _, phase14_audit_definition = asyncio.run(_phase06_preservation(isolated_database_url))
    assert "COMMITMENT_SUPERSEDED" in phase14_audit_definition
    assert "EVIDENCE_RECORDED" in phase14_audit_definition

    command.upgrade(alembic_config, "head")
    assert asyncio.run(_schema_evidence(isolated_database_url))["tables"] == EXPECTED_TABLES

    asyncio.run(_insert_phase06_sentinel(isolated_database_url))
    command.downgrade(alembic_config, "20260829_06")
    tables, function = asyncio.run(_volta_tables_and_function(isolated_database_url))
    assert tables == PHASE06_TABLES
    assert function == "volta_reject_append_only_mutation()"
    sentinel_count, audit_definition = asyncio.run(_phase06_preservation(isolated_database_url))
    assert sentinel_count == 1
    assert "event_type <> 'OPERATION_APPROVED'" in audit_definition

    command.upgrade(alembic_config, "head")
    assert asyncio.run(_schema_evidence(isolated_database_url))["tables"] == EXPECTED_TABLES


def test_text_slice_migration_backfills_existing_synthetic_draft(
    isolated_database_url: str,
    alembic_config: Config,
) -> None:
    command.downgrade(alembic_config, "20260829_08")

    async def insert_sentinel() -> None:
        engine = create_async_engine(isolated_database_url, hide_parameters=True)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "INSERT INTO volta_intake_drafts "
                        "(id, source_prompt, requested_language, extraction_policy_version, "
                        "route_origin, route_destination, pickup_date, maximum_amount, currency, "
                        "pickup_window_start_date, pickup_window_end_date, allowed_conditions, "
                        "escalation_conditions, validation_issues, approval_eligible, version, "
                        "created_at, updated_at) VALUES "
                        "('00000000-0000-0000-0000-00000000f010', "
                        "'Move one 40-foot container', 'EN_US', 'intake-v1', 'A', 'B', "
                        "'2026-09-03', 9000, 'MXN', '2026-09-03', '2026-09-03', "
                        "ARRAY[]::text[], ARRAY[]::text[], '[]'::jsonb, true, 1, "
                        "'2026-09-01T12:00:00Z', '2026-09-01T12:00:00Z')"
                    )
                )
                await connection.execute(
                    text(
                        "INSERT INTO volta_intake_drafts "
                        "(id, source_prompt, requested_language, extraction_policy_version, "
                        "route_origin, route_destination, pickup_date, maximum_amount, currency, "
                        "pickup_window_start_date, pickup_window_end_date, allowed_conditions, "
                        "escalation_conditions, validation_issues, approval_eligible, version, "
                        "created_at, updated_at) VALUES "
                        "('00000000-0000-0000-0000-00000000f011', "
                        "'Move one refrigerated container', 'EN_US', 'intake-v1', 'A', 'B', "
                        "'2026-09-03', 9000, 'MXN', '2026-09-03', '2026-09-03', "
                        "ARRAY[]::text[], ARRAY[]::text[], '[]'::jsonb, true, 1, "
                        "'2026-09-01T12:00:00Z', '2026-09-01T12:00:00Z')"
                    )
                )
        finally:
            await engine.dispose()

    async def read_labels() -> tuple[str, str]:
        engine = create_async_engine(isolated_database_url, hide_parameters=True)
        try:
            async with engine.connect() as connection:
                rows = (
                    await connection.execute(
                        text(
                            "SELECT cargo_label FROM volta_intake_drafts "
                            "WHERE id IN "
                            "('00000000-0000-0000-0000-00000000f010', "
                            "'00000000-0000-0000-0000-00000000f011') ORDER BY id"
                        )
                    )
                ).scalars()
                return tuple(rows)  # type: ignore[return-value]
        finally:
            await engine.dispose()

    asyncio.run(insert_sentinel())
    command.upgrade(alembic_config, "head")
    assert asyncio.run(read_labels()) == (
        "40ft dry container",
        "Synthetic drayage cargo (migrated)",
    )

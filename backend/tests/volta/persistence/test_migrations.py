from __future__ import annotations

import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

EXPECTED_TABLES = {
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
    },
    "volta_operations": {
        "pk_volta_operations",
        "fk_volta_operations_source_draft_id",
        "fk_volta_operations_active_mandate",
        "uq_volta_operations_source_draft_id",
        "ck_volta_operations_version_positive",
        "ck_volta_operations_source_draft_version_positive",
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
                    "pickup_window_start_date, pickup_window_end_date, allowed_conditions, "
                    "escalation_conditions, validation_issues, approval_eligible, version, "
                    "created_at, updated_at) VALUES "
                    "('00000000-0000-0000-0000-00000000f006', 'synthetic', 'EN_US', "
                    "'intake-v1', 'A', 'B', '2026-09-01', 1, 'MXN', '2026-09-01', "
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

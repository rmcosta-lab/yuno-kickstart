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
                    table: {
                        item["name"] for item in inspect(sync_connection).get_indexes(table)
                    }
                    for table in EXPECTED_TABLES
                }
            )
            active_fk = (await connection.execute(
                text(
                    "SELECT condeferrable, condeferred FROM pg_constraint "
                    "WHERE conname = 'fk_volta_operations_active_mandate'"
                )
            )).one()
            trigger_count = (await connection.execute(
                text(
                    "SELECT count(*) FROM pg_trigger "
                    "WHERE tgname IN ('trg_volta_status_history_append_only', "
                    "'trg_volta_audit_events_append_only') AND NOT tgisinternal"
                )
            )).scalar_one()
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
            function = (await connection.execute(
                text("SELECT to_regprocedure('volta_reject_append_only_mutation()')::text")
            )).scalar_one_or_none()
        return tables, function
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

    command.downgrade(alembic_config, "base")
    tables, function = asyncio.run(_volta_tables_and_function(isolated_database_url))
    assert tables == set()
    assert function is None

    command.upgrade(alembic_config, "head")
    assert asyncio.run(_schema_evidence(isolated_database_url))["tables"] == EXPECTED_TABLES

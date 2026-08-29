"""Create the initial append-only Volta persistence schema.

Revision ID: 20260829_06
Revises:
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260829_06"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "volta_intake_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_prompt", sa.Text(), nullable=False),
        sa.Column("requested_language", sa.Text(), nullable=False),
        sa.Column("extraction_policy_version", sa.Text(), nullable=False),
        sa.Column("route_origin", sa.Text(), nullable=False),
        sa.Column("route_destination", sa.Text(), nullable=False),
        sa.Column("pickup_date", sa.Date(), nullable=False),
        sa.Column("maximum_amount", sa.Numeric(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("pickup_window_start_date", sa.Date(), nullable=False),
        sa.Column("pickup_window_end_date", sa.Date(), nullable=False),
        sa.Column("allowed_conditions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("escalation_conditions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("validation_issues", postgresql.JSONB(), nullable=False),
        sa.Column("approval_eligible", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_intake_drafts"),
        sa.CheckConstraint(
            "version > 0", name="ck_volta_intake_drafts_version_positive"
        ),
        sa.CheckConstraint(
            "maximum_amount > '-Infinity'::numeric "
            "AND maximum_amount < 'Infinity'::numeric",
            name="ck_volta_intake_drafts_amount_finite",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(validation_issues) = 'array'",
            name="ck_volta_intake_drafts_validation_issues_array",
        ),
        sa.CheckConstraint(
            "approval_eligible = (jsonb_array_length(validation_issues) = 0)",
            name="ck_volta_intake_drafts_approval_eligibility",
        ),
    )
    op.create_table(
        "volta_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_draft_version", sa.Integer(), nullable=False),
        sa.Column("route_origin", sa.Text(), nullable=False),
        sa.Column("route_destination", sa.Text(), nullable=False),
        sa.Column("pickup_date", sa.Date(), nullable=False),
        sa.Column("active_mandate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_operations"),
        sa.ForeignKeyConstraint(
            ["source_draft_id"],
            ["volta_intake_drafts.id"],
            name="fk_volta_operations_source_draft_id",
        ),
        sa.UniqueConstraint(
            "source_draft_id", name="uq_volta_operations_source_draft_id"
        ),
        sa.CheckConstraint("version > 0", name="ck_volta_operations_version_positive"),
        sa.CheckConstraint(
            "source_draft_version > 0",
            name="ck_volta_operations_source_draft_version_positive",
        ),
    )
    op.create_table(
        "volta_mandates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("maximum_amount", sa.Numeric(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("pickup_window_start_date", sa.Date(), nullable=False),
        sa.Column("pickup_window_end_date", sa.Date(), nullable=False),
        sa.Column("allowed_conditions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("escalation_conditions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("authorized_actions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("approval_actor", sa.Text(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_mandates"),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["volta_operations.id"],
            name="fk_volta_mandates_operation_id",
        ),
        sa.UniqueConstraint(
            "operation_id", "id", name="uq_volta_mandates_operation_id_id"
        ),
        sa.UniqueConstraint(
            "operation_id", "version", name="uq_volta_mandates_operation_version"
        ),
        sa.CheckConstraint("version > 0", name="ck_volta_mandates_version_positive"),
        sa.CheckConstraint(
            "maximum_amount >= 0 AND maximum_amount < 'Infinity'::numeric",
            name="ck_volta_mandates_amount_finite_non_negative",
        ),
        sa.CheckConstraint(
            "pickup_window_end_date >= pickup_window_start_date",
            name="ck_volta_mandates_pickup_window_order",
        ),
        sa.CheckConstraint(
            "cardinality(authorized_actions) > 0 "
            "AND authorized_actions <@ ARRAY['NEGOTIATE', 'COMMIT']::text[]",
            name="ck_volta_mandates_authorized_actions",
        ),
    )
    op.create_foreign_key(
        "fk_volta_operations_active_mandate",
        "volta_operations",
        "volta_mandates",
        ["id", "active_mandate_id"],
        ["operation_id", "id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_table(
        "volta_operation_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_operation_status_history"),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["volta_operations.id"],
            name="fk_volta_operation_status_history_operation",
        ),
        sa.CheckConstraint(
            "operation_version > 0",
            name="ck_volta_operation_status_history_version_positive",
        ),
        sa.CheckConstraint(
            "status IN ('READY', 'NEGOTIATING', 'COMMITTED', 'ESCALATED', 'COMPLETED')",
            name="ck_volta_operation_status_history_status",
        ),
    )
    op.create_index(
        "ix_volta_operation_status_history_ordered",
        "volta_operation_status_history",
        ["operation_id", "occurred_at", "id"],
    )
    op.create_table(
        "volta_audit_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_version", sa.Integer(), nullable=False),
        sa.Column("actor_kind", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("event_id", name="pk_volta_audit_events"),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["volta_operations.id"],
            name="fk_volta_audit_events_operation",
        ),
        sa.CheckConstraint(
            "operation_version > 0", name="ck_volta_audit_events_version_positive"
        ),
        sa.CheckConstraint(
            "actor_kind IN ('COORDINATOR', 'CARRIER_SIMULATOR', 'SYSTEM')",
            name="ck_volta_audit_events_actor_kind",
        ),
        sa.CheckConstraint(
            "event_type ~ '^[A-Z][A-Z0-9_]{0,63}$'",
            name="ck_volta_audit_events_event_type",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_volta_audit_events_metadata_object",
        ),
        sa.CheckConstraint(
            "octet_length(metadata::text) <= 8192",
            name="ck_volta_audit_events_metadata_size",
        ),
        sa.CheckConstraint(
            "(event_type = 'OPERATION_APPROVED' AND (metadata = '{}'::jsonb OR "
            "(metadata = jsonb_build_object('draft_version', "
            "metadata -> 'draft_version') AND "
            "jsonb_typeof(metadata -> 'draft_version') = 'number' AND "
            "metadata ->> 'draft_version' ~ '^(0|[1-9][0-9]{0,15})$' AND "
            "(char_length(metadata ->> 'draft_version') < 16 OR "
            "(char_length(metadata ->> 'draft_version') = 16 AND "
            "metadata ->> 'draft_version' <= '9007199254740991')))) "
            ") OR "
            "(event_type <> 'OPERATION_APPROVED' AND metadata = '{}'::jsonb)",
            name="ck_volta_audit_events_metadata_schema",
        ),
    )
    op.create_index(
        "ix_volta_audit_events_operation_ordered",
        "volta_audit_events",
        ["operation_id", "occurred_at", "event_id"],
    )
    op.create_index(
        "ix_volta_audit_events_correlation_id",
        "volta_audit_events",
        ["correlation_id"],
    )
    op.execute(
        """
        CREATE FUNCTION volta_reject_append_only_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'volta append-only history cannot be modified'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_volta_status_history_append_only
        BEFORE UPDATE OR DELETE ON volta_operation_status_history
        FOR EACH ROW EXECUTE FUNCTION volta_reject_append_only_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_volta_audit_events_append_only
        BEFORE UPDATE OR DELETE ON volta_audit_events
        FOR EACH ROW EXECUTE FUNCTION volta_reject_append_only_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_volta_audit_events_append_only ON volta_audit_events")
    op.execute(
        "DROP TRIGGER trg_volta_status_history_append_only "
        "ON volta_operation_status_history"
    )
    op.execute("DROP FUNCTION volta_reject_append_only_mutation()")
    op.drop_index("ix_volta_audit_events_correlation_id", table_name="volta_audit_events")
    op.drop_index(
        "ix_volta_audit_events_operation_ordered", table_name="volta_audit_events"
    )
    op.drop_table("volta_audit_events")
    op.drop_index(
        "ix_volta_operation_status_history_ordered",
        table_name="volta_operation_status_history",
    )
    op.drop_table("volta_operation_status_history")
    op.drop_constraint(
        "fk_volta_operations_active_mandate",
        "volta_operations",
        type_="foreignkey",
    )
    op.drop_table("volta_mandates")
    op.drop_table("volta_operations")
    op.drop_table("volta_intake_drafts")

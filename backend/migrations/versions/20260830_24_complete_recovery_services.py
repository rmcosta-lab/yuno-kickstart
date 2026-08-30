"""Complete mandate, escalation, and notification recovery persistence.

Revision ID: 20260830_24
Revises: 20260829_10
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830_24"
down_revision: str | None = "20260829_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PHASE14_METADATA_SCHEMA = (
    "(event_type = 'OPERATION_APPROVED' AND (metadata = '{}'::jsonb OR "
    "(metadata = jsonb_build_object('draft_version', metadata -> 'draft_version') "
    "AND jsonb_typeof(metadata -> 'draft_version') = 'number' AND "
    "metadata ->> 'draft_version' ~ '^(0|[1-9][0-9]{0,15})$' AND "
    "(char_length(metadata ->> 'draft_version') < 16 OR "
    "(char_length(metadata ->> 'draft_version') = 16 AND "
    "metadata ->> 'draft_version' <= '9007199254740991'))))) OR "
    "(event_type IN ('NEGOTIATION_STARTED', 'PRE_CONTACT_ESCALATED', "
    "'QUOTE_RECORDED', 'QUOTE_REJECTED', 'COMMITMENT_ACTIVATED', "
    "'COMMITMENT_SUPERSEDED', 'EVIDENCE_RECORDED', 'BRIEF_GENERATED', "
    "'RECAP_GENERATED', 'RECOVERY_REPLACEMENT_APPLIED', 'POST_CONTACT_ESCALATED', "
    "'ESCALATION_RESUMED') AND metadata = '{}'::jsonb)"
)

_PHASE24_METADATA_SCHEMA = _PHASE14_METADATA_SCHEMA[:-1] + (
    " OR (event_type IN ('MANDATE_REPLACED', 'ESCALATION_RESOLVED', "
    "'EXPLICIT_ESCALATION_CREATED', 'NOTIFICATION_ACKNOWLEDGED') "
    "AND metadata = '{}'::jsonb))"
)

_PHASE24_AUDIT_EVENTS = (
    "MANDATE_REPLACED",
    "ESCALATION_RESOLVED",
    "EXPLICIT_ESCALATION_CREATED",
    "NOTIFICATION_ACKNOWLEDGED",
)


def _require_data_reconciliation_before_downgrade() -> None:
    """Fail before DDL when the older schema cannot represent phase-24 data."""
    bind = op.get_bind()
    has_incompatible_data = bind.execute(
        sa.text(
            "SELECT "
            "EXISTS ("
            "SELECT 1 FROM volta_post_contact_escalations "
            "WHERE commitment_id IS NULL OR call_id IS NOT NULL "
            "OR conflict IS NOT NULL OR attempted_alternatives IS NOT NULL "
            "OR recommended_action IS NOT NULL"
            ") OR EXISTS ("
            "SELECT 1 FROM volta_notifications "
            "WHERE operation_version IS NOT NULL OR recovery_before IS NOT NULL "
            "OR recovery_after IS NOT NULL OR decision_reason IS NOT NULL "
            "OR message IS NOT NULL OR correlation_id IS NOT NULL "
            "OR acknowledged_by IS NOT NULL OR acknowledged_at IS NOT NULL"
            ") OR EXISTS ("
            "SELECT 1 FROM volta_audit_events "
            "WHERE event_type IN :phase24_audit_events"
            ")"
        ).bindparams(sa.bindparam("phase24_audit_events", expanding=True)),
        {"phase24_audit_events": _PHASE24_AUDIT_EVENTS},
    ).scalar_one()
    if has_incompatible_data:
        raise RuntimeError(
            "cannot downgrade phase 24 while phase-24 recovery data exists; "
            "reconcile data under an approved retention procedure first"
        )


def upgrade() -> None:
    op.drop_constraint(
        "ck_volta_audit_events_metadata_schema", "volta_audit_events", type_="check"
    )
    op.create_check_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        _PHASE24_METADATA_SCHEMA,
    )

    op.alter_column(
        "volta_post_contact_escalations",
        "commitment_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "volta_post_contact_escalations",
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "volta_post_contact_escalations", sa.Column("conflict", sa.Text(), nullable=True)
    )
    op.add_column(
        "volta_post_contact_escalations",
        sa.Column("attempted_alternatives", postgresql.ARRAY(sa.Text()), nullable=True),
    )
    op.add_column(
        "volta_post_contact_escalations",
        sa.Column("recommended_action", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_volta_sessions_call_operation",
        "volta_carrier_sessions",
        ["call_id", "operation_id"],
    )
    op.create_foreign_key(
        "fk_volta_post_contact_escalations_call_operation",
        "volta_post_contact_escalations",
        "volta_carrier_sessions",
        ["call_id", "operation_id"],
        ["call_id", "operation_id"],
    )
    op.execute(
        """
        CREATE FUNCTION volta_bounded_text_array(items text[])
        RETURNS boolean
        LANGUAGE sql
        IMMUTABLE
        PARALLEL SAFE
        AS $$
            SELECT COALESCE(
                bool_and(
                    value IS NOT NULL
                    AND char_length(btrim(value)) BETWEEN 1 AND 500
                ),
                TRUE
            )
            FROM unnest(items) AS value
        $$
        """
    )
    op.create_check_constraint(
        "ck_volta_post_contact_escalations_context",
        "volta_post_contact_escalations",
        "(call_id IS NULL AND conflict IS NULL AND attempted_alternatives IS NULL "
        "AND recommended_action IS NULL) OR "
        "(call_id IS NOT NULL AND conflict IS NOT NULL AND attempted_alternatives IS NOT NULL "
        "AND char_length(btrim(conflict)) BETWEEN 1 AND 500 "
        "AND cardinality(attempted_alternatives) <= 25 "
        "AND volta_bounded_text_array(attempted_alternatives) "
        "AND recommended_action IS NOT NULL "
        "AND char_length(btrim(recommended_action)) BETWEEN 1 AND 500)",
    )
    op.create_index(
        "ix_volta_post_contact_escalations_call",
        "volta_post_contact_escalations",
        ["call_id"],
        postgresql_where=sa.text("call_id IS NOT NULL"),
    )
    for name, column_type in (
        ("operation_version", sa.Integer()),
        ("recovery_before", postgresql.JSONB(astext_type=sa.Text())),
        ("recovery_after", postgresql.JSONB(astext_type=sa.Text())),
        ("decision_reason", sa.Text()),
        ("message", sa.Text()),
        ("correlation_id", postgresql.UUID(as_uuid=True)),
        ("acknowledged_by", sa.Text()),
        ("acknowledged_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("volta_notifications", sa.Column(name, column_type, nullable=True))
    op.create_check_constraint(
        "ck_volta_notifications_acknowledgement",
        "volta_notifications",
        "(acknowledged_by IS NULL AND acknowledged_at IS NULL) OR "
        "(char_length(btrim(acknowledged_by)) BETWEEN 1 AND 500 "
        "AND acknowledged_at IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_volta_notifications_recovery_context",
        "volta_notifications",
        "(operation_version IS NULL AND recovery_before IS NULL AND recovery_after IS NULL "
        "AND decision_reason IS NULL AND message IS NULL AND correlation_id IS NULL) OR "
        "(operation_version > 0 AND recovery_before IS NOT NULL "
        "AND recovery_after IS NOT NULL AND decision_reason IS NOT NULL "
        "AND message IS NOT NULL AND correlation_id IS NOT NULL "
        "AND jsonb_typeof(recovery_before) = 'object' "
        "AND jsonb_typeof(recovery_after) = 'object' "
        "AND char_length(btrim(decision_reason)) BETWEEN 1 AND 500 "
        "AND char_length(btrim(message)) BETWEEN 1 AND 500)",
    )
def downgrade() -> None:
    _require_data_reconciliation_before_downgrade()
    op.drop_constraint(
        "ck_volta_notifications_recovery_context", "volta_notifications", type_="check"
    )
    op.drop_constraint(
        "ck_volta_notifications_acknowledgement", "volta_notifications", type_="check"
    )
    for name in (
        "acknowledged_at",
        "acknowledged_by",
        "correlation_id",
        "message",
        "decision_reason",
        "recovery_after",
        "recovery_before",
        "operation_version",
    ):
        op.drop_column("volta_notifications", name)

    op.drop_index(
        "ix_volta_post_contact_escalations_call",
        table_name="volta_post_contact_escalations",
    )
    op.drop_constraint(
        "ck_volta_post_contact_escalations_context",
        "volta_post_contact_escalations",
        type_="check",
    )
    op.execute("DROP FUNCTION volta_bounded_text_array(text[])")
    op.drop_constraint(
        "fk_volta_post_contact_escalations_call_operation",
        "volta_post_contact_escalations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_volta_sessions_call_operation",
        "volta_carrier_sessions",
        type_="unique",
    )
    op.drop_column("volta_post_contact_escalations", "recommended_action")
    op.drop_column("volta_post_contact_escalations", "attempted_alternatives")
    op.drop_column("volta_post_contact_escalations", "conflict")
    op.drop_column("volta_post_contact_escalations", "call_id")
    op.alter_column(
        "volta_post_contact_escalations",
        "commitment_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    op.drop_constraint(
        "ck_volta_audit_events_metadata_schema", "volta_audit_events", type_="check"
    )
    op.create_check_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        _PHASE14_METADATA_SCHEMA,
    )

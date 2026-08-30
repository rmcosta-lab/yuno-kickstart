"""Add durable human-handoff reservation, callback state, and AI fence.

Revision ID: 20260830_28
Revises: 20260830_27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830_28"
down_revision: str | None = "20260830_27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_data_reconciliation_before_downgrade() -> None:
    """Refuse before DDL when Phase 28 durable evidence cannot be represented."""

    has_incompatible_data = op.get_bind().execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM volta_human_handoffs) OR EXISTS ("
            "SELECT 1 FROM volta_audit_events WHERE event_type IN ("
            "'HANDOFF_REQUESTED', 'HANDOFF_JOINED', 'HANDOFF_FAILED_SAFE', "
            "'HANDOFF_TIMED_OUT_SAFE'))"
        )
    ).scalar_one()
    if has_incompatible_data:
        raise RuntimeError(
            "phase 28 downgrade refused: reconcile durable handoff evidence first"
        )


def upgrade() -> None:
    op.drop_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
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
        "'ESCALATION_RESUMED', 'MANDATE_REPLACED', 'ESCALATION_RESOLVED', "
        "'EXPLICIT_ESCALATION_CREATED', 'NOTIFICATION_ACKNOWLEDGED', "
        "'HANDOFF_REQUESTED', 'HANDOFF_JOINED', 'HANDOFF_FAILED_SAFE', "
        "'HANDOFF_TIMED_OUT_SAFE', 'INBOUND_CALL_ACCEPTED', "
        "'INBOUND_CONSENT_RECORDED', 'INBOUND_RECOVERY_COMPLETED') "
        "AND metadata = '{}'::jsonb)",
    )
    op.create_table(
        "volta_human_handoffs",
        sa.Column("handoff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_version", sa.Integer(), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coordinator_destination_label", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("request_fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("last_status_event_id", sa.Text(), nullable=True),
        sa.Column("last_status_sequence_number", sa.BigInteger(), nullable=True),
        sa.Column("processed_status_event_ids", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("handoff_id", name="pk_volta_human_handoffs"),
        sa.UniqueConstraint("idempotency_key", name="uq_volta_human_handoffs_idempotency"),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["volta_operations.id"], name="fk_volta_handoffs_operation"
        ),
        sa.CheckConstraint(
            "char_length(idempotency_key) BETWEEN 8 AND 128 AND idempotency_key ~ '^[ -~]+$'",
            name="ck_volta_handoffs_key",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_volta_handoffs_fingerprint"
        ),
        sa.CheckConstraint(
            "operation_version > 0", name="ck_volta_handoffs_operation_version"
        ),
        sa.CheckConstraint(
            "status IN ('CONNECTING', 'JOINED', 'FAILED_SAFE', 'TIMED_OUT_SAFE')",
            name="ck_volta_handoffs_status",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(context) = 'object' AND octet_length(context::text) <= 16384",
            name="ck_volta_handoffs_context",
        ),
        sa.CheckConstraint(
            "cardinality(processed_status_event_ids) <= 128",
            name="ck_volta_handoffs_processed_events",
        ),
        sa.CheckConstraint(
            "(last_status_event_id IS NULL AND last_status_sequence_number IS NULL) OR "
            "(last_status_event_id IS NOT NULL AND last_status_sequence_number >= 0 "
            "AND last_status_event_id = ANY(processed_status_event_ids))",
            name="ck_volta_handoffs_cursor",
        ),
        sa.CheckConstraint(
            "status_updated_at >= requested_at", name="ck_volta_handoffs_timestamps"
        ),
    )
    op.create_index("ix_volta_handoffs_call", "volta_human_handoffs", ["call_id"])
    op.create_index(
        "ix_volta_handoffs_operation", "volta_human_handoffs", ["operation_id"]
    )
    op.create_index(
        "uq_volta_handoffs_one_connecting_per_call",
        "volta_human_handoffs",
        ["call_id"],
        unique=True,
        postgresql_where=sa.text("status = 'CONNECTING'"),
    )
    op.create_table(
        "volta_ai_authority_fences",
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("handoff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fenced_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("call_id", name="pk_volta_ai_authority_fences"),
        sa.ForeignKeyConstraint(
            ["handoff_id"], ["volta_human_handoffs.handoff_id"], name="fk_volta_fence_handoff"
        ),
        sa.UniqueConstraint("handoff_id", name="uq_volta_fence_handoff"),
    )
    op.create_table(
        "volta_twilio_handoff_bindings",
        sa.Column("handoff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("remote_call_sid", sa.Text(), nullable=False),
        sa.Column("conference_name", sa.Text(), nullable=False),
        sa.Column("conference_sid", sa.Text(), nullable=True),
        sa.Column("coordinator_call_sid", sa.Text(), nullable=True),
        sa.Column("remote_present", sa.Boolean(), nullable=False),
        sa.Column("coordinator_present", sa.Boolean(), nullable=False),
        sa.Column("remote_last_sequence", sa.BigInteger(), nullable=True),
        sa.Column("coordinator_last_sequence", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("handoff_id", name="pk_volta_twilio_handoff_bindings"),
        sa.ForeignKeyConstraint(
            ["handoff_id"],
            ["volta_human_handoffs.handoff_id"],
            name="fk_volta_twilio_binding_handoff",
        ),
        sa.UniqueConstraint("conference_name", name="uq_volta_twilio_binding_conference_name"),
        sa.UniqueConstraint("conference_sid", name="uq_volta_twilio_binding_conference_sid"),
        sa.UniqueConstraint(
            "coordinator_call_sid", name="uq_volta_twilio_binding_coordinator_call"
        ),
        sa.CheckConstraint(
            "remote_call_sid ~ '^CA[0-9a-fA-F]{32}$' AND "
            "(conference_sid IS NULL OR conference_sid ~ '^CF[0-9a-fA-F]{32}$') AND "
            "(coordinator_call_sid IS NULL OR coordinator_call_sid ~ '^CA[0-9a-fA-F]{32}$')",
            name="ck_volta_twilio_binding_sids",
        ),
        sa.CheckConstraint(
            "(remote_last_sequence IS NULL OR remote_last_sequence >= 0) AND "
            "(coordinator_last_sequence IS NULL OR coordinator_last_sequence >= 0)",
            name="ck_volta_twilio_binding_sequences",
        ),
    )


def downgrade() -> None:
    _require_data_reconciliation_before_downgrade()
    op.drop_table("volta_twilio_handoff_bindings")
    op.drop_table("volta_ai_authority_fences")
    op.drop_index(
        "uq_volta_handoffs_one_connecting_per_call", table_name="volta_human_handoffs"
    )
    op.drop_index("ix_volta_handoffs_operation", table_name="volta_human_handoffs")
    op.drop_index("ix_volta_handoffs_call", table_name="volta_human_handoffs")
    op.drop_table("volta_human_handoffs")
    op.drop_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
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
        "'ESCALATION_RESUMED', 'MANDATE_REPLACED', 'ESCALATION_RESOLVED', "
        "'EXPLICIT_ESCALATION_CREATED', 'NOTIFICATION_ACKNOWLEDGED', "
        "'INBOUND_CALL_ACCEPTED', 'INBOUND_CONSENT_RECORDED', "
        "'INBOUND_RECOVERY_COMPLETED') "
        "AND metadata = '{}'::jsonb)",
    )

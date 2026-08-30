"""Add durable inbound caller correlation and recovery attempts.

Revision ID: 20260830_27
Revises: 20260830_26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830_27"
down_revision: str | None = "20260830_26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PHASE24_METADATA_SCHEMA = (
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
    "'EXPLICIT_ESCALATION_CREATED', 'NOTIFICATION_ACKNOWLEDGED') "
    "AND metadata = '{}'::jsonb)"
)

_PHASE27_METADATA_SCHEMA = _PHASE24_METADATA_SCHEMA[:-1] + (
    " OR (event_type IN ('INBOUND_CALL_ACCEPTED', 'INBOUND_CONSENT_RECORDED', "
    "'INBOUND_RECOVERY_COMPLETED') AND metadata = '{}'::jsonb))"
)

_PHASE27_AUDIT_EVENTS = (
    "INBOUND_CALL_ACCEPTED",
    "INBOUND_CONSENT_RECORDED",
    "INBOUND_RECOVERY_COMPLETED",
)


def _require_audit_reconciliation_before_downgrade() -> None:
    has_inbound_audit = op.get_bind().execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM volta_audit_events "
            "WHERE event_type IN :event_types)"
        ).bindparams(sa.bindparam("event_types", expanding=True)),
        {"event_types": _PHASE27_AUDIT_EVENTS},
    ).scalar_one()
    if has_inbound_audit:
        raise RuntimeError(
            "phase 27 downgrade refused: inbound audit events require approved reconciliation"
        )


def upgrade() -> None:
    op.drop_constraint(
        "ck_volta_audit_events_metadata_schema", "volta_audit_events", type_="check"
    )
    op.create_check_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        _PHASE27_METADATA_SCHEMA,
    )
    op.create_table(
        "volta_inbound_caller_correlations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("caller_label", sa.Text(), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_inbound_caller_correlations"),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["volta_operations.id"],
            name="fk_volta_inbound_caller_correlations_operation",
        ),
        sa.UniqueConstraint(
            "caller_label",
            "operation_id",
            name="uq_volta_inbound_caller_correlations_caller_operation",
        ),
        sa.CheckConstraint(
            "caller_label ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'",
            name="ck_volta_inbound_caller_correlations_label",
        ),
    )
    op.create_index(
        "ix_volta_inbound_caller_correlations_label",
        "volta_inbound_caller_correlations",
        ["caller_label"],
        postgresql_where=sa.text("active"),
    )
    op.create_table(
        "volta_inbound_call_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("caller_label", sa.Text(), nullable=False),
        sa.Column("provider_call_id", sa.Text(), nullable=False),
        sa.Column("stream_binding_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True)),
        sa.Column("stream_started_at", sa.DateTime(timezone=True)),
        sa.Column("provider_stream_id", sa.Text()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("completion_fingerprint", sa.Text()),
        sa.Column("resulting_commitment_id", postgresql.UUID(as_uuid=True)),
        sa.Column("resulting_evidence_id", postgresql.UUID(as_uuid=True)),
        sa.Column("resulting_brief_id", postgresql.UUID(as_uuid=True)),
        sa.Column("recovery_attempt_id", postgresql.UUID(as_uuid=True)),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True)),
        sa.PrimaryKeyConstraint("id", name="pk_volta_inbound_call_attempts"),
        sa.UniqueConstraint(
            "provider_call_id", name="uq_volta_inbound_call_attempts_provider_call"
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["volta_operations.id"],
            name="fk_volta_inbound_attempt_operation",
        ),
        sa.ForeignKeyConstraint(
            ["commitment_id", "operation_id", "call_id"],
            [
                "volta_commitments.id",
                "volta_commitments.operation_id",
                "volta_commitments.call_id",
            ],
            name="fk_volta_inbound_attempt_commitment",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_inbound_attempt_result_commitment",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_evidence_id", "resulting_commitment_id"],
            ["volta_agreement_evidence.id", "volta_agreement_evidence.commitment_id"],
            name="fk_volta_inbound_attempt_result_evidence",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_brief_id"],
            ["volta_call_briefs.id"],
            name="fk_volta_inbound_attempt_result_brief",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["recovery_attempt_id"],
            ["volta_recovery_attempts.id"],
            name="fk_volta_inbound_attempt_recovery",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint(
            "status IN ('AWAITING_CONSENT', 'CONSENTED', 'STREAMING', 'COMPLETED', 'FAILED')",
            name="ck_volta_inbound_attempt_status",
        ),
        sa.CheckConstraint(
            "caller_label ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$' AND "
            "provider_call_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$' AND "
            "stream_binding_hash ~ '^[0-9a-f]{64}$' AND expires_at > created_at",
            name="ck_volta_inbound_attempt_identifiers",
        ),
        sa.CheckConstraint(
            "(status = 'AWAITING_CONSENT' AND consented_at IS NULL AND "
            "stream_started_at IS NULL AND completed_at IS NULL) OR "
            "(status = 'CONSENTED' AND consented_at IS NOT NULL AND "
            "stream_started_at IS NULL AND completed_at IS NULL) OR "
            "(status = 'STREAMING' AND consented_at IS NOT NULL AND "
            "stream_started_at IS NOT NULL AND provider_stream_id IS NOT NULL "
            "AND completed_at IS NULL) OR "
            "(status = 'COMPLETED' AND consented_at IS NOT NULL AND completed_at IS NOT NULL "
            "AND completion_fingerprint IS NOT NULL AND resulting_commitment_id IS NOT NULL "
            "AND resulting_evidence_id IS NOT NULL AND resulting_brief_id IS NOT NULL "
            "AND recovery_attempt_id IS NOT NULL AND correlation_id IS NOT NULL) OR "
            "(status = 'FAILED' AND completed_at IS NOT NULL AND failure_reason IS NOT NULL)",
            name="ck_volta_inbound_attempt_payload",
        ),
    )
    op.create_index(
        "uq_volta_inbound_attempt_one_active_operation",
        "volta_inbound_call_attempts",
        ["operation_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('AWAITING_CONSENT', 'CONSENTED', 'STREAMING')"
        ),
    )


def downgrade() -> None:
    _require_audit_reconciliation_before_downgrade()
    op.drop_index(
        "uq_volta_inbound_attempt_one_active_operation",
        table_name="volta_inbound_call_attempts",
    )
    op.drop_table("volta_inbound_call_attempts")
    op.drop_index(
        "ix_volta_inbound_caller_correlations_label",
        table_name="volta_inbound_caller_correlations",
    )
    op.drop_table("volta_inbound_caller_correlations")
    op.drop_constraint(
        "ck_volta_audit_events_metadata_schema", "volta_audit_events", type_="check"
    )
    op.create_check_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        _PHASE24_METADATA_SCHEMA,
    )

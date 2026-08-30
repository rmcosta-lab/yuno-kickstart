"""Add deterministic evidence, brief, recap, and recovery state.

Revision ID: 20260829_14
Revises: 20260829_08
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260829_14"
down_revision: str | None = "20260829_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PHASE08_METADATA_SCHEMA = (
    "(event_type = 'OPERATION_APPROVED' AND (metadata = '{}'::jsonb OR "
    "(metadata = jsonb_build_object('draft_version', metadata -> 'draft_version') "
    "AND jsonb_typeof(metadata -> 'draft_version') = 'number' AND "
    "metadata ->> 'draft_version' ~ '^(0|[1-9][0-9]{0,15})$' AND "
    "(char_length(metadata ->> 'draft_version') < 16 OR "
    "(char_length(metadata ->> 'draft_version') = 16 AND "
    "metadata ->> 'draft_version' <= '9007199254740991'))))) OR "
    "(event_type IN ('NEGOTIATION_STARTED', 'PRE_CONTACT_ESCALATED', "
    "'QUOTE_RECORDED', 'QUOTE_REJECTED', 'COMMITMENT_ACTIVATED', "
    "'COMMITMENT_SUPERSEDED') AND metadata = '{}'::jsonb)"
)

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


def upgrade() -> None:
    op.drop_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        _PHASE14_METADATA_SCHEMA,
    )

    op.create_table(
        "volta_agreement_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recording_reference", sa.Text(), nullable=False),
        sa.Column("audio_start_ms", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_agreement_evidence"),
        sa.UniqueConstraint("commitment_id", name="uq_volta_agreement_evidence_commitment"),
        sa.ForeignKeyConstraint(
            ["commitment_id"],
            ["volta_commitments.id"],
            name="fk_volta_agreement_evidence_commitment",
        ),
        sa.CheckConstraint(
            "audio_start_ms >= 0", name="ck_volta_agreement_evidence_audio_start_ms"
        ),
        sa.CheckConstraint(
            "char_length(recording_reference) BETWEEN 1 AND 200",
            name="ck_volta_agreement_evidence_recording_reference",
        ),
        sa.CheckConstraint(
            "char_length(item_id) BETWEEN 1 AND 200",
            name="ck_volta_agreement_evidence_item_id",
        ),
        sa.CheckConstraint(
            "char_length(event_id) BETWEEN 1 AND 200",
            name="ck_volta_agreement_evidence_event_id",
        ),
    )

    op.create_table(
        "volta_call_briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_origin", sa.Text(), nullable=False),
        sa.Column("route_destination", sa.Text(), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agreed_terms_reference", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mandate_version", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_call_briefs"),
        sa.UniqueConstraint("commitment_id", name="uq_volta_call_briefs_commitment"),
        sa.ForeignKeyConstraint(
            ["commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_call_briefs_commitment_operation",
        ),
        sa.CheckConstraint("mandate_version > 0", name="ck_volta_call_briefs_mandate_version"),
    )
    op.create_index("ix_volta_call_briefs_operation", "volta_call_briefs", ["operation_id"])

    op.create_table(
        "volta_recaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("disclosure_state", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_recaps"),
        sa.UniqueConstraint("commitment_id", name="uq_volta_recaps_commitment"),
        sa.ForeignKeyConstraint(
            ["commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_recaps_commitment_operation",
        ),
        sa.CheckConstraint(
            "disclosure_state = 'SIMULATED'", name="ck_volta_recaps_disclosure_state"
        ),
    )
    op.create_index("ix_volta_recaps_operation", "volta_recaps", ["operation_id"])

    op.create_table(
        "volta_post_contact_escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("operation_version", sa.Integer(), nullable=False),
        sa.Column("mandate_version", sa.Integer(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_volta_post_contact_escalations"),
        sa.UniqueConstraint(
            "id", "operation_id", name="uq_volta_post_contact_escalations_id_operation"
        ),
        sa.ForeignKeyConstraint(
            ["commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_post_contact_escalations_commitment_operation",
        ),
        sa.CheckConstraint(
            "operation_version > 0", name="ck_volta_post_contact_escalations_op_version"
        ),
        sa.CheckConstraint(
            "mandate_version > 0", name="ck_volta_post_contact_escalations_mandate_version"
        ),
        sa.CheckConstraint(
            "(resolved AND resolved_at IS NOT NULL) OR (NOT resolved AND resolved_at IS NULL)",
            name="ck_volta_post_contact_escalations_resolved_state",
        ),
    )
    op.create_index(
        "ix_volta_post_contact_escalations_operation",
        "volta_post_contact_escalations",
        ["operation_id"],
    )
    op.create_index(
        "uq_volta_post_contact_escalations_one_unresolved",
        "volta_post_contact_escalations",
        ["operation_id"],
        unique=True,
        postgresql_where=sa.text("NOT resolved"),
    )

    op.create_table(
        "volta_recovery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("resulting_commitment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("escalation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_recovery_attempts"),
        sa.ForeignKeyConstraint(
            ["commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_recovery_attempts_commitment_operation",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_recovery_attempts_resulting_commitment_operation",
        ),
        sa.ForeignKeyConstraint(
            ["escalation_id", "operation_id"],
            [
                "volta_post_contact_escalations.id",
                "volta_post_contact_escalations.operation_id",
            ],
            name="fk_volta_recovery_attempts_escalation_operation",
        ),
        sa.CheckConstraint(
            "outcome IN ('REPLACED', 'ESCALATED')", name="ck_volta_recovery_attempts_outcome"
        ),
        sa.CheckConstraint(
            "(outcome = 'REPLACED' AND resulting_commitment_id IS NOT NULL AND "
            "escalation_id IS NULL) OR (outcome = 'ESCALATED' AND "
            "resulting_commitment_id IS NULL AND escalation_id IS NOT NULL)",
            name="ck_volta_recovery_attempts_outcome_state",
        ),
    )
    op.create_index(
        "ix_volta_recovery_attempts_operation",
        "volta_recovery_attempts",
        ["operation_id", "created_at", "id"],
    )

    op.create_table(
        "volta_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_notifications"),
        sa.ForeignKeyConstraint(
            ["commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_notifications_commitment_operation",
        ),
    )
    op.create_index("ix_volta_notifications_operation", "volta_notifications", ["operation_id"])


def downgrade() -> None:
    op.drop_index("ix_volta_notifications_operation", table_name="volta_notifications")
    op.drop_table("volta_notifications")

    op.drop_index("ix_volta_recovery_attempts_operation", table_name="volta_recovery_attempts")
    op.drop_table("volta_recovery_attempts")

    op.drop_index(
        "uq_volta_post_contact_escalations_one_unresolved",
        table_name="volta_post_contact_escalations",
    )
    op.drop_index(
        "ix_volta_post_contact_escalations_operation",
        table_name="volta_post_contact_escalations",
    )
    op.drop_table("volta_post_contact_escalations")

    op.drop_index("ix_volta_recaps_operation", table_name="volta_recaps")
    op.drop_table("volta_recaps")

    op.drop_index("ix_volta_call_briefs_operation", table_name="volta_call_briefs")
    op.drop_table("volta_call_briefs")

    op.drop_table("volta_agreement_evidence")

    op.drop_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_volta_audit_events_metadata_schema",
        "volta_audit_events",
        _PHASE08_METADATA_SCHEMA,
    )

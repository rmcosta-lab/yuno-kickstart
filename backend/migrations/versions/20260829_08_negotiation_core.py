"""Add deterministic negotiation, quote, commitment, and idempotency state.

Revision ID: 20260829_08
Revises: 20260829_06
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260829_08"
down_revision: str | None = "20260829_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
        "'COMMITMENT_SUPERSEDED') AND metadata = '{}'::jsonb)",
    )
    op.create_table(
        "volta_negotiations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_version", sa.Integer(), nullable=False),
        sa.Column("mandate_version", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_negotiations"),
        sa.UniqueConstraint("operation_id", name="uq_volta_negotiations_operation"),
        sa.UniqueConstraint("id", "operation_id", name="uq_volta_negotiations_id_operation"),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["volta_operations.id"], name="fk_volta_negotiations_operation"
        ),
        sa.CheckConstraint("operation_version > 0", name="ck_volta_negotiations_operation_version"),
        sa.CheckConstraint("mandate_version > 0", name="ck_volta_negotiations_mandate_version"),
    )
    op.create_table(
        "volta_carrier_sessions",
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("negotiation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrier_display_label", sa.Text(), nullable=False),
        sa.Column("route_origin", sa.Text(), nullable=False),
        sa.Column("route_destination", sa.Text(), nullable=False),
        sa.Column("available_snapshot", sa.Boolean(), nullable=False),
        sa.Column("fixed_priority", sa.Integer(), nullable=False),
        sa.Column("selection_rank", sa.Integer(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("call_id", name="pk_volta_carrier_sessions"),
        sa.UniqueConstraint(
            "negotiation_id", "carrier_id", name="uq_volta_sessions_negotiation_carrier"
        ),
        sa.UniqueConstraint(
            "call_id", "operation_id", "carrier_id", name="uq_volta_sessions_call_operation_carrier"
        ),
        sa.ForeignKeyConstraint(
            ["negotiation_id", "operation_id"],
            ["volta_negotiations.id", "volta_negotiations.operation_id"],
            name="fk_volta_sessions_negotiation_operation",
        ),
        sa.CheckConstraint("fixed_priority > 0", name="ck_volta_sessions_priority_positive"),
        sa.CheckConstraint("selection_rank BETWEEN 1 AND 3", name="ck_volta_sessions_rank"),
        sa.CheckConstraint(
            "channel IN ('BROWSER_TEXT', 'BROWSER_VOICE')", name="ck_volta_sessions_channel"
        ),
        sa.CheckConstraint(
            "state IN ('SELECTED', 'ACTIVE', 'COMPLETED', 'FAILED')", name="ck_volta_sessions_state"
        ),
    )
    op.create_index("ix_volta_sessions_negotiation", "volta_carrier_sessions", ["negotiation_id"])
    op.create_table(
        "volta_pre_contact_escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("negotiation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_pre_contact_escalations"),
        sa.UniqueConstraint("operation_id", name="uq_volta_pre_contact_escalations_operation"),
        sa.ForeignKeyConstraint(
            ["negotiation_id", "operation_id"],
            ["volta_negotiations.id", "volta_negotiations.operation_id"],
            name="fk_volta_pre_contact_escalations_negotiation_operation",
        ),
        sa.CheckConstraint(
            "reason_code = 'no_eligible_carrier'", name="ck_volta_pre_contact_escalations_reason"
        ),
    )
    op.create_index(
        "ix_volta_pre_contact_escalations_negotiation",
        "volta_pre_contact_escalations",
        ["negotiation_id"],
    )
    op.create_table(
        "volta_quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrier_priority", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("pickup_window_start", sa.Date(), nullable=False),
        sa.Column("pickup_window_end", sa.Date(), nullable=False),
        sa.Column("conditions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mandate_version", sa.Integer(), nullable=False),
        sa.Column("eligibility", sa.Text(), nullable=False),
        sa.Column("rejection_reasons", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_volta_quotes"),
        sa.UniqueConstraint("id", "operation_id", name="uq_volta_quotes_id_operation"),
        sa.UniqueConstraint(
            "id", "operation_id", "call_id", "carrier_id", name="uq_volta_quotes_identity_scope"
        ),
        sa.ForeignKeyConstraint(
            ["call_id", "operation_id", "carrier_id"],
            [
                "volta_carrier_sessions.call_id",
                "volta_carrier_sessions.operation_id",
                "volta_carrier_sessions.carrier_id",
            ],
            name="fk_volta_quotes_session_scope",
        ),
        sa.CheckConstraint("carrier_priority > 0", name="ck_volta_quotes_priority_positive"),
        sa.CheckConstraint("mandate_version > 0", name="ck_volta_quotes_mandate_version"),
        sa.CheckConstraint(
            "amount >= 0 AND amount < 'Infinity'::numeric", name="ck_volta_quotes_amount_finite"
        ),
        sa.CheckConstraint(
            "pickup_window_end >= pickup_window_start", name="ck_volta_quotes_window_order"
        ),
        sa.CheckConstraint(
            "eligibility IN ('ELIGIBLE', 'REJECTED')", name="ck_volta_quotes_eligibility"
        ),
        sa.CheckConstraint(
            "(eligibility = 'ELIGIBLE' AND cardinality(rejection_reasons) = 0) OR "
            "(eligibility = 'REJECTED' AND cardinality(rejection_reasons) > 0)",
            name="ck_volta_quotes_rejection_consistency",
        ),
    )
    op.create_index(
        "ix_volta_quotes_operation_comparison",
        "volta_quotes",
        ["operation_id", "eligibility", "valid_until"],
    )
    op.create_index("ix_volta_quotes_call", "volta_quotes", ["call_id"])
    op.create_table(
        "volta_commitments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("pickup_window_start", sa.Date(), nullable=False),
        sa.Column("pickup_window_end", sa.Date(), nullable=False),
        sa.Column("conditions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("mandate_version", sa.Integer(), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lifecycle", sa.Text(), nullable=False),
        sa.Column("disposition", sa.Text(), nullable=False),
        sa.Column("replaces_commitment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("replaced_by_commitment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_volta_commitments"),
        sa.UniqueConstraint("id", "operation_id", name="uq_volta_commitments_id_operation"),
        sa.UniqueConstraint("quote_id", name="uq_volta_commitments_quote"),
        sa.ForeignKeyConstraint(
            ["quote_id", "operation_id", "call_id", "carrier_id"],
            [
                "volta_quotes.id",
                "volta_quotes.operation_id",
                "volta_quotes.call_id",
                "volta_quotes.carrier_id",
            ],
            name="fk_volta_commitments_quote_scope",
        ),
        sa.ForeignKeyConstraint(
            ["replaces_commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_commitments_replaces_operation",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_commitments_replaced_by_operation",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint("mandate_version > 0", name="ck_volta_commitments_mandate_version"),
        sa.CheckConstraint(
            "amount >= 0 AND amount < 'Infinity'::numeric",
            name="ck_volta_commitments_amount_finite",
        ),
        sa.CheckConstraint(
            "pickup_window_end >= pickup_window_start", name="ck_volta_commitments_window_order"
        ),
        sa.CheckConstraint("lifecycle = 'CANDIDATE'", name="ck_volta_commitments_lifecycle"),
        sa.CheckConstraint(
            "disposition IN ('ACTIVE', 'SUPERSEDED')", name="ck_volta_commitments_disposition"
        ),
        sa.CheckConstraint(
            "(disposition = 'ACTIVE' AND superseded_at IS NULL AND "
            "replaced_by_commitment_id IS NULL) OR (disposition = 'SUPERSEDED' "
            "AND superseded_at IS NOT NULL AND replaced_by_commitment_id IS NOT NULL)",
            name="ck_volta_commitments_disposition_state",
        ),
        sa.CheckConstraint(
            "replaces_commitment_id IS NULL OR replaces_commitment_id <> id",
            name="ck_volta_commitments_not_self_replacing",
        ),
        sa.CheckConstraint(
            "replaced_by_commitment_id IS NULL OR replaced_by_commitment_id <> id",
            name="ck_volta_commitments_not_self_replaced",
        ),
    )
    op.create_index(
        "ix_volta_commitments_operation_history",
        "volta_commitments",
        ["operation_id", "created_at", "id"],
    )
    op.create_index(
        "ix_volta_commitments_replaces", "volta_commitments", ["replaces_commitment_id"]
    )
    op.create_index(
        "ix_volta_commitments_replaced_by", "volta_commitments", ["replaced_by_commitment_id"]
    )
    op.create_index(
        "uq_volta_commitments_one_active",
        "volta_commitments",
        ["operation_id"],
        unique=True,
        postgresql_where=sa.text("disposition = 'ACTIVE'"),
    )
    op.create_table(
        "volta_mutation_idempotency",
        sa.Column("operation_name", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("negotiation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("commitment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "operation_name", "idempotency_key", name="pk_volta_mutation_idempotency"
        ),
        sa.UniqueConstraint(
            "operation_name",
            "negotiation_id",
            name="uq_volta_mutation_idempotency_negotiation",
        ),
        sa.UniqueConstraint(
            "operation_name", "quote_id", name="uq_volta_mutation_idempotency_quote"
        ),
        sa.UniqueConstraint(
            "operation_name",
            "commitment_id",
            name="uq_volta_mutation_idempotency_commitment",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["volta_operations.id"],
            name="fk_volta_mutation_idempotency_operation",
        ),
        sa.CheckConstraint(
            "operation_name IN ('start_negotiation', 'record_quote', 'create_commitment')",
            name="ck_volta_mutation_idempotency_operation_name",
        ),
        sa.CheckConstraint(
            "(operation_name = 'start_negotiation' AND negotiation_id IS NOT NULL AND "
            "quote_id IS NULL AND commitment_id IS NULL) OR "
            "(operation_name = 'record_quote' AND negotiation_id IS NULL AND "
            "quote_id IS NOT NULL AND commitment_id IS NULL) OR "
            "(operation_name = 'create_commitment' AND negotiation_id IS NULL AND "
            "quote_id IS NULL AND commitment_id IS NOT NULL)",
            name="ck_volta_mutation_idempotency_result_mapping",
        ),
        sa.ForeignKeyConstraint(
            ["negotiation_id", "operation_id"],
            ["volta_negotiations.id", "volta_negotiations.operation_id"],
            name="fk_volta_mutation_idempotency_negotiation_operation",
        ),
        sa.ForeignKeyConstraint(
            ["quote_id", "operation_id"],
            ["volta_quotes.id", "volta_quotes.operation_id"],
            name="fk_volta_mutation_idempotency_quote_operation",
        ),
        sa.ForeignKeyConstraint(
            ["commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_mutation_idempotency_commitment_operation",
        ),
        sa.CheckConstraint(
            "char_length(idempotency_key) BETWEEN 8 AND 128 AND idempotency_key ~ '^[ -~]+$'",
            name="ck_volta_mutation_idempotency_key",
        ),
        sa.CheckConstraint(
            "fingerprint ~ '^[0-9a-f]{64}$'", name="ck_volta_mutation_idempotency_fingerprint"
        ),
    )
    op.create_index(
        "ix_volta_mutation_idempotency_operation", "volta_mutation_idempotency", ["operation_id"]
    )
    for suffix in ("negotiation", "quote", "commitment"):
        op.create_index(
            f"ix_volta_mutation_idempotency_{suffix}",
            "volta_mutation_idempotency",
            [f"{suffix}_id"],
            postgresql_where=sa.text(f"{suffix}_id IS NOT NULL"),
        )


def downgrade() -> None:
    for suffix in ("commitment", "quote", "negotiation"):
        op.drop_index(
            f"ix_volta_mutation_idempotency_{suffix}",
            table_name="volta_mutation_idempotency",
        )
    op.drop_index(
        "ix_volta_mutation_idempotency_operation", table_name="volta_mutation_idempotency"
    )
    op.drop_table("volta_mutation_idempotency")
    op.drop_index("uq_volta_commitments_one_active", table_name="volta_commitments")
    op.drop_index("ix_volta_commitments_replaced_by", table_name="volta_commitments")
    op.drop_index("ix_volta_commitments_replaces", table_name="volta_commitments")
    op.drop_index("ix_volta_commitments_operation_history", table_name="volta_commitments")
    op.drop_table("volta_commitments")
    op.drop_index("ix_volta_quotes_call", table_name="volta_quotes")
    op.drop_index("ix_volta_quotes_operation_comparison", table_name="volta_quotes")
    op.drop_table("volta_quotes")
    op.drop_index(
        "ix_volta_pre_contact_escalations_negotiation", table_name="volta_pre_contact_escalations"
    )
    op.drop_table("volta_pre_contact_escalations")
    op.drop_index("ix_volta_sessions_negotiation", table_name="volta_carrier_sessions")
    op.drop_table("volta_carrier_sessions")
    op.drop_table("volta_negotiations")
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
        "(event_type <> 'OPERATION_APPROVED' AND metadata = '{}'::jsonb)",
    )

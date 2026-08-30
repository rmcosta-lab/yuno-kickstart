"""Persist text-slice cargo labels and intake idempotency.

Revision ID: 20260829_10
Revises: 20260829_14
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260829_10"
down_revision: str | None = "20260829_14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("volta_intake_drafts", sa.Column("cargo_label", sa.Text(), nullable=True))
    op.execute(
        "UPDATE volta_intake_drafts SET cargo_label = "
        "CASE WHEN source_prompt ~* '40[ -]?(foot|ft)' "
        "THEN '40ft dry container' ELSE 'Synthetic drayage cargo (migrated)' END"
    )
    op.alter_column("volta_intake_drafts", "cargo_label", nullable=False)
    op.create_check_constraint(
        "ck_volta_intake_drafts_cargo_label",
        "volta_intake_drafts",
        "char_length(cargo_label) <= 500",
    )

    op.add_column("volta_operations", sa.Column("cargo_label", sa.Text(), nullable=True))
    op.execute(
        "UPDATE volta_operations AS operation SET cargo_label = draft.cargo_label "
        "FROM volta_intake_drafts AS draft "
        "WHERE draft.id = operation.source_draft_id"
    )
    op.alter_column("volta_operations", "cargo_label", nullable=False)
    op.create_check_constraint(
        "ck_volta_operations_cargo_label",
        "volta_operations",
        "char_length(btrim(cargo_label)) BETWEEN 1 AND 500",
    )

    op.create_table(
        "volta_text_mutation_idempotency",
        sa.Column("operation_name", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "operation_name",
            "idempotency_key",
            name="pk_volta_text_mutation_idempotency",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["volta_intake_drafts.id"],
            name="fk_volta_text_idempotency_draft",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["volta_operations.id"],
            name="fk_volta_text_idempotency_operation",
        ),
        sa.CheckConstraint(
            "operation_name IN ('create_operation_draft', 'approve_operation')",
            name="ck_volta_text_idempotency_operation_name",
        ),
        sa.CheckConstraint(
            "(operation_name = 'create_operation_draft' AND draft_id IS NOT NULL "
            "AND operation_id IS NULL) OR "
            "(operation_name = 'approve_operation' AND draft_id IS NULL "
            "AND operation_id IS NOT NULL)",
            name="ck_volta_text_idempotency_result_mapping",
        ),
        sa.CheckConstraint(
            "char_length(idempotency_key) BETWEEN 8 AND 128 AND idempotency_key ~ '^[ -~]+$'",
            name="ck_volta_text_idempotency_key",
        ),
        sa.CheckConstraint(
            "fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_volta_text_idempotency_fingerprint",
        ),
    )
    op.create_index(
        "ix_volta_text_idempotency_draft",
        "volta_text_mutation_idempotency",
        ["draft_id"],
        postgresql_where=sa.text("draft_id IS NOT NULL"),
    )
    op.create_index(
        "ix_volta_text_idempotency_operation",
        "volta_text_mutation_idempotency",
        ["operation_id"],
        postgresql_where=sa.text("operation_id IS NOT NULL"),
    )

    op.create_table(
        "volta_evidence_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recording_reference", sa.Text(), nullable=False),
        sa.Column("audio_start_ms", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_by_commitment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_volta_evidence_reservations"),
        sa.UniqueConstraint("quote_id", name="uq_volta_evidence_reservations_quote"),
        sa.UniqueConstraint(
            "consumed_by_commitment_id",
            name="uq_volta_evidence_reservations_consumed_commitment",
        ),
        sa.ForeignKeyConstraint(
            ["quote_id", "operation_id"],
            ["volta_quotes.id", "volta_quotes.operation_id"],
            name="fk_volta_evidence_reservations_quote_operation",
        ),
        sa.ForeignKeyConstraint(
            ["consumed_by_commitment_id", "operation_id"],
            ["volta_commitments.id", "volta_commitments.operation_id"],
            name="fk_volta_evidence_reservations_commitment_operation",
        ),
        sa.CheckConstraint(
            "audio_start_ms >= 0", name="ck_volta_evidence_reservations_offset"
        ),
        sa.CheckConstraint(
            "char_length(recording_reference) BETWEEN 1 AND 200",
            name="ck_volta_evidence_reservations_reference",
        ),
        sa.CheckConstraint(
            "char_length(item_id) BETWEEN 1 AND 200 "
            "AND char_length(event_id) BETWEEN 1 AND 200",
            name="ck_volta_evidence_reservations_event_ids",
        ),
    )
    op.add_column(
        "volta_mutation_idempotency",
        sa.Column("evidence_reservation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.drop_constraint(
        "ck_volta_mutation_idempotency_operation_name",
        "volta_mutation_idempotency",
        type_="check",
    )
    op.drop_constraint(
        "ck_volta_mutation_idempotency_result_mapping",
        "volta_mutation_idempotency",
        type_="check",
    )
    op.create_check_constraint(
        "ck_volta_mutation_idempotency_operation_name",
        "volta_mutation_idempotency",
        "operation_name IN ('start_negotiation', 'record_quote', 'create_commitment', "
        "'attach_commitment_evidence')",
    )
    op.create_check_constraint(
        "ck_volta_mutation_idempotency_result_mapping",
        "volta_mutation_idempotency",
        "(operation_name = 'start_negotiation' AND negotiation_id IS NOT NULL AND "
        "quote_id IS NULL AND commitment_id IS NULL AND evidence_reservation_id IS NULL) OR "
        "(operation_name = 'record_quote' AND negotiation_id IS NULL AND quote_id IS NOT NULL "
        "AND commitment_id IS NULL AND evidence_reservation_id IS NULL) OR "
        "(operation_name = 'create_commitment' AND negotiation_id IS NULL AND quote_id IS NULL "
        "AND commitment_id IS NOT NULL AND evidence_reservation_id IS NULL) OR "
        "(operation_name = 'attach_commitment_evidence' AND negotiation_id IS NULL AND "
        "quote_id IS NULL AND commitment_id IS NULL AND evidence_reservation_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM volta_mutation_idempotency "
        "WHERE operation_name = 'attach_commitment_evidence'"
    )
    op.drop_constraint(
        "ck_volta_mutation_idempotency_result_mapping",
        "volta_mutation_idempotency",
        type_="check",
    )
    op.drop_constraint(
        "ck_volta_mutation_idempotency_operation_name",
        "volta_mutation_idempotency",
        type_="check",
    )
    op.create_check_constraint(
        "ck_volta_mutation_idempotency_operation_name",
        "volta_mutation_idempotency",
        "operation_name IN ('start_negotiation', 'record_quote', 'create_commitment')",
    )
    op.create_check_constraint(
        "ck_volta_mutation_idempotency_result_mapping",
        "volta_mutation_idempotency",
        "(operation_name = 'start_negotiation' AND negotiation_id IS NOT NULL AND "
        "quote_id IS NULL AND commitment_id IS NULL) OR "
        "(operation_name = 'record_quote' AND negotiation_id IS NULL AND quote_id IS NOT NULL "
        "AND commitment_id IS NULL) OR "
        "(operation_name = 'create_commitment' AND negotiation_id IS NULL AND quote_id IS NULL "
        "AND commitment_id IS NOT NULL)",
    )
    op.drop_column("volta_mutation_idempotency", "evidence_reservation_id")
    op.drop_table("volta_evidence_reservations")
    op.drop_index(
        "ix_volta_text_idempotency_operation",
        table_name="volta_text_mutation_idempotency",
    )
    op.drop_index(
        "ix_volta_text_idempotency_draft",
        table_name="volta_text_mutation_idempotency",
    )
    op.drop_table("volta_text_mutation_idempotency")
    op.drop_constraint(
        "ck_volta_operations_cargo_label",
        "volta_operations",
        type_="check",
    )
    op.drop_column("volta_operations", "cargo_label")
    op.drop_constraint(
        "ck_volta_intake_drafts_cargo_label",
        "volta_intake_drafts",
        type_="check",
    )
    op.drop_column("volta_intake_drafts", "cargo_label")

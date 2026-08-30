"""complete evidence and recovery application projections

Revision ID: 20260830_25
Revises: 20260830_24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830_25"
down_revision: str | None = "20260830_24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _refuse_incomplete_legacy_rows() -> None:
    connection = op.get_bind()
    legacy = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM volta_recaps) "
            "OR EXISTS (SELECT 1 FROM volta_call_briefs) "
            "OR EXISTS (SELECT 1 FROM volta_recovery_attempts) "
            "OR EXISTS (SELECT 1 FROM volta_agreement_evidence e "
            "JOIN volta_commitments c ON c.id = e.commitment_id "
            "WHERE e.id <> c.evidence_id)"
        )
    ).scalar_one()
    if legacy:
        raise RuntimeError(
            "phase 25 upgrade refused: legacy evidence/recovery rows lack non-derivable facts"
        )


def upgrade() -> None:
    _refuse_incomplete_legacy_rows()

    op.create_unique_constraint(
        "uq_volta_commitments_id_evidence",
        "volta_commitments",
        ["id", "evidence_id"],
    )
    op.create_unique_constraint(
        "uq_volta_commitments_id_operation_call",
        "volta_commitments",
        ["id", "operation_id", "call_id"],
    )
    op.create_unique_constraint(
        "uq_volta_agreement_evidence_id_commitment",
        "volta_agreement_evidence",
        ["id", "commitment_id"],
    )
    op.create_foreign_key(
        "fk_volta_agreement_evidence_commitment_artifact",
        "volta_agreement_evidence",
        "volta_commitments",
        ["commitment_id", "id"],
        ["id", "evidence_id"],
    )

    op.add_column("volta_recaps", sa.Column("call_id", postgresql.UUID(as_uuid=True)))
    op.add_column("volta_recaps", sa.Column("content_hash", sa.Text()))
    op.add_column("volta_recaps", sa.Column("rendered_content", sa.Text()))
    op.create_foreign_key(
        "fk_volta_recaps_call_operation",
        "volta_recaps",
        "volta_carrier_sessions",
        ["call_id", "operation_id"],
        ["call_id", "operation_id"],
    )
    for column in ("call_id", "content_hash", "rendered_content"):
        op.alter_column("volta_recaps", column, nullable=False)
    op.drop_constraint(
        "fk_volta_recaps_commitment_operation", "volta_recaps", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_volta_recaps_commitment_operation_call",
        "volta_recaps",
        "volta_commitments",
        ["commitment_id", "operation_id", "call_id"],
        ["id", "operation_id", "call_id"],
    )
    op.create_check_constraint(
        "ck_volta_recaps_content",
        "volta_recaps",
        "content_hash ~ '^[0-9a-f]{64}$' AND "
        "char_length(rendered_content) <= 10000 "
        "AND char_length(btrim(rendered_content)) >= 1",
    )
    op.drop_index("ix_volta_recaps_operation", table_name="volta_recaps")
    op.create_index(
        "ix_volta_recaps_operation_order",
        "volta_recaps",
        ["operation_id", "generated_at", "id"],
    )

    op.add_column("volta_call_briefs", sa.Column("call_id", postgresql.UUID(as_uuid=True)))
    for name in ("facts", "objections", "changes", "unresolved_items"):
        op.add_column("volta_call_briefs", sa.Column(name, postgresql.ARRAY(sa.Text())))
    op.create_foreign_key(
        "fk_volta_call_briefs_call_operation",
        "volta_call_briefs",
        "volta_carrier_sessions",
        ["call_id", "operation_id"],
        ["call_id", "operation_id"],
    )
    for column in ("call_id", "facts", "objections", "changes", "unresolved_items"):
        op.alter_column("volta_call_briefs", column, nullable=False)
    op.drop_constraint(
        "fk_volta_call_briefs_commitment_operation",
        "volta_call_briefs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_volta_call_briefs_commitment_operation_call",
        "volta_call_briefs",
        "volta_commitments",
        ["commitment_id", "operation_id", "call_id"],
        ["id", "operation_id", "call_id"],
    )
    op.create_check_constraint(
        "ck_volta_call_briefs_structured_fields",
        "volta_call_briefs",
        "cardinality(facts) <= 50 AND volta_bounded_text_array(facts) "
        "AND cardinality(objections) <= 50 AND volta_bounded_text_array(objections) "
        "AND cardinality(changes) <= 50 AND volta_bounded_text_array(changes) "
        "AND cardinality(unresolved_items) <= 50 "
        "AND volta_bounded_text_array(unresolved_items)",
    )
    op.drop_index("ix_volta_call_briefs_operation", table_name="volta_call_briefs")
    op.create_index(
        "ix_volta_call_briefs_operation_order",
        "volta_call_briefs",
        ["operation_id", "generated_at", "id"],
    )

    op.add_column("volta_recovery_attempts", sa.Column("scenario", sa.Text()))
    op.add_column(
        "volta_recovery_attempts", sa.Column("before_operation_version", sa.Integer())
    )
    op.add_column(
        "volta_recovery_attempts", sa.Column("after_operation_version", sa.Integer())
    )
    op.add_column("volta_recovery_attempts", sa.Column("decision_reason", sa.Text()))
    op.add_column(
        "volta_recovery_attempts",
        sa.Column("resulting_evidence_id", postgresql.UUID(as_uuid=True)),
    )
    for column in (
        "scenario",
        "before_operation_version",
        "after_operation_version",
        "decision_reason",
    ):
        op.alter_column("volta_recovery_attempts", column, nullable=False)
    op.create_check_constraint(
        "ck_volta_recovery_attempts_complete_decision",
        "volta_recovery_attempts",
        "scenario IN ('MANDATE_SAFE', 'OUT_OF_MANDATE') "
        "AND before_operation_version > 0 "
        "AND after_operation_version = before_operation_version + 1 "
        "AND char_length(btrim(decision_reason)) BETWEEN 1 AND 500",
    )
    op.drop_constraint(
        "ck_volta_recovery_attempts_outcome_state",
        "volta_recovery_attempts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_volta_recovery_attempts_outcome_state",
        "volta_recovery_attempts",
        "(outcome = 'REPLACED' AND resulting_commitment_id IS NOT NULL AND "
        "resulting_evidence_id IS NOT NULL AND escalation_id IS NULL) OR "
        "(outcome = 'ESCALATED' AND resulting_commitment_id IS NULL AND "
        "resulting_evidence_id IS NULL AND escalation_id IS NOT NULL)",
    )
    op.create_foreign_key(
        "fk_volta_recovery_attempts_resulting_evidence_commitment",
        "volta_recovery_attempts",
        "volta_agreement_evidence",
        ["resulting_evidence_id", "resulting_commitment_id"],
        ["id", "commitment_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_check_constraint(
        "ck_volta_recovery_attempts_scenario_outcome",
        "volta_recovery_attempts",
        "(scenario = 'MANDATE_SAFE' AND outcome = 'REPLACED') OR "
        "(scenario = 'OUT_OF_MANDATE' AND outcome = 'ESCALATED')",
    )

    op.add_column(
        "volta_text_mutation_idempotency",
        sa.Column("result_id", postgresql.UUID(as_uuid=True)),
    )
    op.add_column(
        "volta_text_mutation_idempotency",
        sa.Column("result_kind", sa.Text(), server_default="LEGACY_RESOURCE"),
    )
    op.add_column(
        "volta_text_mutation_idempotency",
        sa.Column(
            "result_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.execute(
        "UPDATE volta_text_mutation_idempotency "
        "SET result_id = COALESCE(draft_id, operation_id)"
    )
    for column in ("result_id", "result_kind", "result_snapshot"):
        op.alter_column(
            "volta_text_mutation_idempotency", column, nullable=False, server_default=None
        )
    op.drop_constraint(
        "ck_volta_text_idempotency_operation_name",
        "volta_text_mutation_idempotency",
        type_="check",
    )
    op.drop_constraint(
        "ck_volta_text_idempotency_result_mapping",
        "volta_text_mutation_idempotency",
        type_="check",
    )
    op.create_check_constraint(
        "ck_volta_text_idempotency_operation_name",
        "volta_text_mutation_idempotency",
        "operation_name IN ('create_operation_draft', 'approve_operation', "
        "'create_simulated_recap', 'create_call_brief', 'start_inbound_simulation', "
        "'replace_mandate', 'create_escalation', 'acknowledge_notification')",
    )
    op.create_check_constraint(
        "ck_volta_text_idempotency_result_mapping",
        "volta_text_mutation_idempotency",
        "(operation_name = 'create_operation_draft' AND draft_id IS NOT NULL "
        "AND operation_id IS NULL) OR "
        "(operation_name = 'approve_operation' AND draft_id IS NULL "
        "AND operation_id IS NOT NULL) OR "
        "(operation_name NOT IN ('create_operation_draft', 'approve_operation') "
        "AND draft_id IS NULL AND operation_id IS NULL)",
    )
    op.create_check_constraint(
        "ck_volta_text_idempotency_result_kind",
        "volta_text_mutation_idempotency",
        "(operation_name IN ('create_operation_draft', 'approve_operation') "
        "AND result_kind = 'LEGACY_RESOURCE') OR "
        "(operation_name = 'create_simulated_recap' AND result_kind = 'Recap') OR "
        "(operation_name = 'create_call_brief' AND result_kind = 'CallBrief') OR "
        "(operation_name = 'start_inbound_simulation' "
        "AND result_kind = 'RecoveryProjection') OR "
        "(operation_name = 'replace_mandate' "
        "AND result_kind = 'OperationProjection') OR "
        "(operation_name = 'create_escalation' "
        "AND result_kind = 'PostContactEscalation') OR "
        "(operation_name = 'acknowledge_notification' "
        "AND result_kind = 'Notification')",
    )
    op.create_check_constraint(
        "ck_volta_text_idempotency_result_snapshot",
        "volta_text_mutation_idempotency",
        "jsonb_typeof(result_snapshot) = 'object' "
        "AND octet_length(result_snapshot::text) <= 33554432",
    )
    op.drop_index("ix_volta_notifications_operation", table_name="volta_notifications")
    op.create_index(
        "ix_volta_notifications_operation_order",
        "volta_notifications",
        ["operation_id", "created_at", "id"],
    )
    op.drop_index(
        "ix_volta_post_contact_escalations_operation",
        table_name="volta_post_contact_escalations",
    )
    op.create_index(
        "ix_volta_post_contact_escalations_operation_order",
        "volta_post_contact_escalations",
        ["operation_id", "created_at", "id"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    phase25 = connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM volta_recaps) "
            "OR EXISTS (SELECT 1 FROM volta_call_briefs) "
            "OR EXISTS (SELECT 1 FROM volta_recovery_attempts) "
            "OR EXISTS (SELECT 1 FROM volta_text_mutation_idempotency "
            "WHERE operation_name NOT IN ('create_operation_draft', 'approve_operation'))"
        )
    ).scalar_one()
    if phase25:
        raise RuntimeError(
            "phase 25 downgrade refused: complete evidence/recovery facts would be lost"
        )

    op.drop_index(
        "ix_volta_post_contact_escalations_operation_order",
        table_name="volta_post_contact_escalations",
    )
    op.create_index(
        "ix_volta_post_contact_escalations_operation",
        "volta_post_contact_escalations",
        ["operation_id"],
    )
    op.drop_index("ix_volta_notifications_operation_order", table_name="volta_notifications")
    op.create_index("ix_volta_notifications_operation", "volta_notifications", ["operation_id"])
    for name in (
        "ck_volta_text_idempotency_result_snapshot",
        "ck_volta_text_idempotency_result_kind",
        "ck_volta_text_idempotency_result_mapping",
        "ck_volta_text_idempotency_operation_name",
    ):
        op.drop_constraint(name, "volta_text_mutation_idempotency", type_="check")
    op.create_check_constraint(
        "ck_volta_text_idempotency_operation_name",
        "volta_text_mutation_idempotency",
        "operation_name IN ('create_operation_draft', 'approve_operation')",
    )
    op.create_check_constraint(
        "ck_volta_text_idempotency_result_mapping",
        "volta_text_mutation_idempotency",
        "(operation_name = 'create_operation_draft' AND draft_id IS NOT NULL "
        "AND operation_id IS NULL) OR "
        "(operation_name = 'approve_operation' AND draft_id IS NULL "
        "AND operation_id IS NOT NULL)",
    )
    for column in ("result_snapshot", "result_kind", "result_id"):
        op.drop_column("volta_text_mutation_idempotency", column)

    for name in (
        "ck_volta_recovery_attempts_scenario_outcome",
        "ck_volta_recovery_attempts_complete_decision",
    ):
        op.drop_constraint(name, "volta_recovery_attempts", type_="check")
    op.drop_constraint(
        "fk_volta_recovery_attempts_resulting_evidence_commitment",
        "volta_recovery_attempts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_volta_recovery_attempts_outcome_state",
        "volta_recovery_attempts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_volta_recovery_attempts_outcome_state",
        "volta_recovery_attempts",
        "(outcome = 'REPLACED' AND resulting_commitment_id IS NOT NULL AND "
        "escalation_id IS NULL) OR (outcome = 'ESCALATED' AND "
        "resulting_commitment_id IS NULL AND escalation_id IS NOT NULL)",
    )
    op.drop_column("volta_recovery_attempts", "resulting_evidence_id")
    for column in (
        "decision_reason",
        "after_operation_version",
        "before_operation_version",
        "scenario",
    ):
        op.drop_column("volta_recovery_attempts", column)

    op.drop_index("ix_volta_call_briefs_operation_order", table_name="volta_call_briefs")
    op.create_index("ix_volta_call_briefs_operation", "volta_call_briefs", ["operation_id"])
    op.drop_constraint(
        "ck_volta_call_briefs_structured_fields", "volta_call_briefs", type_="check"
    )
    op.drop_constraint(
        "fk_volta_call_briefs_call_operation", "volta_call_briefs", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_volta_call_briefs_commitment_operation_call",
        "volta_call_briefs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_volta_call_briefs_commitment_operation",
        "volta_call_briefs",
        "volta_commitments",
        ["commitment_id", "operation_id"],
        ["id", "operation_id"],
    )
    for column in ("unresolved_items", "changes", "objections", "facts", "call_id"):
        op.drop_column("volta_call_briefs", column)

    op.drop_index("ix_volta_recaps_operation_order", table_name="volta_recaps")
    op.create_index("ix_volta_recaps_operation", "volta_recaps", ["operation_id"])
    op.drop_constraint("ck_volta_recaps_content", "volta_recaps", type_="check")
    op.drop_constraint("fk_volta_recaps_call_operation", "volta_recaps", type_="foreignkey")
    op.drop_constraint(
        "fk_volta_recaps_commitment_operation_call",
        "volta_recaps",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_volta_recaps_commitment_operation",
        "volta_recaps",
        "volta_commitments",
        ["commitment_id", "operation_id"],
        ["id", "operation_id"],
    )
    for column in ("rendered_content", "content_hash", "call_id"):
        op.drop_column("volta_recaps", column)
    op.drop_constraint(
        "fk_volta_agreement_evidence_commitment_artifact",
        "volta_agreement_evidence",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_volta_agreement_evidence_id_commitment",
        "volta_agreement_evidence",
        type_="unique",
    )
    op.drop_constraint(
        "uq_volta_commitments_id_evidence", "volta_commitments", type_="unique"
    )
    op.drop_constraint(
        "uq_volta_commitments_id_operation_call",
        "volta_commitments",
        type_="unique",
    )

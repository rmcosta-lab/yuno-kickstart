"""Add durable outbound call attempt reservations.

Revision ID: 20260830_26
Revises: 20260830_25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830_26"
down_revision: str | None = "20260830_25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "volta_outbound_call_attempts",
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_fingerprint", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("call_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_call_id", sa.Text(), nullable=True),
        sa.Column("call_status", sa.Text(), nullable=True),
        sa.Column("call_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status_event_id", sa.Text(), nullable=True),
        sa.Column("last_status_sequence_number", sa.BigInteger(), nullable=True),
        sa.Column(
            "processed_status_event_ids", postgresql.ARRAY(sa.Text()), nullable=True
        ),
        sa.Column("uncertainty_reason", sa.Text(), nullable=True),
        sa.Column("uncertainty_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_category", sa.Text(), nullable=True),
        sa.Column("failure_status_code", sa.Integer(), nullable=True),
        sa.Column("failure_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "idempotency_key", name="pk_volta_outbound_call_attempts"
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["volta_operations.id"],
            name="fk_volta_outbound_call_attempts_operation",
        ),
        sa.UniqueConstraint(
            "provider_call_id", name="uq_volta_outbound_call_attempts_provider_call"
        ),
        sa.CheckConstraint(
            "char_length(idempotency_key) BETWEEN 8 AND 128 "
            "AND idempotency_key ~ '^[ -~]+$'",
            name="ck_volta_outbound_call_attempts_key",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_volta_outbound_call_attempts_fingerprint",
        ),
        sa.CheckConstraint(
            "state IN ('PENDING', 'SUCCEEDED', 'UNCERTAIN', 'FAILED')",
            name="ck_volta_outbound_call_attempts_state",
        ),
        sa.CheckConstraint(
            "(state = 'PENDING' AND call_session_id IS NULL AND provider_call_id IS NULL "
            "AND call_status IS NULL AND call_created_at IS NULL AND status_updated_at IS NULL "
            "AND last_status_event_id IS NULL AND last_status_sequence_number IS NULL "
            "AND processed_status_event_ids IS NULL AND uncertainty_reason IS NULL "
            "AND uncertainty_occurred_at IS NULL AND failure_category IS NULL "
            "AND failure_status_code IS NULL AND failure_occurred_at IS NULL) OR "
            "(state = 'SUCCEEDED' AND call_session_id IS NOT NULL "
            "AND provider_call_id IS NOT NULL AND call_status IS NOT NULL "
            "AND call_created_at IS NOT NULL AND status_updated_at IS NOT NULL "
            "AND processed_status_event_ids IS NOT NULL AND uncertainty_reason IS NULL "
            "AND uncertainty_occurred_at IS NULL AND failure_category IS NULL "
            "AND failure_status_code IS NULL AND failure_occurred_at IS NULL) OR "
            "(state = 'UNCERTAIN' AND call_session_id IS NULL AND provider_call_id IS NULL "
            "AND call_status IS NULL AND call_created_at IS NULL AND status_updated_at IS NULL "
            "AND last_status_event_id IS NULL AND last_status_sequence_number IS NULL "
            "AND processed_status_event_ids IS NULL AND uncertainty_reason IS NOT NULL "
            "AND uncertainty_occurred_at IS NOT NULL AND failure_category IS NULL "
            "AND failure_status_code IS NULL AND failure_occurred_at IS NULL) OR "
            "(state = 'FAILED' AND call_session_id IS NULL AND provider_call_id IS NULL "
            "AND call_status IS NULL AND call_created_at IS NULL AND status_updated_at IS NULL "
            "AND last_status_event_id IS NULL AND last_status_sequence_number IS NULL "
            "AND processed_status_event_ids IS NULL AND uncertainty_reason IS NULL "
            "AND uncertainty_occurred_at IS NULL AND failure_category IS NOT NULL "
            "AND failure_occurred_at IS NOT NULL)",
            name="ck_volta_outbound_call_attempts_payload",
        ),
        sa.CheckConstraint(
            "call_status IS NULL OR call_status IN ('QUEUED', 'INITIATED', 'RINGING', "
            "'IN_PROGRESS', 'COMPLETED', 'BUSY', 'FAILED', 'NO_ANSWER', 'CANCELED')",
            name="ck_volta_outbound_call_attempts_call_status",
        ),
        sa.CheckConstraint(
            "provider_call_id IS NULL OR provider_call_id ~ "
            "'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'",
            name="ck_volta_outbound_call_attempts_provider_call",
        ),
        sa.CheckConstraint(
            "(last_status_event_id IS NULL AND last_status_sequence_number IS NULL) OR "
            "(last_status_event_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$' "
            "AND last_status_sequence_number >= 0)",
            name="ck_volta_outbound_call_attempts_cursor",
        ),
        sa.CheckConstraint(
            "processed_status_event_ids IS NULL OR "
            "(cardinality(processed_status_event_ids) <= 128 AND "
            "array_to_string(processed_status_event_ids, ',') ~ "
            "'^$|^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}(,[A-Za-z0-9][A-Za-z0-9._:/-]{0,127})*$' "
            "AND (last_status_event_id IS NULL OR "
            "last_status_event_id = ANY(processed_status_event_ids)))",
            name="ck_volta_outbound_call_attempts_processed_events",
        ),
        sa.CheckConstraint(
            "uncertainty_reason IS NULL OR uncertainty_reason IN "
            "('TIMEOUT', 'CONNECTION_LOST', 'INVALID_RESPONSE', 'PROVIDER_FAILURE')",
            name="ck_volta_outbound_call_attempts_uncertainty",
        ),
        sa.CheckConstraint(
            "failure_category IS NULL OR failure_category IN ('AUTHENTICATION', "
            "'PERMISSION', 'RATE_LIMIT', 'TIMEOUT', 'CONNECTION', 'INVALID_REQUEST', "
            "'PROVIDER_REJECTED', 'INVALID_RESPONSE')",
            name="ck_volta_outbound_call_attempts_failure",
        ),
        sa.CheckConstraint(
            "failure_status_code IS NULL OR failure_status_code BETWEEN 100 AND 599",
            name="ck_volta_outbound_call_attempts_failure_status",
        ),
        sa.CheckConstraint(
            "(call_created_at IS NULL AND status_updated_at IS NULL) OR "
            "status_updated_at >= call_created_at",
            name="ck_volta_outbound_call_attempts_call_timestamps",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_volta_outbound_call_attempts_timestamps",
        ),
    )
    op.create_index(
        "ix_volta_outbound_call_attempts_operation",
        "volta_outbound_call_attempts",
        ["operation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_volta_outbound_call_attempts_operation",
        table_name="volta_outbound_call_attempts",
    )
    op.drop_table("volta_outbound_call_attempts")

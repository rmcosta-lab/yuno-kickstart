"""Private SQLAlchemy Core table metadata for Volta persistence."""

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

__all__: list[str] = []

_metadata = MetaData()

_intake_drafts = Table(
    "volta_intake_drafts",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("source_prompt", Text, nullable=False),
    Column("requested_language", Text, nullable=False),
    Column("extraction_policy_version", Text, nullable=False),
    Column("route_origin", Text, nullable=False),
    Column("route_destination", Text, nullable=False),
    Column("pickup_date", Date, nullable=False),
    Column("maximum_amount", Numeric, nullable=False),
    Column("currency", Text, nullable=False),
    Column("pickup_window_start_date", Date, nullable=False),
    Column("pickup_window_end_date", Date, nullable=False),
    Column("allowed_conditions", ARRAY(Text), nullable=False),
    Column("escalation_conditions", ARRAY(Text), nullable=False),
    Column("validation_issues", JSONB, nullable=False),
    Column("approval_eligible", Boolean, nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_intake_drafts"),
    CheckConstraint("version > 0", name="ck_volta_intake_drafts_version_positive"),
    CheckConstraint(
        "maximum_amount > '-Infinity'::numeric "
        "AND maximum_amount < 'Infinity'::numeric",
        name="ck_volta_intake_drafts_amount_finite",
    ),
    CheckConstraint(
        "jsonb_typeof(validation_issues) = 'array'",
        name="ck_volta_intake_drafts_validation_issues_array",
    ),
    CheckConstraint(
        "approval_eligible = (jsonb_array_length(validation_issues) = 0)",
        name="ck_volta_intake_drafts_approval_eligibility",
    ),
)

_operations = Table(
    "volta_operations",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("version", Integer, nullable=False),
    Column(
        "source_draft_id",
        UUID(as_uuid=True),
        ForeignKey(
            "volta_intake_drafts.id",
            name="fk_volta_operations_source_draft_id",
        ),
        nullable=False,
    ),
    Column("source_draft_version", Integer, nullable=False),
    Column("route_origin", Text, nullable=False),
    Column("route_destination", Text, nullable=False),
    Column("pickup_date", Date, nullable=False),
    Column("active_mandate_id", UUID(as_uuid=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_operations"),
    CheckConstraint("version > 0", name="ck_volta_operations_version_positive"),
    CheckConstraint(
        "source_draft_version > 0",
        name="ck_volta_operations_source_draft_version_positive",
    ),
    UniqueConstraint("source_draft_id", name="uq_volta_operations_source_draft_id"),
)

_mandates = Table(
    "volta_mandates",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column(
        "operation_id",
        UUID(as_uuid=True),
        ForeignKey("volta_operations.id", name="fk_volta_mandates_operation_id"),
        nullable=False,
    ),
    Column("version", Integer, nullable=False),
    Column("maximum_amount", Numeric, nullable=False),
    Column("currency", Text, nullable=False),
    Column("pickup_window_start_date", Date, nullable=False),
    Column("pickup_window_end_date", Date, nullable=False),
    Column("allowed_conditions", ARRAY(Text), nullable=False),
    Column("escalation_conditions", ARRAY(Text), nullable=False),
    Column("authorized_actions", ARRAY(Text), nullable=False),
    Column("approval_actor", Text, nullable=False),
    Column("approved_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_mandates"),
    CheckConstraint("version > 0", name="ck_volta_mandates_version_positive"),
    CheckConstraint(
        "maximum_amount >= 0 AND maximum_amount < 'Infinity'::numeric",
        name="ck_volta_mandates_amount_finite_non_negative",
    ),
    CheckConstraint(
        "pickup_window_end_date >= pickup_window_start_date",
        name="ck_volta_mandates_pickup_window_order",
    ),
    CheckConstraint(
        "cardinality(authorized_actions) > 0 "
        "AND authorized_actions <@ ARRAY['NEGOTIATE', 'COMMIT']::text[]",
        name="ck_volta_mandates_authorized_actions",
    ),
    UniqueConstraint("operation_id", "id", name="uq_volta_mandates_operation_id_id"),
    UniqueConstraint("operation_id", "version", name="uq_volta_mandates_operation_version"),
)

_operations.append_constraint(
    ForeignKeyConstraint(
        ["id", "active_mandate_id"],
        ["volta_mandates.operation_id", "volta_mandates.id"],
        name="fk_volta_operations_active_mandate",
        deferrable=True,
        initially="DEFERRED",
        use_alter=True,
    )
)

_operation_status_history = Table(
    "volta_operation_status_history",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("operation_version", Integer, nullable=False),
    Column("status", Text, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_operation_status_history"),
    CheckConstraint(
        "operation_version > 0",
        name="ck_volta_operation_status_history_version_positive",
    ),
    CheckConstraint(
        "status IN ('READY', 'NEGOTIATING', 'COMMITTED', 'ESCALATED', 'COMPLETED')",
        name="ck_volta_operation_status_history_status",
    ),
    ForeignKeyConstraint(
        ["operation_id"],
        ["volta_operations.id"],
        name="fk_volta_operation_status_history_operation",
    ),
)

_audit_events = Table(
    "volta_audit_events",
    _metadata,
    Column("event_id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("operation_version", Integer, nullable=False),
    Column("actor_kind", Text, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("correlation_id", UUID(as_uuid=True), nullable=False),
    Column("metadata", JSONB, nullable=False),
    PrimaryKeyConstraint("event_id", name="pk_volta_audit_events"),
    CheckConstraint("operation_version > 0", name="ck_volta_audit_events_version_positive"),
    CheckConstraint(
        "actor_kind IN ('COORDINATOR', 'CARRIER_SIMULATOR', 'SYSTEM')",
        name="ck_volta_audit_events_actor_kind",
    ),
    CheckConstraint(
        "event_type ~ '^[A-Z][A-Z0-9_]{0,63}$'",
        name="ck_volta_audit_events_event_type",
    ),
    CheckConstraint(
        "jsonb_typeof(metadata) = 'object'",
        name="ck_volta_audit_events_metadata_object",
    ),
    CheckConstraint(
        "octet_length(metadata::text) <= 8192",
        name="ck_volta_audit_events_metadata_size",
    ),
    CheckConstraint(
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
    ForeignKeyConstraint(
        ["operation_id"],
        ["volta_operations.id"],
        name="fk_volta_audit_events_operation",
    ),
)

Index(
    "ix_volta_operation_status_history_ordered",
    _operation_status_history.c.operation_id,
    _operation_status_history.c.occurred_at,
    _operation_status_history.c.id,
)
Index(
    "ix_volta_audit_events_operation_ordered",
    _audit_events.c.operation_id,
    _audit_events.c.occurred_at,
    _audit_events.c.event_id,
)
Index("ix_volta_audit_events_correlation_id", _audit_events.c.correlation_id)

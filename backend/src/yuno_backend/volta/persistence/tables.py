"""Private SQLAlchemy Core table metadata for Volta persistence."""

from sqlalchemy import (
    ARRAY,
    BigInteger,
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
    Column("cargo_label", Text, nullable=False),
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
        "char_length(cargo_label) <= 500",
        name="ck_volta_intake_drafts_cargo_label",
    ),
    CheckConstraint(
        "maximum_amount > '-Infinity'::numeric AND maximum_amount < 'Infinity'::numeric",
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
    Column("cargo_label", Text, nullable=False),
    Column("pickup_date", Date, nullable=False),
    Column("active_mandate_id", UUID(as_uuid=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_operations"),
    CheckConstraint("version > 0", name="ck_volta_operations_version_positive"),
    CheckConstraint(
        "char_length(btrim(cargo_label)) BETWEEN 1 AND 500",
        name="ck_volta_operations_cargo_label",
    ),
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
        "(event_type IN ('NEGOTIATION_STARTED', 'PRE_CONTACT_ESCALATED', "
        "'QUOTE_RECORDED', 'QUOTE_REJECTED', 'COMMITMENT_ACTIVATED', "
        "'COMMITMENT_SUPERSEDED', 'EVIDENCE_RECORDED', 'BRIEF_GENERATED', "
        "'RECAP_GENERATED', 'RECOVERY_REPLACEMENT_APPLIED', 'POST_CONTACT_ESCALATED', "
        "'ESCALATION_RESUMED', 'MANDATE_REPLACED', 'ESCALATION_RESOLVED', "
        "'EXPLICIT_ESCALATION_CREATED', 'NOTIFICATION_ACKNOWLEDGED', "
        "'HANDOFF_REQUESTED', 'HANDOFF_JOINED', 'HANDOFF_FAILED_SAFE', "
        "'HANDOFF_TIMED_OUT_SAFE') "
        "AND metadata = '{}'::jsonb)",
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

_negotiations = Table(
    "volta_negotiations",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("operation_version", Integer, nullable=False),
    Column("mandate_version", Integer, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_negotiations"),
    UniqueConstraint("operation_id", name="uq_volta_negotiations_operation"),
    UniqueConstraint("id", "operation_id", name="uq_volta_negotiations_id_operation"),
    ForeignKeyConstraint(
        ["operation_id"], ["volta_operations.id"], name="fk_volta_negotiations_operation"
    ),
    CheckConstraint("operation_version > 0", name="ck_volta_negotiations_operation_version"),
    CheckConstraint("mandate_version > 0", name="ck_volta_negotiations_mandate_version"),
)

_carrier_sessions = Table(
    "volta_carrier_sessions",
    _metadata,
    Column("call_id", UUID(as_uuid=True), nullable=False),
    Column("negotiation_id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("carrier_id", UUID(as_uuid=True), nullable=False),
    Column("carrier_display_label", Text, nullable=False),
    Column("route_origin", Text, nullable=False),
    Column("route_destination", Text, nullable=False),
    Column("available_snapshot", Boolean, nullable=False),
    Column("fixed_priority", Integer, nullable=False),
    Column("selection_rank", Integer, nullable=False),
    Column("channel", Text, nullable=False),
    Column("state", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("call_id", name="pk_volta_carrier_sessions"),
    UniqueConstraint("negotiation_id", "carrier_id", name="uq_volta_sessions_negotiation_carrier"),
    UniqueConstraint(
        "call_id", "operation_id", "carrier_id", name="uq_volta_sessions_call_operation_carrier"
    ),
    UniqueConstraint("call_id", "operation_id", name="uq_volta_sessions_call_operation"),
    ForeignKeyConstraint(
        ["negotiation_id", "operation_id"],
        ["volta_negotiations.id", "volta_negotiations.operation_id"],
        name="fk_volta_sessions_negotiation_operation",
    ),
    CheckConstraint("fixed_priority > 0", name="ck_volta_sessions_priority_positive"),
    CheckConstraint("selection_rank BETWEEN 1 AND 3", name="ck_volta_sessions_rank"),
    CheckConstraint(
        "channel IN ('BROWSER_TEXT', 'BROWSER_VOICE')", name="ck_volta_sessions_channel"
    ),
    CheckConstraint(
        "state IN ('SELECTED', 'ACTIVE', 'COMPLETED', 'FAILED')", name="ck_volta_sessions_state"
    ),
)

_pre_contact_escalations = Table(
    "volta_pre_contact_escalations",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("negotiation_id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("reason_code", Text, nullable=False),
    Column("correlation_id", UUID(as_uuid=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_pre_contact_escalations"),
    UniqueConstraint("operation_id", name="uq_volta_pre_contact_escalations_operation"),
    ForeignKeyConstraint(
        ["negotiation_id", "operation_id"],
        ["volta_negotiations.id", "volta_negotiations.operation_id"],
        name="fk_volta_pre_contact_escalations_negotiation_operation",
    ),
    CheckConstraint(
        "reason_code = 'no_eligible_carrier'", name="ck_volta_pre_contact_escalations_reason"
    ),
)

_quotes = Table(
    "volta_quotes",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("call_id", UUID(as_uuid=True), nullable=False),
    Column("carrier_id", UUID(as_uuid=True), nullable=False),
    Column("carrier_priority", Integer, nullable=False),
    Column("amount", Numeric, nullable=False),
    Column("currency", Text, nullable=False),
    Column("pickup_window_start", Date, nullable=False),
    Column("pickup_window_end", Date, nullable=False),
    Column("conditions", ARRAY(Text), nullable=False),
    Column("valid_until", DateTime(timezone=True), nullable=False),
    Column("mandate_version", Integer, nullable=False),
    Column("eligibility", Text, nullable=False),
    Column("rejection_reasons", ARRAY(Text), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_quotes"),
    UniqueConstraint("id", "operation_id", name="uq_volta_quotes_id_operation"),
    UniqueConstraint(
        "id", "operation_id", "call_id", "carrier_id", name="uq_volta_quotes_identity_scope"
    ),
    ForeignKeyConstraint(
        ["call_id", "operation_id", "carrier_id"],
        [
            "volta_carrier_sessions.call_id",
            "volta_carrier_sessions.operation_id",
            "volta_carrier_sessions.carrier_id",
        ],
        name="fk_volta_quotes_session_scope",
    ),
    CheckConstraint("carrier_priority > 0", name="ck_volta_quotes_priority_positive"),
    CheckConstraint("mandate_version > 0", name="ck_volta_quotes_mandate_version"),
    CheckConstraint(
        "amount >= 0 AND amount < 'Infinity'::numeric", name="ck_volta_quotes_amount_finite"
    ),
    CheckConstraint(
        "pickup_window_end >= pickup_window_start", name="ck_volta_quotes_window_order"
    ),
    CheckConstraint("eligibility IN ('ELIGIBLE', 'REJECTED')", name="ck_volta_quotes_eligibility"),
    CheckConstraint(
        "(eligibility = 'ELIGIBLE' AND cardinality(rejection_reasons) = 0) OR "
        "(eligibility = 'REJECTED' AND cardinality(rejection_reasons) > 0)",
        name="ck_volta_quotes_rejection_consistency",
    ),
)

_commitments = Table(
    "volta_commitments",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("call_id", UUID(as_uuid=True), nullable=False),
    Column("quote_id", UUID(as_uuid=True), nullable=False),
    Column("carrier_id", UUID(as_uuid=True), nullable=False),
    Column("amount", Numeric, nullable=False),
    Column("currency", Text, nullable=False),
    Column("pickup_window_start", Date, nullable=False),
    Column("pickup_window_end", Date, nullable=False),
    Column("conditions", ARRAY(Text), nullable=False),
    Column("mandate_version", Integer, nullable=False),
    Column("evidence_id", UUID(as_uuid=True), nullable=False),
    Column("lifecycle", Text, nullable=False),
    Column("disposition", Text, nullable=False),
    Column("replaces_commitment_id", UUID(as_uuid=True), nullable=True),
    Column("replaced_by_commitment_id", UUID(as_uuid=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("superseded_at", DateTime(timezone=True), nullable=True),
    PrimaryKeyConstraint("id", name="pk_volta_commitments"),
    UniqueConstraint("id", "operation_id", name="uq_volta_commitments_id_operation"),
    UniqueConstraint(
        "id", "operation_id", "call_id", name="uq_volta_commitments_id_operation_call"
    ),
    UniqueConstraint("id", "evidence_id", name="uq_volta_commitments_id_evidence"),
    UniqueConstraint("quote_id", name="uq_volta_commitments_quote"),
    ForeignKeyConstraint(
        ["quote_id", "operation_id", "call_id", "carrier_id"],
        [
            "volta_quotes.id",
            "volta_quotes.operation_id",
            "volta_quotes.call_id",
            "volta_quotes.carrier_id",
        ],
        name="fk_volta_commitments_quote_scope",
    ),
    ForeignKeyConstraint(
        ["replaces_commitment_id", "operation_id"],
        ["volta_commitments.id", "volta_commitments.operation_id"],
        name="fk_volta_commitments_replaces_operation",
    ),
    ForeignKeyConstraint(
        ["replaced_by_commitment_id", "operation_id"],
        ["volta_commitments.id", "volta_commitments.operation_id"],
        name="fk_volta_commitments_replaced_by_operation",
        deferrable=True,
        initially="DEFERRED",
    ),
    CheckConstraint("mandate_version > 0", name="ck_volta_commitments_mandate_version"),
    CheckConstraint(
        "amount >= 0 AND amount < 'Infinity'::numeric", name="ck_volta_commitments_amount_finite"
    ),
    CheckConstraint(
        "pickup_window_end >= pickup_window_start", name="ck_volta_commitments_window_order"
    ),
    CheckConstraint("lifecycle = 'CANDIDATE'", name="ck_volta_commitments_lifecycle"),
    CheckConstraint(
        "disposition IN ('ACTIVE', 'SUPERSEDED')", name="ck_volta_commitments_disposition"
    ),
    CheckConstraint(
        "(disposition = 'ACTIVE' AND superseded_at IS NULL AND "
        "replaced_by_commitment_id IS NULL) OR (disposition = 'SUPERSEDED' AND "
        "superseded_at IS NOT NULL AND replaced_by_commitment_id IS NOT NULL)",
        name="ck_volta_commitments_disposition_state",
    ),
    CheckConstraint(
        "replaces_commitment_id IS NULL OR replaces_commitment_id <> id",
        name="ck_volta_commitments_not_self_replacing",
    ),
    CheckConstraint(
        "replaced_by_commitment_id IS NULL OR replaced_by_commitment_id <> id",
        name="ck_volta_commitments_not_self_replaced",
    ),
)

_mutation_idempotency = Table(
    "volta_mutation_idempotency",
    _metadata,
    Column("operation_name", Text, nullable=False),
    Column("idempotency_key", Text, nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("fingerprint", Text, nullable=False),
    Column("negotiation_id", UUID(as_uuid=True), nullable=True),
    Column("quote_id", UUID(as_uuid=True), nullable=True),
    Column("commitment_id", UUID(as_uuid=True), nullable=True),
    Column("evidence_reservation_id", UUID(as_uuid=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("operation_name", "idempotency_key", name="pk_volta_mutation_idempotency"),
    UniqueConstraint(
        "operation_name", "negotiation_id", name="uq_volta_mutation_idempotency_negotiation"
    ),
    UniqueConstraint("operation_name", "quote_id", name="uq_volta_mutation_idempotency_quote"),
    UniqueConstraint(
        "operation_name", "commitment_id", name="uq_volta_mutation_idempotency_commitment"
    ),
    ForeignKeyConstraint(
        ["operation_id"], ["volta_operations.id"], name="fk_volta_mutation_idempotency_operation"
    ),
    CheckConstraint(
        "operation_name IN ('start_negotiation', 'record_quote', 'create_commitment', "
        "'attach_commitment_evidence')",
        name="ck_volta_mutation_idempotency_operation_name",
    ),
    CheckConstraint(
        "(operation_name = 'start_negotiation' AND negotiation_id IS NOT NULL AND "
        "quote_id IS NULL AND commitment_id IS NULL AND evidence_reservation_id IS NULL) OR "
        "(operation_name = 'record_quote' AND negotiation_id IS NULL AND "
        "quote_id IS NOT NULL AND commitment_id IS NULL AND evidence_reservation_id IS NULL) OR "
        "(operation_name = 'create_commitment' AND negotiation_id IS NULL AND "
        "quote_id IS NULL AND commitment_id IS NOT NULL AND evidence_reservation_id IS NULL) OR "
        "(operation_name = 'attach_commitment_evidence' AND negotiation_id IS NULL AND "
        "quote_id IS NULL AND commitment_id IS NULL AND evidence_reservation_id IS NOT NULL)",
        name="ck_volta_mutation_idempotency_result_mapping",
    ),
    ForeignKeyConstraint(
        ["negotiation_id", "operation_id"],
        ["volta_negotiations.id", "volta_negotiations.operation_id"],
        name="fk_volta_mutation_idempotency_negotiation_operation",
    ),
    ForeignKeyConstraint(
        ["quote_id", "operation_id"],
        ["volta_quotes.id", "volta_quotes.operation_id"],
        name="fk_volta_mutation_idempotency_quote_operation",
    ),
    ForeignKeyConstraint(
        ["commitment_id", "operation_id"],
        ["volta_commitments.id", "volta_commitments.operation_id"],
        name="fk_volta_mutation_idempotency_commitment_operation",
    ),
    CheckConstraint(
        "char_length(idempotency_key) BETWEEN 8 AND 128 AND idempotency_key ~ '^[ -~]+$'",
        name="ck_volta_mutation_idempotency_key",
    ),
    CheckConstraint(
        "fingerprint ~ '^[0-9a-f]{64}$'", name="ck_volta_mutation_idempotency_fingerprint"
    ),
)

_text_mutation_idempotency = Table(
    "volta_text_mutation_idempotency",
    _metadata,
    Column("operation_name", Text, nullable=False),
    Column("idempotency_key", Text, nullable=False),
    Column("fingerprint", Text, nullable=False),
    Column("draft_id", UUID(as_uuid=True), nullable=True),
    Column("operation_id", UUID(as_uuid=True), nullable=True),
    Column("result_id", UUID(as_uuid=True), nullable=False),
    Column("result_kind", Text, nullable=False),
    Column("result_snapshot", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint(
        "operation_name",
        "idempotency_key",
        name="pk_volta_text_mutation_idempotency",
    ),
    ForeignKeyConstraint(
        ["draft_id"],
        ["volta_intake_drafts.id"],
        name="fk_volta_text_idempotency_draft",
    ),
    ForeignKeyConstraint(
        ["operation_id"],
        ["volta_operations.id"],
        name="fk_volta_text_idempotency_operation",
    ),
    CheckConstraint(
        "operation_name IN ('create_operation_draft', 'approve_operation', "
        "'create_simulated_recap', 'create_call_brief', 'start_inbound_simulation', "
        "'replace_mandate', 'create_escalation', 'acknowledge_notification')",
        name="ck_volta_text_idempotency_operation_name",
    ),
    CheckConstraint(
        "(operation_name = 'create_operation_draft' AND draft_id IS NOT NULL "
        "AND operation_id IS NULL) OR "
        "(operation_name = 'approve_operation' AND draft_id IS NULL "
        "AND operation_id IS NOT NULL) OR "
        "(operation_name NOT IN ('create_operation_draft', 'approve_operation') "
        "AND draft_id IS NULL AND operation_id IS NULL)",
        name="ck_volta_text_idempotency_result_mapping",
    ),
    CheckConstraint(
        "char_length(idempotency_key) BETWEEN 8 AND 128 "
        "AND idempotency_key ~ '^[ -~]+$'",
        name="ck_volta_text_idempotency_key",
    ),
    CheckConstraint(
        "fingerprint ~ '^[0-9a-f]{64}$'",
        name="ck_volta_text_idempotency_fingerprint",
    ),
    CheckConstraint(
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
        name="ck_volta_text_idempotency_result_kind",
    ),
    CheckConstraint(
        "jsonb_typeof(result_snapshot) = 'object' "
        "AND octet_length(result_snapshot::text) <= 33554432",
        name="ck_volta_text_idempotency_result_snapshot",
    ),
)

_outbound_call_attempts = Table(
    "volta_outbound_call_attempts",
    _metadata,
    Column("idempotency_key", Text, nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("request_fingerprint", Text, nullable=False),
    Column("state", Text, nullable=False),
    Column("call_session_id", UUID(as_uuid=True), nullable=True),
    Column("provider_call_id", Text, nullable=True),
    Column("call_status", Text, nullable=True),
    Column("call_created_at", DateTime(timezone=True), nullable=True),
    Column("status_updated_at", DateTime(timezone=True), nullable=True),
    Column("last_status_event_id", Text, nullable=True),
    Column("last_status_sequence_number", BigInteger, nullable=True),
    Column("processed_status_event_ids", ARRAY(Text), nullable=True),
    Column("uncertainty_reason", Text, nullable=True),
    Column("uncertainty_occurred_at", DateTime(timezone=True), nullable=True),
    Column("failure_category", Text, nullable=True),
    Column("failure_status_code", Integer, nullable=True),
    Column("failure_occurred_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("idempotency_key", name="pk_volta_outbound_call_attempts"),
    ForeignKeyConstraint(
        ["operation_id"],
        ["volta_operations.id"],
        name="fk_volta_outbound_call_attempts_operation",
    ),
    UniqueConstraint(
        "provider_call_id", name="uq_volta_outbound_call_attempts_provider_call"
    ),
    CheckConstraint(
        "char_length(idempotency_key) BETWEEN 8 AND 128 "
        "AND idempotency_key ~ '^[ -~]+$'",
        name="ck_volta_outbound_call_attempts_key",
    ),
    CheckConstraint(
        "request_fingerprint ~ '^[0-9a-f]{64}$'",
        name="ck_volta_outbound_call_attempts_fingerprint",
    ),
    CheckConstraint(
        "state IN ('PENDING', 'SUCCEEDED', 'UNCERTAIN', 'FAILED')",
        name="ck_volta_outbound_call_attempts_state",
    ),
    CheckConstraint(
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
    CheckConstraint(
        "call_status IS NULL OR call_status IN ('QUEUED', 'INITIATED', 'RINGING', "
        "'IN_PROGRESS', 'COMPLETED', 'BUSY', 'FAILED', 'NO_ANSWER', 'CANCELED')",
        name="ck_volta_outbound_call_attempts_call_status",
    ),
    CheckConstraint(
        "provider_call_id IS NULL OR provider_call_id ~ "
        "'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'",
        name="ck_volta_outbound_call_attempts_provider_call",
    ),
    CheckConstraint(
        "(last_status_event_id IS NULL AND last_status_sequence_number IS NULL) OR "
        "(last_status_event_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$' "
        "AND last_status_sequence_number >= 0)",
        name="ck_volta_outbound_call_attempts_cursor",
    ),
    CheckConstraint(
        "processed_status_event_ids IS NULL OR "
        "(cardinality(processed_status_event_ids) <= 128 AND "
        "array_to_string(processed_status_event_ids, ',') ~ "
        "'^$|^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}(,[A-Za-z0-9][A-Za-z0-9._:/-]{0,127})*$' "
        "AND (last_status_event_id IS NULL OR "
        "last_status_event_id = ANY(processed_status_event_ids)))",
        name="ck_volta_outbound_call_attempts_processed_events",
    ),
    CheckConstraint(
        "uncertainty_reason IS NULL OR uncertainty_reason IN "
        "('TIMEOUT', 'CONNECTION_LOST', 'INVALID_RESPONSE', 'PROVIDER_FAILURE')",
        name="ck_volta_outbound_call_attempts_uncertainty",
    ),
    CheckConstraint(
        "failure_category IS NULL OR failure_category IN ('AUTHENTICATION', "
        "'PERMISSION', 'RATE_LIMIT', 'TIMEOUT', 'CONNECTION', 'INVALID_REQUEST', "
        "'PROVIDER_REJECTED', 'INVALID_RESPONSE')",
        name="ck_volta_outbound_call_attempts_failure",
    ),
    CheckConstraint(
        "failure_status_code IS NULL OR failure_status_code BETWEEN 100 AND 599",
        name="ck_volta_outbound_call_attempts_failure_status",
    ),
    CheckConstraint(
        "(call_created_at IS NULL AND status_updated_at IS NULL) OR "
        "status_updated_at >= call_created_at",
        name="ck_volta_outbound_call_attempts_call_timestamps",
    ),
    CheckConstraint(
        "updated_at >= created_at",
        name="ck_volta_outbound_call_attempts_timestamps",
    ),
)

Index("ix_volta_outbound_call_attempts_operation", _outbound_call_attempts.c.operation_id)

_human_handoffs = Table(
    "volta_human_handoffs",
    _metadata,
    Column("handoff_id", UUID(as_uuid=True), nullable=False),
    Column("call_id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("operation_version", Integer, nullable=False),
    Column("correlation_id", UUID(as_uuid=True), nullable=False),
    Column("coordinator_destination_label", Text, nullable=False),
    Column("idempotency_key", Text, nullable=False),
    Column("request_fingerprint", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("requested_at", DateTime(timezone=True), nullable=False),
    Column("status_updated_at", DateTime(timezone=True), nullable=False),
    Column("context", JSONB, nullable=False),
    Column("last_status_event_id", Text, nullable=True),
    Column("last_status_sequence_number", BigInteger, nullable=True),
    Column("processed_status_event_ids", ARRAY(Text), nullable=False),
    PrimaryKeyConstraint("handoff_id", name="pk_volta_human_handoffs"),
    UniqueConstraint("idempotency_key", name="uq_volta_human_handoffs_idempotency"),
    ForeignKeyConstraint(
        ["operation_id"], ["volta_operations.id"], name="fk_volta_handoffs_operation"
    ),
    CheckConstraint(
        "char_length(idempotency_key) BETWEEN 8 AND 128 AND "
        "idempotency_key ~ '^[ -~]+$'",
        name="ck_volta_handoffs_key",
    ),
    CheckConstraint(
        "request_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_volta_handoffs_fingerprint"
    ),
    CheckConstraint("operation_version > 0", name="ck_volta_handoffs_operation_version"),
    CheckConstraint(
        "status IN ('CONNECTING', 'JOINED', 'FAILED_SAFE', 'TIMED_OUT_SAFE')",
        name="ck_volta_handoffs_status",
    ),
    CheckConstraint(
        "jsonb_typeof(context) = 'object' AND octet_length(context::text) <= 16384",
        name="ck_volta_handoffs_context",
    ),
    CheckConstraint(
        "cardinality(processed_status_event_ids) <= 128",
        name="ck_volta_handoffs_processed_events",
    ),
    CheckConstraint(
        "(last_status_event_id IS NULL AND last_status_sequence_number IS NULL) OR "
        "(last_status_event_id IS NOT NULL AND last_status_sequence_number >= 0 "
        "AND last_status_event_id = ANY(processed_status_event_ids))",
        name="ck_volta_handoffs_cursor",
    ),
    CheckConstraint(
        "status_updated_at >= requested_at", name="ck_volta_handoffs_timestamps"
    ),
)
Index("ix_volta_handoffs_call", _human_handoffs.c.call_id)
Index("ix_volta_handoffs_operation", _human_handoffs.c.operation_id)
Index(
    "uq_volta_handoffs_one_connecting_per_call",
    _human_handoffs.c.call_id,
    unique=True,
    postgresql_where=_human_handoffs.c.status == "CONNECTING",
)

_ai_authority_fences = Table(
    "volta_ai_authority_fences",
    _metadata,
    Column("call_id", UUID(as_uuid=True), nullable=False),
    Column("handoff_id", UUID(as_uuid=True), nullable=False),
    Column("fenced_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("call_id", name="pk_volta_ai_authority_fences"),
    ForeignKeyConstraint(
        ["handoff_id"], ["volta_human_handoffs.handoff_id"], name="fk_volta_fence_handoff"
    ),
    UniqueConstraint("handoff_id", name="uq_volta_fence_handoff"),
)

_twilio_handoff_bindings = Table(
    "volta_twilio_handoff_bindings",
    _metadata,
    Column("handoff_id", UUID(as_uuid=True), nullable=False),
    Column("call_id", UUID(as_uuid=True), nullable=False),
    Column("remote_call_sid", Text, nullable=False),
    Column("conference_name", Text, nullable=False),
    Column("conference_sid", Text, nullable=True),
    Column("coordinator_call_sid", Text, nullable=True),
    Column("remote_present", Boolean, nullable=False),
    Column("coordinator_present", Boolean, nullable=False),
    Column("remote_last_sequence", BigInteger, nullable=True),
    Column("coordinator_last_sequence", BigInteger, nullable=True),
    PrimaryKeyConstraint("handoff_id", name="pk_volta_twilio_handoff_bindings"),
    ForeignKeyConstraint(
        ["handoff_id"], ["volta_human_handoffs.handoff_id"], name="fk_volta_twilio_binding_handoff"
    ),
    UniqueConstraint("conference_name", name="uq_volta_twilio_binding_conference_name"),
    UniqueConstraint("conference_sid", name="uq_volta_twilio_binding_conference_sid"),
    UniqueConstraint("coordinator_call_sid", name="uq_volta_twilio_binding_coordinator_call"),
    CheckConstraint(
        "remote_call_sid ~ '^CA[0-9a-fA-F]{32}$' AND "
        "(conference_sid IS NULL OR conference_sid ~ '^CF[0-9a-fA-F]{32}$') AND "
        "(coordinator_call_sid IS NULL OR "
        "coordinator_call_sid ~ '^CA[0-9a-fA-F]{32}$')",
        name="ck_volta_twilio_binding_sids",
    ),
    CheckConstraint(
        "(remote_last_sequence IS NULL OR remote_last_sequence >= 0) AND "
        "(coordinator_last_sequence IS NULL OR coordinator_last_sequence >= 0)",
        name="ck_volta_twilio_binding_sequences",
    ),
)

Index("ix_volta_sessions_negotiation", _carrier_sessions.c.negotiation_id)
Index("ix_volta_pre_contact_escalations_negotiation", _pre_contact_escalations.c.negotiation_id)
Index(
    "ix_volta_quotes_operation_comparison",
    _quotes.c.operation_id,
    _quotes.c.eligibility,
    _quotes.c.valid_until,
)
Index("ix_volta_quotes_call", _quotes.c.call_id)
Index(
    "ix_volta_commitments_operation_history",
    _commitments.c.operation_id,
    _commitments.c.created_at,
    _commitments.c.id,
)
Index("ix_volta_commitments_replaces", _commitments.c.replaces_commitment_id)
Index("ix_volta_commitments_replaced_by", _commitments.c.replaced_by_commitment_id)
Index(
    "uq_volta_commitments_one_active",
    _commitments.c.operation_id,
    unique=True,
    postgresql_where=_commitments.c.disposition == "ACTIVE",
)
Index("ix_volta_mutation_idempotency_operation", _mutation_idempotency.c.operation_id)
Index(
    "ix_volta_text_idempotency_draft",
    _text_mutation_idempotency.c.draft_id,
    postgresql_where=_text_mutation_idempotency.c.draft_id.is_not(None),
)
Index(
    "ix_volta_text_idempotency_operation",
    _text_mutation_idempotency.c.operation_id,
    postgresql_where=_text_mutation_idempotency.c.operation_id.is_not(None),
)
Index(
    "ix_volta_mutation_idempotency_negotiation",
    _mutation_idempotency.c.negotiation_id,
    postgresql_where=_mutation_idempotency.c.negotiation_id.is_not(None),
)
Index(
    "ix_volta_mutation_idempotency_quote",
    _mutation_idempotency.c.quote_id,
    postgresql_where=_mutation_idempotency.c.quote_id.is_not(None),
)
Index(
    "ix_volta_mutation_idempotency_commitment",
    _mutation_idempotency.c.commitment_id,
    postgresql_where=_mutation_idempotency.c.commitment_id.is_not(None),
)

_agreement_evidence = Table(
    "volta_agreement_evidence",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("commitment_id", UUID(as_uuid=True), nullable=False),
    Column("recording_reference", Text, nullable=False),
    Column("audio_start_ms", Integer, nullable=False),
    Column("item_id", Text, nullable=False),
    Column("event_id", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_agreement_evidence"),
    UniqueConstraint("commitment_id", name="uq_volta_agreement_evidence_commitment"),
    UniqueConstraint(
        "id", "commitment_id", name="uq_volta_agreement_evidence_id_commitment"
    ),
    ForeignKeyConstraint(
        ["commitment_id"],
        ["volta_commitments.id"],
        name="fk_volta_agreement_evidence_commitment",
    ),
    ForeignKeyConstraint(
        ["commitment_id", "id"],
        ["volta_commitments.id", "volta_commitments.evidence_id"],
        name="fk_volta_agreement_evidence_commitment_artifact",
    ),
    CheckConstraint("audio_start_ms >= 0", name="ck_volta_agreement_evidence_audio_start_ms"),
    CheckConstraint(
        "char_length(recording_reference) BETWEEN 1 AND 200",
        name="ck_volta_agreement_evidence_recording_reference",
    ),
    CheckConstraint(
        "char_length(item_id) BETWEEN 1 AND 200", name="ck_volta_agreement_evidence_item_id"
    ),
    CheckConstraint(
        "char_length(event_id) BETWEEN 1 AND 200", name="ck_volta_agreement_evidence_event_id"
    ),
)

_evidence_reservations = Table(
    "volta_evidence_reservations",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("call_id", UUID(as_uuid=True), nullable=False),
    Column("quote_id", UUID(as_uuid=True), nullable=False),
    Column("recording_reference", Text, nullable=False),
    Column("audio_start_ms", Integer, nullable=False),
    Column("item_id", Text, nullable=False),
    Column("event_id", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("consumed_by_commitment_id", UUID(as_uuid=True), nullable=True),
    PrimaryKeyConstraint("id", name="pk_volta_evidence_reservations"),
    UniqueConstraint("quote_id", name="uq_volta_evidence_reservations_quote"),
    UniqueConstraint(
        "consumed_by_commitment_id", name="uq_volta_evidence_reservations_consumed_commitment"
    ),
    ForeignKeyConstraint(
        ["quote_id", "operation_id"],
        ["volta_quotes.id", "volta_quotes.operation_id"],
        name="fk_volta_evidence_reservations_quote_operation",
    ),
    ForeignKeyConstraint(
        ["consumed_by_commitment_id", "operation_id"],
        ["volta_commitments.id", "volta_commitments.operation_id"],
        name="fk_volta_evidence_reservations_commitment_operation",
    ),
    CheckConstraint("audio_start_ms >= 0", name="ck_volta_evidence_reservations_offset"),
    CheckConstraint(
        "char_length(recording_reference) BETWEEN 1 AND 200",
        name="ck_volta_evidence_reservations_reference",
    ),
    CheckConstraint(
        "char_length(item_id) BETWEEN 1 AND 200 AND char_length(event_id) BETWEEN 1 AND 200",
        name="ck_volta_evidence_reservations_event_ids",
    ),
)

_call_briefs = Table(
    "volta_call_briefs",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("commitment_id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("call_id", UUID(as_uuid=True), nullable=False),
    Column("route_origin", Text, nullable=False),
    Column("route_destination", Text, nullable=False),
    Column("carrier_id", UUID(as_uuid=True), nullable=False),
    Column("agreed_terms_reference", UUID(as_uuid=True), nullable=False),
    Column("mandate_version", Integer, nullable=False),
    Column("facts", ARRAY(Text), nullable=False),
    Column("objections", ARRAY(Text), nullable=False),
    Column("changes", ARRAY(Text), nullable=False),
    Column("unresolved_items", ARRAY(Text), nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_call_briefs"),
    UniqueConstraint("commitment_id", name="uq_volta_call_briefs_commitment"),
    ForeignKeyConstraint(
        ["commitment_id", "operation_id", "call_id"],
        [
            "volta_commitments.id",
            "volta_commitments.operation_id",
            "volta_commitments.call_id",
        ],
        name="fk_volta_call_briefs_commitment_operation_call",
    ),
    ForeignKeyConstraint(
        ["call_id", "operation_id"],
        ["volta_carrier_sessions.call_id", "volta_carrier_sessions.operation_id"],
        name="fk_volta_call_briefs_call_operation",
    ),
    CheckConstraint("mandate_version > 0", name="ck_volta_call_briefs_mandate_version"),
    CheckConstraint(
        "cardinality(facts) <= 50 AND volta_bounded_text_array(facts) "
        "AND cardinality(objections) <= 50 AND volta_bounded_text_array(objections) "
        "AND cardinality(changes) <= 50 AND volta_bounded_text_array(changes) "
        "AND cardinality(unresolved_items) <= 50 "
        "AND volta_bounded_text_array(unresolved_items)",
        name="ck_volta_call_briefs_structured_fields",
    ),
)

_recaps = Table(
    "volta_recaps",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("commitment_id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("call_id", UUID(as_uuid=True), nullable=False),
    Column("disclosure_state", Text, nullable=False),
    Column("content_hash", Text, nullable=False),
    Column("rendered_content", Text, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_recaps"),
    UniqueConstraint("commitment_id", name="uq_volta_recaps_commitment"),
    ForeignKeyConstraint(
        ["commitment_id", "operation_id", "call_id"],
        [
            "volta_commitments.id",
            "volta_commitments.operation_id",
            "volta_commitments.call_id",
        ],
        name="fk_volta_recaps_commitment_operation_call",
    ),
    ForeignKeyConstraint(
        ["call_id", "operation_id"],
        ["volta_carrier_sessions.call_id", "volta_carrier_sessions.operation_id"],
        name="fk_volta_recaps_call_operation",
    ),
    CheckConstraint("disclosure_state = 'SIMULATED'", name="ck_volta_recaps_disclosure_state"),
    CheckConstraint(
        "content_hash ~ '^[0-9a-f]{64}$' AND "
        "char_length(rendered_content) <= 10000 "
        "AND char_length(btrim(rendered_content)) >= 1",
        name="ck_volta_recaps_content",
    ),
)

_post_contact_escalations = Table(
    "volta_post_contact_escalations",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("commitment_id", UUID(as_uuid=True), nullable=True),
    Column("call_id", UUID(as_uuid=True), nullable=True),
    Column("reason_code", Text, nullable=False),
    Column("operation_version", Integer, nullable=False),
    Column("mandate_version", Integer, nullable=False),
    Column("resolved", Boolean, nullable=False),
    Column("correlation_id", UUID(as_uuid=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    Column("conflict", Text, nullable=True),
    Column("attempted_alternatives", ARRAY(Text), nullable=True),
    Column("recommended_action", Text, nullable=True),
    PrimaryKeyConstraint("id", name="pk_volta_post_contact_escalations"),
    UniqueConstraint(
        "id", "operation_id", name="uq_volta_post_contact_escalations_id_operation"
    ),
    ForeignKeyConstraint(
        ["commitment_id", "operation_id"],
        ["volta_commitments.id", "volta_commitments.operation_id"],
        name="fk_volta_post_contact_escalations_commitment_operation",
    ),
    ForeignKeyConstraint(
        ["call_id", "operation_id"],
        ["volta_carrier_sessions.call_id", "volta_carrier_sessions.operation_id"],
        name="fk_volta_post_contact_escalations_call_operation",
    ),
    CheckConstraint(
        "operation_version > 0", name="ck_volta_post_contact_escalations_op_version"
    ),
    CheckConstraint(
        "mandate_version > 0", name="ck_volta_post_contact_escalations_mandate_version"
    ),
    CheckConstraint(
        "(resolved AND resolved_at IS NOT NULL) OR (NOT resolved AND resolved_at IS NULL)",
        name="ck_volta_post_contact_escalations_resolved_state",
    ),
    CheckConstraint(
        "(call_id IS NULL AND conflict IS NULL AND attempted_alternatives IS NULL "
        "AND recommended_action IS NULL) OR "
        "(call_id IS NOT NULL AND conflict IS NOT NULL AND attempted_alternatives IS NOT NULL "
        "AND char_length(btrim(conflict)) BETWEEN 1 AND 500 "
        "AND cardinality(attempted_alternatives) <= 25 "
        "AND volta_bounded_text_array(attempted_alternatives) "
        "AND recommended_action IS NOT NULL "
        "AND char_length(btrim(recommended_action)) BETWEEN 1 AND 500)",
        name="ck_volta_post_contact_escalations_context",
    ),
)

_recovery_attempts = Table(
    "volta_recovery_attempts",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("commitment_id", UUID(as_uuid=True), nullable=False),
    Column("scenario", Text, nullable=False),
    Column("before_operation_version", Integer, nullable=False),
    Column("after_operation_version", Integer, nullable=False),
    Column("decision_reason", Text, nullable=False),
    Column("outcome", Text, nullable=False),
    Column("resulting_commitment_id", UUID(as_uuid=True), nullable=True),
    Column("resulting_evidence_id", UUID(as_uuid=True), nullable=True),
    Column("escalation_id", UUID(as_uuid=True), nullable=True),
    Column("correlation_id", UUID(as_uuid=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("id", name="pk_volta_recovery_attempts"),
    ForeignKeyConstraint(
        ["commitment_id", "operation_id"],
        ["volta_commitments.id", "volta_commitments.operation_id"],
        name="fk_volta_recovery_attempts_commitment_operation",
    ),
    ForeignKeyConstraint(
        ["resulting_commitment_id", "operation_id"],
        ["volta_commitments.id", "volta_commitments.operation_id"],
        name="fk_volta_recovery_attempts_resulting_commitment_operation",
    ),
    ForeignKeyConstraint(
        ["resulting_evidence_id", "resulting_commitment_id"],
        ["volta_agreement_evidence.id", "volta_agreement_evidence.commitment_id"],
        name="fk_volta_recovery_attempts_resulting_evidence_commitment",
        deferrable=True,
        initially="DEFERRED",
    ),
    ForeignKeyConstraint(
        ["escalation_id", "operation_id"],
        [
            "volta_post_contact_escalations.id",
            "volta_post_contact_escalations.operation_id",
        ],
        name="fk_volta_recovery_attempts_escalation_operation",
    ),
    CheckConstraint(
        "outcome IN ('REPLACED', 'ESCALATED')", name="ck_volta_recovery_attempts_outcome"
    ),
    CheckConstraint(
        "scenario IN ('MANDATE_SAFE', 'OUT_OF_MANDATE') "
        "AND before_operation_version > 0 "
        "AND after_operation_version = before_operation_version + 1 "
        "AND char_length(btrim(decision_reason)) BETWEEN 1 AND 500",
        name="ck_volta_recovery_attempts_complete_decision",
    ),
    CheckConstraint(
        "(scenario = 'MANDATE_SAFE' AND outcome = 'REPLACED') OR "
        "(scenario = 'OUT_OF_MANDATE' AND outcome = 'ESCALATED')",
        name="ck_volta_recovery_attempts_scenario_outcome",
    ),
    CheckConstraint(
        "(outcome = 'REPLACED' AND resulting_commitment_id IS NOT NULL AND "
        "resulting_evidence_id IS NOT NULL AND escalation_id IS NULL) OR "
        "(outcome = 'ESCALATED' AND resulting_commitment_id IS NULL "
        "AND resulting_evidence_id IS NULL AND escalation_id IS NOT NULL)",
        name="ck_volta_recovery_attempts_outcome_state",
    ),
)

_notifications = Table(
    "volta_notifications",
    _metadata,
    Column("id", UUID(as_uuid=True), nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False),
    Column("commitment_id", UUID(as_uuid=True), nullable=False),
    Column("reason_code", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("operation_version", Integer, nullable=True),
    Column("recovery_before", JSONB, nullable=True),
    Column("recovery_after", JSONB, nullable=True),
    Column("decision_reason", Text, nullable=True),
    Column("message", Text, nullable=True),
    Column("correlation_id", UUID(as_uuid=True), nullable=True),
    Column("acknowledged_by", Text, nullable=True),
    Column("acknowledged_at", DateTime(timezone=True), nullable=True),
    PrimaryKeyConstraint("id", name="pk_volta_notifications"),
    ForeignKeyConstraint(
        ["commitment_id", "operation_id"],
        ["volta_commitments.id", "volta_commitments.operation_id"],
        name="fk_volta_notifications_commitment_operation",
    ),
    CheckConstraint(
        "(acknowledged_by IS NULL AND acknowledged_at IS NULL) OR "
        "(char_length(btrim(acknowledged_by)) BETWEEN 1 AND 500 "
        "AND acknowledged_at IS NOT NULL)",
        name="ck_volta_notifications_acknowledgement",
    ),
    CheckConstraint(
        "(operation_version IS NULL AND recovery_before IS NULL AND recovery_after IS NULL "
        "AND decision_reason IS NULL AND message IS NULL AND correlation_id IS NULL) OR "
        "(operation_version > 0 AND recovery_before IS NOT NULL "
        "AND recovery_after IS NOT NULL AND decision_reason IS NOT NULL "
        "AND message IS NOT NULL AND correlation_id IS NOT NULL "
        "AND jsonb_typeof(recovery_before) = 'object' "
        "AND jsonb_typeof(recovery_after) = 'object' "
        "AND char_length(btrim(decision_reason)) BETWEEN 1 AND 500 "
        "AND char_length(btrim(message)) BETWEEN 1 AND 500)",
        name="ck_volta_notifications_recovery_context",
    ),
)

Index(
    "ix_volta_call_briefs_operation_order",
    _call_briefs.c.operation_id,
    _call_briefs.c.generated_at,
    _call_briefs.c.id,
)
Index(
    "ix_volta_recaps_operation_order",
    _recaps.c.operation_id,
    _recaps.c.generated_at,
    _recaps.c.id,
)
Index(
    "ix_volta_post_contact_escalations_operation_order",
    _post_contact_escalations.c.operation_id,
    _post_contact_escalations.c.created_at,
    _post_contact_escalations.c.id,
)
Index(
    "ix_volta_post_contact_escalations_call",
    _post_contact_escalations.c.call_id,
    postgresql_where=_post_contact_escalations.c.call_id.is_not(None),
)
Index(
    "uq_volta_post_contact_escalations_one_unresolved",
    _post_contact_escalations.c.operation_id,
    unique=True,
    postgresql_where=_post_contact_escalations.c.resolved.is_(False),
)
Index(
    "ix_volta_recovery_attempts_operation",
    _recovery_attempts.c.operation_id,
    _recovery_attempts.c.created_at,
    _recovery_attempts.c.id,
)
Index(
    "ix_volta_notifications_operation_order",
    _notifications.c.operation_id,
    _notifications.c.created_at,
    _notifications.c.id,
)

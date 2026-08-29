"""Synthetic, deterministic contract fixtures with no provider or participant data."""

from typing import Any

IDS = {
    "draft": "00000000-0000-4000-8000-000000000001",
    "operation": "00000000-0000-4000-8000-000000000002",
    "mandate": "00000000-0000-4000-8000-000000000003",
    "negotiation": "00000000-0000-4000-8000-000000000004",
    "call": "00000000-0000-4000-8000-000000000005",
    "carrier": "00000000-0000-4000-8000-000000000006",
    "quote": "00000000-0000-4000-8000-000000000007",
    "evidence": "00000000-0000-4000-8000-000000000008",
    "commitment": "00000000-0000-4000-8000-000000000009",
    "recap": "00000000-0000-4000-8000-000000000010",
    "brief": "00000000-0000-4000-8000-000000000011",
    "recovery": "00000000-0000-4000-8000-000000000012",
    "escalation": "00000000-0000-4000-8000-000000000013",
    "notification": "00000000-0000-4000-8000-000000000014",
    "correlation": "00000000-0000-4000-8000-000000000015",
    "event": "00000000-0000-4000-8000-000000000016",
}
NOW = "2026-08-29T12:00:00Z"


def pickup_window() -> dict[str, str]:
    return {"start_date": "2026-09-01", "end_date": "2026-09-02"}


def terms() -> dict[str, Any]:
    return {
        "amount_minor": 125000,
        "currency": "MXN",
        "pickup_window": pickup_window(),
        "conditions": ["sealed container"],
    }


def evidence() -> dict[str, Any]:
    return {
        "evidence_id": IDS["evidence"],
        "call_id": IDS["call"],
        "recording_reference": "private-demo-recording-001",
        "audio_start_ms": 4200,
        "item_id": "synthetic-item-001",
        "event_id": "synthetic-event-001",
        "lifecycle": "CANDIDATE",
        "created_at": NOW,
    }


def commitment() -> dict[str, Any]:
    return {
        "commitment_id": IDS["commitment"],
        "operation_id": IDS["operation"],
        "call_id": IDS["call"],
        "quote_id": IDS["quote"],
        "carrier_id": IDS["carrier"],
        "agreed_terms": terms(),
        "mandate_version": 1,
        "evidence": evidence(),
        "lifecycle": "SIMULATED",
        "disposition": "ACTIVE",
        "replaces_commitment_id": None,
        "created_at": NOW,
        "superseded_at": None,
    }


def escalation() -> dict[str, Any]:
    return {
        "escalation_id": IDS["escalation"],
        "operation_id": IDS["operation"],
        "call_id": IDS["call"],
        "conflict": "Pickup window falls outside the current mandate.",
        "attempted_alternatives": ["Requested the approved window"],
        "recommended_action": "Coordinator review required",
        "resolution_state": "OPEN",
        "correlation_id": IDS["correlation"],
        "created_at": NOW,
        "resolved_at": None,
    }


def notification() -> dict[str, Any]:
    return {
        "notification_id": IDS["notification"],
        "operation_id": IDS["operation"],
        "message": "Synthetic recovery requires coordinator review.",
        "acknowledged": False,
        "acknowledged_by": None,
        "acknowledged_at": None,
        "correlation_id": IDS["correlation"],
        "created_at": NOW,
    }


def operation() -> dict[str, Any]:
    return {
        "operation_id": IDS["operation"],
        "route": {"origin": "Manzanillo", "destination": "Guadalajara"},
        "cargo_label": "Synthetic container",
        "status": "READY",
        "operation_version": 1,
        "active_mandate": {
            "mandate_id": IDS["mandate"],
            "version": 1,
            "maximum_amount_minor": 150000,
            "currency": "MXN",
            "pickup_window": pickup_window(),
            "allowed_conditions": ["sealed container"],
            "escalation_conditions": ["amount exceeds mandate"],
            "approval_actor": "demo-coordinator",
            "approved_at": NOW,
        },
        "negotiation_summary": None,
        "active_commitment": None,
        "open_escalation": None,
        "notifications": [],
        "created_at": NOW,
        "updated_at": NOW,
    }


def response_for(operation_id: str) -> dict[str, Any]:
    responses: dict[str, dict[str, Any]] = {
        "create_operation_draft": {
            "draft_id": IDS["draft"],
            "source_prompt": "Move a synthetic container from Manzanillo to Guadalajara.",
            "requested_language": "EN_US",
            "extraction_policy_version": "intake-v1",
            "proposed_route": {"origin": "Manzanillo", "destination": "Guadalajara"},
            "proposed_pickup_date": "2026-09-01",
            "proposed_mandate": {
                "maximum_amount_minor": 150000,
                "currency": "MXN",
                "pickup_window": pickup_window(),
                "allowed_conditions": ["sealed container"],
                "escalation_conditions": ["amount exceeds mandate"],
            },
            "validation_issues": [],
            "approval_eligible": True,
            "draft_version": 1,
            "created_at": NOW,
            "updated_at": NOW,
        },
        "approve_operation": operation(),
        "get_operation": operation(),
        "start_negotiation": {
            "negotiation_id": IDS["negotiation"],
            "operation_id": IDS["operation"],
            "operation_version": 2,
            "sessions": [
                {
                    "call_id": IDS["call"],
                    "carrier": {
                        "carrier_id": IDS["carrier"],
                        "display_name": "Synthetic Transport One",
                        "eligible": True,
                        "deterministic_rank": 1,
                        "ranking_evidence": ["route coverage", "available"],
                    },
                    "channel": "BROWSER_TEXT",
                    "direction": "OUTBOUND_SIMULATION",
                    "state": "SELECTED",
                    "started_at": None,
                    "ended_at": None,
                }
            ],
            "pre_contact_escalation": None,
            "started_at": NOW,
        },
        "record_quote": {
            "quote_id": IDS["quote"],
            "operation_id": IDS["operation"],
            "call_id": IDS["call"],
            "carrier_id": IDS["carrier"],
            "terms": terms(),
            "valid_until": "2026-08-29T13:00:00Z",
            "mandate_version": 1,
            "eligibility": "ELIGIBLE",
            "rejection_reasons": [],
            "created_at": NOW,
        },
        "attach_commitment_evidence": evidence(),
        "create_candidate_commitment": commitment(),
        "create_simulated_recap": {
            "recap_id": IDS["recap"],
            "operation_id": IDS["operation"],
            "call_id": IDS["call"],
            "commitment_id": IDS["commitment"],
            "channel": "SIMULATED",
            "content_hash": "sha256:synthetic-recap",
            "rendered_content": "Simulated agreement recap.",
            "created_at": NOW,
        },
        "create_call_brief": {
            "brief_id": IDS["brief"],
            "operation_id": IDS["operation"],
            "call_id": IDS["call"],
            "facts": ["Carrier is available"],
            "objections": [],
            "changes": [],
            "unresolved_items": [],
            "created_at": NOW,
        },
        "start_inbound_simulation": {
            "recovery_id": IDS["recovery"],
            "operation_id": IDS["operation"],
            "scenario": "OUT_OF_MANDATE",
            "before_operation_version": 2,
            "after_operation_version": 2,
            "decision_reason": "Coordinator authority is required.",
            "active_commitment": commitment(),
            "escalation": escalation(),
            "correlation_id": IDS["correlation"],
            "created_at": NOW,
        },
        "replace_mandate": operation(),
        "create_escalation": escalation(),
        "acknowledge_notification": {
            **notification(),
            "acknowledged": True,
            "acknowledged_by": "demo-coordinator",
            "acknowledged_at": NOW,
        },
        "get_operation_audit": {
            "operation_id": IDS["operation"],
            "events": [
                {
                    "event_id": IDS["event"],
                    "operation_version": 1,
                    "actor_kind": "COORDINATOR",
                    "event_type": "operation.approved",
                    "occurred_at": NOW,
                    "correlation_id": IDS["correlation"],
                    "metadata": {"draft_version": 1},
                }
            ],
            "quote_comparison": [
                {
                    "quote_id": IDS["quote"],
                    "carrier_id": IDS["carrier"],
                    "amount_minor": 125000,
                    "currency": "MXN",
                    "eligible": True,
                    "selected": True,
                    "rejection_reasons": [],
                }
            ],
            "next_cursor": None,
        },
    }
    return responses[operation_id]


def request_for(operation_id: str) -> dict[str, Any] | None:
    requests: dict[str, dict[str, Any] | None] = {
        "create_operation_draft": {
            "source_prompt": "Move a synthetic container from Manzanillo to Guadalajara.",
            "requested_language": "EN_US",
            "extraction_policy_version": "intake-v1",
        },
        "approve_operation": {
            "draft_id": IDS["draft"],
            "expected_draft_version": 1,
            "approval_actor": "demo-coordinator",
        },
        "get_operation": None,
        "start_negotiation": {"expected_operation_version": 1, "channel": "BROWSER_TEXT"},
        "record_quote": {
            "expected_operation_version": 2,
            "carrier_id": IDS["carrier"],
            "mandate_version": 1,
            "terms": terms(),
            "valid_until": "2026-08-29T13:00:00Z",
        },
        "attach_commitment_evidence": {
            "expected_operation_version": 2,
            "recording_reference": "private-demo-recording-001",
            "audio_start_ms": 4200,
            "item_id": "synthetic-item-001",
            "event_id": "synthetic-event-001",
        },
        "create_candidate_commitment": {
            "expected_operation_version": 2,
            "quote_id": IDS["quote"],
            "mandate_version": 1,
            "evidence_id": IDS["evidence"],
        },
        "create_simulated_recap": {
            "expected_operation_version": 3,
            "commitment_id": IDS["commitment"],
            "rendered_content": "Simulated agreement recap.",
        },
        "create_call_brief": {
            "expected_operation_version": 3,
            "facts": ["Carrier is available"],
            "objections": [],
            "changes": [],
            "unresolved_items": [],
        },
        "start_inbound_simulation": {
            "expected_operation_version": 3,
            "scenario": "OUT_OF_MANDATE",
            "active_commitment_id": IDS["commitment"],
        },
        "replace_mandate": {
            "expected_operation_version": 3,
            "resolved_escalation_id": IDS["escalation"],
            "maximum_amount_minor": 175000,
            "currency": "MXN",
            "pickup_window": pickup_window(),
            "allowed_conditions": ["sealed container"],
            "escalation_conditions": ["amount exceeds mandate"],
            "approval_actor": "demo-coordinator",
        },
        "create_escalation": {
            "expected_operation_version": 3,
            "conflict": "Pickup window falls outside the current mandate.",
            "attempted_alternatives": ["Requested the approved window"],
            "recommended_action": "Coordinator review required",
        },
        "acknowledge_notification": {
            "expected_operation_version": 3,
            "acknowledged_by": "demo-coordinator",
        },
        "get_operation_audit": None,
    }
    return requests[operation_id]

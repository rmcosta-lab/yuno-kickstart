import type {
  AuditTimelineResponse,
  CallBriefResponse,
  CommitmentResponse,
  CoordinatorNotificationResponse,
  EscalationResponse,
  QuoteComparisonRow,
  RecoverySimulationResponse,
  WrittenRecapResponse,
} from "@/lib/api/generated/models";

export const AUDIT_SOURCE_KINDS = [
  "event",
  "quote",
  "commitment",
  "recap",
  "brief",
  "recovery",
  "escalation",
  "notification",
] as const;

export type AuditSourceKind = (typeof AUDIT_SOURCE_KINDS)[number];

export type AuditPresentationItem = {
  id: string;
  timestamp: string;
  sourceKind: AuditSourceKind;
  title: string;
  description: string;
  state?: string;
  correlationId?: string;
};

function moneyLabel(amountMinor: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amountMinor / 100);
}

function quoteItem(quote: QuoteComparisonRow): AuditPresentationItem {
  return {
    id: quote.quote_id,
    timestamp: quote.created_at,
    sourceKind: "quote",
    title: `Quote · ${quote.carrier_display_name}`,
    description: `${moneyLabel(quote.terms.amount_minor, quote.terms.currency)} · mandate v${quote.mandate_version}`,
    state: quote.selected ? "SELECTED" : quote.eligibility,
  };
}

function commitmentItem(commitment: CommitmentResponse): AuditPresentationItem {
  return {
    id: commitment.commitment_id,
    timestamp: commitment.created_at,
    sourceKind: "commitment",
    title: `Commitment · ${commitment.carrier_id}`,
    description: `${moneyLabel(commitment.agreed_terms.amount_minor, commitment.agreed_terms.currency)} · mandate v${commitment.mandate_version}`,
    state: `${commitment.lifecycle} · ${commitment.disposition}`,
  };
}

function recapItem(recap: WrittenRecapResponse): AuditPresentationItem {
  return {
    id: recap.recap_id,
    timestamp: recap.created_at,
    sourceKind: "recap",
    title: `Written recap · ${recap.channel}`,
    description: recap.rendered_content,
  };
}

function briefItem(brief: CallBriefResponse): AuditPresentationItem {
  const counts = [
    `${brief.facts?.length ?? 0} facts`,
    `${brief.changes?.length ?? 0} changes`,
    `${brief.objections?.length ?? 0} objections`,
    `${brief.unresolved_items?.length ?? 0} unresolved`,
  ];
  return {
    id: brief.brief_id,
    timestamp: brief.created_at,
    sourceKind: "brief",
    title: "Call brief",
    description: counts.join(" · "),
  };
}

function recoveryItem(
  recovery: RecoverySimulationResponse,
): AuditPresentationItem {
  return {
    id: recovery.recovery_id,
    timestamp: recovery.created_at,
    sourceKind: "recovery",
    title: `Recovery · ${recovery.scenario}`,
    description: `${recovery.decision_reason} · operation v${recovery.before_operation_version} → v${recovery.after_operation_version}`,
    state: recovery.escalation?.resolution_state,
    correlationId: recovery.correlation_id,
  };
}

function escalationItem(escalation: EscalationResponse): AuditPresentationItem {
  return {
    id: escalation.escalation_id,
    timestamp: escalation.created_at,
    sourceKind: "escalation",
    title: "Escalation",
    description: escalation.conflict,
    state: escalation.resolution_state,
    correlationId: escalation.correlation_id,
  };
}

function notificationItem(
  notification: CoordinatorNotificationResponse,
): AuditPresentationItem {
  return {
    id: notification.notification_id,
    timestamp: notification.created_at,
    sourceKind: "notification",
    title: "Coordinator notification",
    description: notification.message,
    state: notification.acknowledged ? "ACKNOWLEDGED" : "PENDING",
    correlationId: notification.correlation_id,
  };
}

export function auditItemsFromPages(
  pages: readonly AuditTimelineResponse[],
): AuditPresentationItem[] {
  const byIdentity = new Map<string, AuditPresentationItem>();

  for (const page of pages) {
    const items: AuditPresentationItem[] = [
      ...page.events.map((event) => ({
        id: event.event_id,
        timestamp: event.occurred_at,
        sourceKind: "event" as const,
        title: event.event_type,
        description: `${event.actor_kind} · operation v${event.operation_version}`,
        correlationId: event.correlation_id,
      })),
      ...page.quote_comparison.map(quoteItem),
      ...page.commitment_history.map(commitmentItem),
      ...page.recaps.map(recapItem),
      ...page.briefs.map(briefItem),
      ...page.recoveries.map(recoveryItem),
      ...page.escalations.map(escalationItem),
      ...page.notifications.map(notificationItem),
    ];

    for (const item of items) {
      byIdentity.set(`${item.sourceKind}:${item.id}`, item);
    }
  }

  return [...byIdentity.values()].sort((left, right) => {
    const timestamp = left.timestamp.localeCompare(right.timestamp);
    if (timestamp !== 0) return timestamp;
    const id = left.id.localeCompare(right.id);
    if (id !== 0) return id;
    return left.sourceKind.localeCompare(right.sourceKind);
  });
}

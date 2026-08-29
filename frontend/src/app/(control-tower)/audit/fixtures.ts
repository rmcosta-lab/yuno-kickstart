import type { AuditTimelineItemProps } from "@/components/control-tower/audit-timeline-item";

export const auditEvents: Omit<AuditTimelineItemProps, "isLast">[] = [
  {
    timestampLabel: "2026-08-29 09:40:12",
    actor: "System",
    action: "recorded a mandate-safe winner transition for OP-1041.",
    correlationId: "corr_op-1041_7f3a",
  },
  {
    timestampLabel: "2026-08-29 09:22:05",
    actor: "Naviera del Caribe session",
    action: "submitted a quote of 890.00 USD for OP-1041.",
    correlationId: "corr_op-1041_7f3a",
  },
  {
    timestampLabel: "2026-08-29 08:55:31",
    actor: "J. Souza",
    action: "approved mandate v2 for OP-1041.",
    correlationId: "corr_op-1041_7f3a",
  },
  {
    timestampLabel: "2026-08-29 08:52:47",
    actor: "J. Souza",
    action: "submitted the intake prompt for OP-1041.",
    correlationId: "corr_op-1041_7f3a",
  },
  {
    timestampLabel: "2026-08-28 16:45:02",
    actor: "J. Souza",
    action:
      "replaced the mandate for OP-1039 after an out-of-mandate escalation.",
    correlationId: "corr_op-1039_2ac1",
  },
];

import type { StatusTone } from "@/components/control-tower/status-badge";

export type RecoveryAttempt = {
  id: string;
  kind: string;
  status: { tone: StatusTone; label: string };
  description: string;
  timestampLabel: string;
};

export const recoveryAttempts: RecoveryAttempt[] = [
  {
    id: "RECOVERY-2201",
    kind: "Inbound renegotiation (good simulation)",
    status: { tone: "success", label: "MANDATE-SAFE" },
    description:
      "Carrier called back proposing a new pickup time within the existing mandate. Winner transitioned atomically and the coordinator was notified.",
    timestampLabel: "2026-08-29 09:40",
  },
  {
    id: "RECOVERY-2198",
    kind: "Inbound renegotiation (bad simulation)",
    status: { tone: "danger", label: "OUT OF MANDATE" },
    description:
      "Carrier requested a price above the mandate's ceiling. The operation escalated and paused until a coordinator issues a new mandate version.",
    timestampLabel: "2026-08-28 16:12",
  },
  {
    id: "RECOVERY-2190",
    kind: "Mandate replacement",
    status: { tone: "neutral", label: "SUPERSEDED" },
    description:
      "A human coordinator replaced the mandate with a higher price limit after the escalation above. Negotiation resumed with the new version.",
    timestampLabel: "2026-08-28 16:45",
  },
];

import type { EscalationBannerProps } from "@/components/control-tower/escalation-banner";

export const escalations: EscalationBannerProps[] = [
  {
    reason: "Out-of-mandate quote",
    operationLabel: "OP-1039",
    status: { tone: "danger", label: "OPEN" },
    raisedAtLabel: "2026-08-28 16:12",
    description:
      "Every candidate carrier quoted above the mandate's price limit. Negotiation is paused until a coordinator issues a new mandate version.",
  },
  {
    reason: "No eligible carrier",
    operationLabel: "OP-1037",
    status: { tone: "warning", label: "RESOLVED" },
    raisedAtLabel: "2026-08-27 11:05",
    description:
      "Route and availability filtering found no eligible carrier before contact. A coordinator manually sourced a carrier outside the fixed ranking.",
  },
];

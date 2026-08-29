import type { SessionCardProps } from "@/components/control-tower/session-card";

export const carrierSessions: SessionCardProps[] = [
  {
    carrierName: "Naviera del Caribe",
    channel: "Text negotiation",
    status: { tone: "success", label: "ACTIVE" },
    summary:
      "Quote received for the 40ft dry container move, awaiting comparison against remaining candidates.",
    updatedAtLabel: "Updated 2026-08-29 09:22",
  },
  {
    carrierName: "Transportes Andinos SAS",
    channel: "Text negotiation",
    status: { tone: "pending", label: "CONNECTING" },
    summary: "Session opened, waiting for the carrier's first response.",
    updatedAtLabel: "Updated 2026-08-29 09:18",
  },
  {
    carrierName: "Logística Portuaria del Norte",
    channel: "Text negotiation",
    status: { tone: "neutral", label: "COMPLETED" },
    summary:
      "Quote submitted outside the mandate's price limit; rejected automatically and archived.",
    updatedAtLabel: "Updated 2026-08-29 08:47",
  },
  {
    carrierName: "Carga Rápida del Magdalena",
    channel: "Text negotiation",
    status: { tone: "danger", label: "FAILED" },
    summary: "Carrier did not respond within the session timeout window.",
    updatedAtLabel: "Updated 2026-08-28 17:40",
  },
];

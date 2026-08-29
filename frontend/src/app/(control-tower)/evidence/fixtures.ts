import type { StatusTone } from "@/components/control-tower/status-badge";

export type EvidenceRecord = {
  sessionId: string;
  carrierName: string;
  status: { tone: StatusTone; label: string };
  audioStartLabel: string;
  itemId: string;
  eventId: string;
  recapSummary: string;
};

export const evidenceRecords: EvidenceRecord[] = [
  {
    sessionId: "SESSION-8841",
    carrierName: "Naviera del Caribe",
    status: { tone: "neutral", label: "SIMULATED" },
    audioStartLabel: "audio_start_ms: 128400",
    itemId: "item_6f2a1c",
    eventId: "evt_9931d0",
    recapSummary:
      "SIMULATED recap: carrier confirmed pickup Monday 08:00 at 890.00 USD, standard handling, within mandate.",
  },
  {
    sessionId: "SESSION-8809",
    carrierName: "Transportes Andinos SAS",
    status: { tone: "neutral", label: "SIMULATED" },
    audioStartLabel: "audio_start_ms: 41200",
    itemId: "item_0b7fd4",
    eventId: "evt_1c4e88",
    recapSummary:
      "SIMULATED recap: carrier proposed 935.00 USD with a nine-hour pickup window; superseded by a lower quote.",
  },
];

import type { StatusTone } from "@/components/control-tower/status-badge";

export type MandateVersion = {
  operationId: string;
  version: number;
  priceLimit: string;
  pickupWindow: string;
  conditions: string[];
  authority: string;
  status: { tone: StatusTone; label: string };
  approvedByLabel?: string;
};

export const mandateVersions: MandateVersion[] = [
  {
    operationId: "OP-1042",
    version: 1,
    priceLimit: "950.00 USD",
    pickupWindow: "2026-08-31 08:00 – 18:00",
    conditions: ["40ft dry container", "Standard handling"],
    authority: "Coordinator: J. Souza",
    status: { tone: "pending", label: "PENDING APPROVAL" },
  },
  {
    operationId: "OP-1041",
    version: 2,
    priceLimit: "700.00 USD",
    pickupWindow: "2026-08-27 07:00 – 2026-08-28 19:00",
    conditions: [
      "20ft reefer container",
      "Temperature-controlled",
      "Chain-of-custody photo required",
    ],
    authority: "Coordinator: J. Souza",
    status: { tone: "success", label: "APPROVED" },
    approvedByLabel: "Approved 2026-08-29 08:55 by J. Souza",
  },
  {
    operationId: "OP-1039",
    version: 1,
    priceLimit: "600.00 USD",
    pickupWindow: "2026-08-29 06:00 – 20:00",
    conditions: ["40ft dry container", "Free-trade zone clearance"],
    authority: "Coordinator: J. Souza",
    status: { tone: "neutral", label: "DRAFT" },
  },
];

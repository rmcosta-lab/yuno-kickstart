import type { StatusTone } from "@/components/control-tower/status-badge";

export type IntakeDraft = {
  id: string;
  submittedAtLabel: string;
  promptExcerpt: string;
  pickupLocation: string;
  destination: string;
  status: { tone: StatusTone; label: string };
};

export const intakeDrafts: IntakeDraft[] = [
  {
    id: "OP-1042",
    submittedAtLabel: "2026-08-29 09:14",
    promptExcerpt:
      "Necesito mover un contenedor de 40 pies desde el puerto de Cartagena hasta la bodega en Barranquilla antes del viernes, presupuesto máximo de 950 USD.",
    pickupLocation: "Puerto de Cartagena",
    destination: "Barranquilla, bodega central",
    status: { tone: "pending", label: "PENDING APPROVAL" },
  },
  {
    id: "OP-1041",
    submittedAtLabel: "2026-08-29 08:52",
    promptExcerpt:
      "Drayage move for one 20ft reefer container, Cartagena to Soledad cold storage, pickup window Wed-Thu, ceiling 700 USD, temperature-controlled required.",
    pickupLocation: "Puerto de Cartagena",
    destination: "Soledad cold storage",
    status: { tone: "success", label: "APPROVED" },
  },
  {
    id: "OP-1039",
    submittedAtLabel: "2026-08-28 17:03",
    promptExcerpt:
      "Contenedor de 40 pies, terminal SPRC, entrega en zona franca de Cartagena, autorización hasta 600 USD, condiciones estándar.",
    pickupLocation: "Terminal SPRC",
    destination: "Zona franca de Cartagena",
    status: { tone: "neutral", label: "DRAFT" },
  },
];

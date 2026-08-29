import type { LucideIcon } from "lucide-react";
import {
  ClipboardList,
  FileText,
  Flag,
  GitCompare,
  Radio,
  ScrollText,
  ShieldAlert,
  Ship,
} from "lucide-react";

import type { StatusTone } from "@/components/control-tower/status-badge";

export type OverviewMetric = {
  label: string;
  value: string;
  status: { tone: StatusTone; label: string };
};

export type OverviewSection = {
  href: string;
  icon: LucideIcon;
  title: string;
  description: string;
};

export const overviewMetrics: OverviewMetric[] = [
  {
    label: "Operations in flight",
    value: "3",
    status: { tone: "info", label: "CANDIDATE" },
  },
  {
    label: "Mandates pending approval",
    value: "1",
    status: { tone: "pending", label: "PENDING" },
  },
  {
    label: "Active carrier sessions",
    value: "2",
    status: { tone: "success", label: "ACTIVE" },
  },
  {
    label: "Open escalations",
    value: "1",
    status: { tone: "danger", label: "ESCALATED" },
  },
];

export const overviewSections: OverviewSection[] = [
  {
    href: "/intake",
    icon: FileText,
    title: "Intake",
    description: "Canonical drayage prompts waiting to become a draft.",
  },
  {
    href: "/mandate",
    icon: ClipboardList,
    title: "Mandate review",
    description: "Immutable mandate versions and their approval state.",
  },
  {
    href: "/sessions",
    icon: Ship,
    title: "Carrier sessions",
    description: "Live and completed negotiation sessions per carrier.",
  },
  {
    href: "/comparison",
    icon: GitCompare,
    title: "Comparison",
    description: "Side-by-side quotes and the current active winner.",
  },
  {
    href: "/evidence",
    icon: Radio,
    title: "Evidence",
    description: "Recorded turns, recaps, and briefs for each commitment.",
  },
  {
    href: "/recovery",
    icon: Flag,
    title: "Recovery",
    description: "Inbound renegotiation and mandate-replacement outcomes.",
  },
  {
    href: "/escalation",
    icon: ShieldAlert,
    title: "Escalation",
    description: "Operations that stopped for a human decision.",
  },
  {
    href: "/audit",
    icon: ScrollText,
    title: "Audit trail",
    description: "The append-only, correlated history of every operation.",
  },
];

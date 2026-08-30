import {
  CheckCircle2,
  CircleAlert,
  CircleDashed,
  Clock,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import type { ComponentType } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type StatusTone =
  "neutral" | "info" | "pending" | "success" | "warning" | "danger";

const TONE_CONFIG: Record<
  StatusTone,
  { icon: ComponentType<{ className?: string }>; className: string }
> = {
  neutral: {
    icon: CircleDashed,
    className: "bg-muted text-muted-foreground",
  },
  info: {
    icon: Sparkles,
    className: "bg-accent text-accent-foreground",
  },
  pending: {
    icon: Clock,
    className: "bg-secondary text-secondary-foreground",
  },
  success: {
    icon: CheckCircle2,
    className: "border-success/40 bg-transparent text-success",
  },
  warning: {
    icon: CircleAlert,
    className: "border-destructive/30 bg-transparent text-destructive",
  },
  danger: {
    icon: ShieldAlert,
    className: "border-destructive/40 bg-transparent text-destructive",
  },
};

type StatusBadgeProps = {
  tone: StatusTone;
  label: string;
  className?: string;
};

/**
 * Icon + text + color together carry status meaning so it never rests on
 * color alone (e.g. `SIMULATED` vs `CANDIDATE` vs an escalation state).
 */
export function StatusBadge({ tone, label, className }: StatusBadgeProps) {
  const { icon: Icon, className: toneClassName } = TONE_CONFIG[tone];

  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 border-transparent font-medium",
        toneClassName,
        className,
      )}
    >
      <Icon aria-hidden="true" data-icon="inline-start" className="size-3" />
      {label}
    </Badge>
  );
}

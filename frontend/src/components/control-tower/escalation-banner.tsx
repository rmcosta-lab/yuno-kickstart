import { ShieldAlert } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  StatusBadge,
  type StatusTone,
} from "@/components/control-tower/status-badge";

export type EscalationBannerProps = {
  reason: string;
  operationLabel: string;
  status: { tone: StatusTone; label: string };
  raisedAtLabel: string;
  description: string;
};

export function EscalationBanner({
  reason,
  operationLabel,
  status,
  raisedAtLabel,
  description,
}: EscalationBannerProps) {
  return (
    <Alert variant="destructive">
      <ShieldAlert aria-hidden="true" />
      <AlertTitle className="flex flex-wrap items-center gap-2">
        <span>{reason}</span>
        <StatusBadge tone={status.tone} label={status.label} />
      </AlertTitle>
      <AlertDescription>
        <p>{description}</p>
        <p className="mt-2 font-mono text-xs">
          {operationLabel} &middot; raised {raisedAtLabel}
        </p>
      </AlertDescription>
    </Alert>
  );
}

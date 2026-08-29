import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  StatusBadge,
  type StatusTone,
} from "@/components/control-tower/status-badge";

export type SessionCardProps = {
  carrierName: string;
  channel: string;
  status: { tone: StatusTone; label: string };
  summary: string;
  updatedAtLabel: string;
};

export function SessionCard({
  carrierName,
  channel,
  status,
  summary,
  updatedAtLabel,
}: SessionCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span className="truncate">{carrierName}</span>
          <StatusBadge tone={status.tone} label={status.label} />
        </CardTitle>
        <CardDescription>{channel}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-sm text-muted-foreground">{summary}</p>
        <p className="font-mono text-xs text-muted-foreground">
          {updatedAtLabel}
        </p>
      </CardContent>
    </Card>
  );
}

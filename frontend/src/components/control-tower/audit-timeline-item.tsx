import { cn } from "@/lib/utils";

export type AuditTimelineItemProps = {
  timestampLabel: string;
  actor: string;
  action: string;
  correlationId: string;
  isLast?: boolean;
};

export function AuditTimelineItem({
  timestampLabel,
  actor,
  action,
  correlationId,
  isLast = false,
}: AuditTimelineItemProps) {
  return (
    <li className="flex gap-4">
      <div className="flex flex-col items-center">
        <span
          aria-hidden="true"
          className="mt-1.5 size-2.5 shrink-0 rounded-full border-2 border-primary bg-background"
        />
        {!isLast ? (
          <span aria-hidden="true" className={cn("w-px flex-1 bg-border")} />
        ) : null}
      </div>
      <div className="min-w-0 flex-1 pb-6">
        <p className="font-mono text-xs text-muted-foreground">
          {timestampLabel}
        </p>
        <p className="mt-1 text-sm text-foreground">
          <span className="font-medium">{actor}</span> {action}
        </p>
        <p className="mt-1 truncate font-mono text-xs text-muted-foreground">
          {correlationId}
        </p>
      </div>
    </li>
  );
}

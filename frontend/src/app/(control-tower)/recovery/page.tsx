import { Flag } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { PageHeader } from "@/components/control-tower/page-header";
import { ScreenStateDemo } from "@/components/control-tower/screen-state-demo";
import { StatusBadge } from "@/components/control-tower/status-badge";
import { recoveryAttempts } from "./fixtures";

function RecoveryPopulated() {
  return (
    <ul className="space-y-4">
      {recoveryAttempts.map((attempt) => (
        <li key={attempt.id}>
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center justify-between gap-2">
                <span>{attempt.kind}</span>
                <StatusBadge
                  tone={attempt.status.tone}
                  label={attempt.status.label}
                />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-pretty text-muted-foreground">
                {attempt.description}
              </p>
              <p className="font-mono text-xs text-muted-foreground">
                {attempt.id} &middot; {attempt.timestampLabel}
              </p>
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  );
}

export default function RecoveryPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Recovery"
        description="Inbound renegotiation and mandate-replacement outcomes. A mandate-safe change transitions the winner atomically; an out-of-mandate change escalates."
      />
      <ScreenStateDemo
        loading={<LoadingState label="Loading recovery attempts" rows={2} />}
        empty={
          <EmptyState
            icon={Flag}
            title="No recovery attempts"
            description="Recovery attempts appear after an active commitment receives an inbound renegotiation or a coordinator replaces its mandate."
          />
        }
        error={
          <ErrorState
            title="Recovery unavailable"
            description="Recovery history could not be retrieved. This is a synthetic placeholder for a future backend failure."
          />
        }
        populated={<RecoveryPopulated />}
      />
    </div>
  );
}

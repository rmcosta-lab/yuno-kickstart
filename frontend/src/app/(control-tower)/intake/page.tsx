import { Inbox } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { PageHeader } from "@/components/control-tower/page-header";
import { ScreenStateDemo } from "@/components/control-tower/screen-state-demo";
import { StatusBadge } from "@/components/control-tower/status-badge";
import { intakeDrafts } from "./fixtures";

function IntakePopulated() {
  return (
    <ul className="space-y-4">
      {intakeDrafts.map((draft) => (
        <li key={draft.id}>
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-sm">{draft.id}</span>
                <StatusBadge
                  tone={draft.status.tone}
                  label={draft.status.label}
                />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-pretty text-foreground">
                &ldquo;{draft.promptExcerpt}&rdquo;
              </p>
              <dl className="grid grid-cols-1 gap-2 text-sm text-muted-foreground sm:grid-cols-3">
                <div>
                  <dt className="font-medium text-foreground">Pickup</dt>
                  <dd>{draft.pickupLocation}</dd>
                </div>
                <div>
                  <dt className="font-medium text-foreground">Destination</dt>
                  <dd>{draft.destination}</dd>
                </div>
                <div>
                  <dt className="font-medium text-foreground">Submitted</dt>
                  <dd className="font-mono text-xs">
                    {draft.submittedAtLabel}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  );
}

export default function IntakePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Intake"
        description="Canonical drayage prompts submitted by a coordinator, retained verbatim alongside the policy version used to draft them."
      />
      <ScreenStateDemo
        loading={<LoadingState label="Loading intake drafts" />}
        empty={
          <EmptyState
            icon={Inbox}
            title="No intake drafts"
            description="Submit a canonical drayage prompt to start a new operation. This phase does not implement submission — it is presentation only."
          />
        }
        error={
          <ErrorState
            title="Intake unavailable"
            description="The extraction policy could not process the submitted prompt. This is a synthetic placeholder for a future provider failure."
          />
        }
        populated={<IntakePopulated />}
      />
    </div>
  );
}

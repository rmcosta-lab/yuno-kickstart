import { Radio } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { PageHeader } from "@/components/control-tower/page-header";
import { ScreenStateDemo } from "@/components/control-tower/screen-state-demo";
import { StatusBadge } from "@/components/control-tower/status-badge";
import { evidenceRecords } from "./fixtures";

function EvidencePopulated() {
  return (
    <ul className="space-y-4">
      {evidenceRecords.map((record) => (
        <li key={record.sessionId}>
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center justify-between gap-2">
                <span>{record.carrierName}</span>
                <StatusBadge
                  tone={record.status.tone}
                  label={record.status.label}
                />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-pretty text-foreground">
                {record.recapSummary}
              </p>
              <Separator />
              <dl className="grid grid-cols-1 gap-2 font-mono text-xs text-muted-foreground sm:grid-cols-3">
                <div>
                  <dt className="text-foreground">Session</dt>
                  <dd>{record.sessionId}</dd>
                </div>
                <div>
                  <dt className="text-foreground">Item</dt>
                  <dd>{record.itemId}</dd>
                </div>
                <div>
                  <dt className="text-foreground">Event</dt>
                  <dd>{record.eventId}</dd>
                </div>
              </dl>
              <p className="font-mono text-xs text-muted-foreground">
                {record.audioStartLabel}
              </p>
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  );
}

export default function EvidencePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Evidence"
        description="Provider-neutral call sessions, recording references, and recaps for each commitment. Every recap here is labeled SIMULATED."
      />
      <ScreenStateDemo
        loading={<LoadingState label="Loading evidence records" rows={2} />}
        empty={
          <EmptyState
            icon={Radio}
            title="No evidence recorded"
            description="Evidence appears once a carrier session reaches an active commitment. This phase records no real audio."
          />
        }
        error={
          <ErrorState
            title="Evidence unavailable"
            description="Recording references could not be retrieved. This is a synthetic placeholder for a future storage failure."
          />
        }
        populated={<EvidencePopulated />}
      />
    </div>
  );
}

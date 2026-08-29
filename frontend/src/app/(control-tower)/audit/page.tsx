import { ScrollText } from "lucide-react";

import { AuditTimelineItem } from "@/components/control-tower/audit-timeline-item";
import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { PageHeader } from "@/components/control-tower/page-header";
import { ScreenStateDemo } from "@/components/control-tower/screen-state-demo";
import { auditEvents } from "./fixtures";

function AuditPopulated() {
  return (
    <ol className="max-w-2xl">
      {auditEvents.map((event, index) => (
        <AuditTimelineItem
          key={`${event.correlationId}-${event.timestampLabel}`}
          {...event}
          isLast={index === auditEvents.length - 1}
        />
      ))}
    </ol>
  );
}

export default function AuditPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Audit trail"
        description="The append-only, correlated history of every operation: intake, approval, negotiation, commitment, recovery, and escalation."
      />
      <ScreenStateDemo
        loading={<LoadingState label="Loading audit trail" rows={4} />}
        empty={
          <EmptyState
            icon={ScrollText}
            title="No audit events yet"
            description="Audit events accumulate as soon as an operation is created. This phase has no persistence, so this fixture starts empty on demand."
          />
        }
        error={
          <ErrorState
            title="Audit trail unavailable"
            description="Audit events could not be retrieved. This is a synthetic placeholder for a future backend failure."
          />
        }
        populated={<AuditPopulated />}
      />
    </div>
  );
}

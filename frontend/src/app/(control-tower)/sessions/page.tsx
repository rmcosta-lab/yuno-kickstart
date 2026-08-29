import { Ship } from "lucide-react";

import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { PageHeader } from "@/components/control-tower/page-header";
import { ScreenStateDemo } from "@/components/control-tower/screen-state-demo";
import { SessionCard } from "@/components/control-tower/session-card";
import { carrierSessions } from "./fixtures";

function SessionsPopulated() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {carrierSessions.map((session) => (
        <SessionCard key={session.carrierName} {...session} />
      ))}
    </div>
  );
}

export default function SessionsPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Carrier sessions"
        description="One to three synthetic negotiation sessions selected by the fixed ranking. The model never chooses carriers or validates a quote."
      />
      <ScreenStateDemo
        loading={<LoadingState label="Loading carrier sessions" rows={2} />}
        empty={
          <EmptyState
            icon={Ship}
            title="No eligible carriers"
            description="Route and availability filtering found no eligible carrier for this operation, so the operation escalates before contact."
          />
        }
        error={
          <ErrorState
            title="Sessions unavailable"
            description="Carrier session state could not be retrieved. This is a synthetic placeholder for a future provider failure."
          />
        }
        populated={<SessionsPopulated />}
      />
    </div>
  );
}

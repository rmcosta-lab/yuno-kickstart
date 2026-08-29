import { ShieldAlert } from "lucide-react";

import { EmptyState } from "@/components/control-tower/empty-state";
import { EscalationBanner } from "@/components/control-tower/escalation-banner";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { PageHeader } from "@/components/control-tower/page-header";
import { ScreenStateDemo } from "@/components/control-tower/screen-state-demo";
import { escalations } from "./fixtures";

function EscalationPopulated() {
  return (
    <div className="space-y-4">
      {escalations.map((escalation) => (
        <EscalationBanner key={escalation.operationLabel} {...escalation} />
      ))}
    </div>
  );
}

export default function EscalationPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Escalation"
        description="Operations that stopped for a human decision, either because no carrier was eligible or every quote fell outside the mandate."
      />
      <ScreenStateDemo
        loading={<LoadingState label="Loading escalations" rows={2} />}
        empty={
          <EmptyState
            icon={ShieldAlert}
            title="No open escalations"
            description="Every operation is either negotiating within its mandate or has reached an active commitment."
          />
        }
        error={
          <ErrorState
            title="Escalation view unavailable"
            description="Escalation state could not be retrieved. This is a synthetic placeholder for a future backend failure."
          />
        }
        populated={<EscalationPopulated />}
      />
    </div>
  );
}

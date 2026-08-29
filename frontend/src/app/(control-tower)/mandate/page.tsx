import { PageHeader } from "@/components/control-tower/page-header";
import { MandateApproval } from "./mandate-approval";

export default function MandatePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Mandate review"
        description="Immutable mandate versions derived from an approved intake draft. Approval, not extraction, creates operational authority."
      />
      <MandateApproval />
    </div>
  );
}

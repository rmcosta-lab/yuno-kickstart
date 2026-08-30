import { PageHeader } from "@/components/control-tower/page-header";
import { NegotiationExperience } from "@/features/negotiation";

export default function ComparisonPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Quote comparison"
        description="Compare server-recorded synthetic quotes, use only the audit-selected option, and inspect the evidence-backed active winner returned by the backend."
      />
      <NegotiationExperience
        surface="comparison"
        initialScenario="active-market"
      />
    </div>
  );
}

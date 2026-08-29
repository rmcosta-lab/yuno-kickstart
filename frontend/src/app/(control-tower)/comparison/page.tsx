import { PageHeader } from "@/components/control-tower/page-header";
import { NegotiationExperience } from "@/features/negotiation";

export default function ComparisonPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Quote comparison"
        description="Compare every recorded synthetic quote without hiding rejected or earlier terms. A winner appears only from the server-declared active commitment."
      />
      <NegotiationExperience
        surface="comparison"
        initialScenario="active-market"
      />
    </div>
  );
}

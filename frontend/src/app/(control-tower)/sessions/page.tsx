import { PageHeader } from "@/components/control-tower/page-header";
import { NegotiationExperience } from "@/features/negotiation";

export default function SessionsPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Contact the selected carrier"
        description="Review Volta's best route match, confirm participant authorization, and start the demo call."
      />
      <NegotiationExperience
        surface="sessions"
        initialScenario="active-market"
      />
    </div>
  );
}

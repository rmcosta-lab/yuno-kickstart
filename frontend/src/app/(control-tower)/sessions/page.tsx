import { PageHeader } from "@/components/control-tower/page-header";
import { NegotiationExperience } from "@/features/negotiation";

export default function SessionsPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Carrier sessions"
        description="Inspect one to three synthetic text sessions, their server-owned ranking evidence, quote changes, and mandate outcomes. No carrier is contacted."
      />
      <NegotiationExperience
        surface="sessions"
        initialScenario="active-market"
      />
    </div>
  );
}

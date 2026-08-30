import { PageHeader } from "@/components/control-tower/page-header";
import { RecoveryExperience } from "@/features/recovery/recovery-experience";

export default function EscalationPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Escalation"
        description="Operations that stopped for a human decision, either because no carrier was eligible or every quote fell outside the mandate."
      />
      <RecoveryExperience surface="escalation" />
    </div>
  );
}

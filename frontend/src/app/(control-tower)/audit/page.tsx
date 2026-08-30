import { PageHeader } from "@/components/control-tower/page-header";
import { RecoveryExperience } from "@/features/recovery/recovery-experience";

export default function AuditPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Audit trail"
        description="The append-only history of operation events and artifacts. Correlation appears only where the server supplies it directly; timestamp ordering never invents causality."
      />
      <RecoveryExperience surface="audit" />
    </div>
  );
}

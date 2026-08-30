import { PageHeader } from "@/components/control-tower/page-header";
import { RecoveryExperience } from "@/features/recovery/recovery-experience";

export default function RecoveryPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Recovery"
        description="Inbound renegotiation and mandate-replacement outcomes. A mandate-safe change transitions the winner atomically; an out-of-mandate change escalates."
      />
      <RecoveryExperience surface="recovery" />
    </div>
  );
}

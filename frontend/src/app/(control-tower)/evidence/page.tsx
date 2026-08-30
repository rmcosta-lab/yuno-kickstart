import { PageHeader } from "@/components/control-tower/page-header";
import { RecoveryExperience } from "@/features/recovery/recovery-experience";

export default function EvidencePage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Evidence"
        description="Authenticated evidence playback, provider-neutral metadata, written recaps, and call briefs for each commitment. Lifecycle and disposition remain separate server-owned facts."
      />
      <RecoveryExperience surface="evidence" />
    </div>
  );
}

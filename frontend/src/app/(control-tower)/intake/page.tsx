import { PageHeader } from "@/components/control-tower/page-header";
import { IntakeForm } from "./intake-form";

export default function IntakePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Intake"
        description="Canonical drayage prompts submitted by a coordinator, retained verbatim alongside the policy version used to draft them."
      />
      <IntakeForm />
    </div>
  );
}

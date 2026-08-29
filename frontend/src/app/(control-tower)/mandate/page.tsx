import { ClipboardList } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { PageHeader } from "@/components/control-tower/page-header";
import { ScreenStateDemo } from "@/components/control-tower/screen-state-demo";
import { StatusBadge } from "@/components/control-tower/status-badge";
import { mandateVersions } from "./fixtures";

function MandatePopulated() {
  return (
    <ul className="space-y-4">
      {mandateVersions.map((mandate) => (
        <li key={`${mandate.operationId}-v${mandate.version}`}>
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-sm">
                  {mandate.operationId} &middot; v{mandate.version}
                </span>
                <StatusBadge
                  tone={mandate.status.tone}
                  label={mandate.status.label}
                />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
                <div>
                  <dt className="font-medium text-foreground">Price limit</dt>
                  <dd className="text-muted-foreground">
                    {mandate.priceLimit}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-foreground">Pickup window</dt>
                  <dd className="text-muted-foreground">
                    {mandate.pickupWindow}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-foreground">Authority</dt>
                  <dd className="text-muted-foreground">{mandate.authority}</dd>
                </div>
              </dl>
              <Separator />
              <div>
                <p className="text-sm font-medium text-foreground">
                  Conditions
                </p>
                <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                  {mandate.conditions.map((condition) => (
                    <li key={condition} className="flex gap-1.5">
                      <span aria-hidden="true">&bull;</span>
                      <span>{condition}</span>
                    </li>
                  ))}
                </ul>
              </div>
              {mandate.approvedByLabel ? (
                <p className="font-mono text-xs text-muted-foreground">
                  {mandate.approvedByLabel}
                </p>
              ) : null}
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  );
}

export default function MandatePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Mandate review"
        description="Immutable mandate versions derived from an approved intake draft. Approval, not extraction, creates operational authority."
      />
      <ScreenStateDemo
        loading={<LoadingState label="Loading mandate versions" />}
        empty={
          <EmptyState
            icon={ClipboardList}
            title="No mandates yet"
            description="A mandate version appears here once a coordinator approves an intake draft. This phase does not implement approval."
          />
        }
        error={
          <ErrorState
            title="Mandate review unavailable"
            description="The mandate service could not be reached. This is a synthetic placeholder for a future backend failure."
          />
        }
        populated={<MandatePopulated />}
      />
    </div>
  );
}

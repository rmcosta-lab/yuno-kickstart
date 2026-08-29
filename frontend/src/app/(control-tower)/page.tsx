import { Inbox } from "lucide-react";
import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { PageHeader } from "@/components/control-tower/page-header";
import { ScreenStateDemo } from "@/components/control-tower/screen-state-demo";
import { StatusBadge } from "@/components/control-tower/status-badge";
import { overviewMetrics, overviewSections } from "./fixtures";

function OverviewPopulated() {
  return (
    <div className="space-y-8">
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {overviewMetrics.map((metric) => (
          <div
            key={metric.label}
            className="rounded-xl border border-border bg-card p-4"
          >
            <dt className="text-sm text-muted-foreground">{metric.label}</dt>
            <dd className="mt-2 flex items-center justify-between gap-2">
              <span className="font-display text-3xl font-semibold text-foreground">
                {metric.value}
              </span>
              <StatusBadge
                tone={metric.status.tone}
                label={metric.status.label}
              />
            </dd>
          </div>
        ))}
      </dl>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {overviewSections.map((section) => (
          <Link key={section.href} href={section.href} className="group/link">
            <Card className="h-full transition-colors group-hover/link:ring-1 group-hover/link:ring-primary group-focus-visible/link:ring-1 group-focus-visible/link:ring-primary">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <section.icon
                    aria-hidden="true"
                    className="size-4 text-primary"
                  />
                  {section.title}
                </CardTitle>
                <CardDescription>{section.description}</CardDescription>
              </CardHeader>
              <CardContent />
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function OverviewPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Overview"
        description="A coordinator's landing screen for the complete drayage negotiation journey, from intake through audit. Every value on this page is a local synthetic fixture."
      />
      <ScreenStateDemo
        loading={<LoadingState label="Loading overview metrics" rows={4} />}
        empty={
          <EmptyState
            icon={Inbox}
            title="No operations yet"
            description="Once a coordinator submits the first drayage prompt, this overview will summarize operations, mandates, sessions, and escalations."
          />
        }
        error={
          <ErrorState
            title="Overview unavailable"
            description="The control tower could not summarize current operations. This is a synthetic placeholder for a future provider failure."
          />
        }
        populated={<OverviewPopulated />}
      />
    </div>
  );
}

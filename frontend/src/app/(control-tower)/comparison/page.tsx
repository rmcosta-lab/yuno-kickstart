import { GitCompare } from "lucide-react";

import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { PageHeader } from "@/components/control-tower/page-header";
import { QuoteComparisonCard } from "@/components/control-tower/quote-comparison-card";
import { ScreenStateDemo } from "@/components/control-tower/screen-state-demo";
import { quoteComparisons } from "./fixtures";

function ComparisonPopulated() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {quoteComparisons.map((quote) => (
        <QuoteComparisonCard key={quote.carrierName} {...quote} />
      ))}
    </div>
  );
}

export default function ComparisonPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Volta control tower"
        title="Quote comparison"
        description="Every recorded quote for the current operation, with exactly one active winner and every superseded quote kept for history."
      />
      <ScreenStateDemo
        loading={<LoadingState label="Loading quote comparison" rows={2} />}
        empty={
          <EmptyState
            icon={GitCompare}
            title="No quotes recorded"
            description="Quotes appear here once at least one carrier session returns a response for this operation."
          />
        }
        error={
          <ErrorState
            title="Comparison unavailable"
            description="Quote history could not be retrieved. This is a synthetic placeholder for a future backend failure."
          />
        }
        populated={<ComparisonPopulated />}
      />
    </div>
  );
}

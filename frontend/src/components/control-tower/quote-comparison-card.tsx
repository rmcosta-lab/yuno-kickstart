import { Trophy } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  StatusBadge,
  type StatusTone,
} from "@/components/control-tower/status-badge";
import { cn } from "@/lib/utils";

export type QuoteComparisonCardProps = {
  carrierName: string;
  price: string;
  pickupWindow: string;
  conditions: string[];
  isWinner: boolean;
  status: { tone: StatusTone; label: string };
};

export function QuoteComparisonCard({
  carrierName,
  price,
  pickupWindow,
  conditions,
  isWinner,
  status,
}: QuoteComparisonCardProps) {
  return (
    <Card
      className={cn(isWinner && "ring-2 ring-primary")}
      aria-current={isWinner ? "true" : undefined}
    >
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span className="truncate">{carrierName}</span>
          <StatusBadge tone={status.tone} label={status.label} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {isWinner ? (
          <p className="flex items-center gap-1.5 text-sm font-medium text-primary">
            <Trophy aria-hidden="true" className="size-4" />
            Active winner
          </p>
        ) : null}
        <p className="font-display text-2xl font-semibold text-foreground">
          {price}
        </p>
        <dl className="text-sm text-muted-foreground">
          <div className="flex items-baseline gap-1.5">
            <dt className="font-medium text-foreground">Pickup window:</dt>
            <dd>{pickupWindow}</dd>
          </div>
        </dl>
        <ul className="space-y-1 text-sm text-muted-foreground">
          {conditions.map((condition) => (
            <li key={condition} className="flex gap-1.5">
              <span aria-hidden="true">&bull;</span>
              <span>{condition}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

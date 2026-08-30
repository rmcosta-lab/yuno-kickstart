import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Clock3,
  History,
  MessageSquareText,
  ShieldAlert,
} from "lucide-react";

import { StatusBadge } from "@/components/control-tower/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { CarrierSessionResponse } from "@/lib/api/generated/models/carrierSessionResponse";
import type { EscalationResponse } from "@/lib/api/generated/models/escalationResponse";
import type { OperationResponse } from "@/lib/api/generated/models/operationResponse";
import type { QuoteResponse } from "@/lib/api/generated/models/quoteResponse";

const MONEY_FORMATTER = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  minimumFractionDigits: 2,
});

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "America/Mexico_City",
});

function formatMoney(amountMinor: number) {
  return MONEY_FORMATTER.format(amountMinor / 100);
}

function formatDateTime(value: string) {
  return DATE_TIME_FORMATTER.format(new Date(value));
}

function formatPickupWindow(start: string, end: string) {
  return DATE_TIME_FORMATTER.formatRange(new Date(start), new Date(end));
}

function humanize(value: string) {
  return value.toLowerCase().replaceAll("_", " ");
}

function sessionStatusTone(state: CarrierSessionResponse["state"]) {
  switch (state) {
    case "ACTIVE":
      return "info" as const;
    case "COMPLETED":
      return "success" as const;
    case "FAILED":
      return "danger" as const;
    case "SELECTED":
      return "pending" as const;
  }
}

function quoteStatusTone(eligibility: QuoteResponse["eligibility"]) {
  return eligibility === "ELIGIBLE"
    ? ("success" as const)
    : ("danger" as const);
}

function OperationStrip({ operation }: { operation: OperationResponse }) {
  return (
    <section
      aria-label="Operation context"
      className="grid gap-4 border-y border-border py-4 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center"
    >
      <div className="min-w-0">
        <p className="font-mono text-xs text-muted-foreground">
          {operation.operation_id} · version {operation.operation_version}
        </p>
        <p className="mt-1 text-sm font-medium text-foreground">
          {operation.cargo_label}
        </p>
      </div>
      <p className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
        <span className="min-w-0 wrap-break-word">
          {operation.route.origin}
        </span>
        <ArrowRight aria-hidden="true" className="shrink-0" />
        <span className="min-w-0 wrap-break-word">
          {operation.route.destination}
        </span>
      </p>
      <StatusBadge tone="info" label={operation.status} />
    </section>
  );
}

function PreContactEscalation({
  escalation,
}: {
  escalation: EscalationResponse;
}) {
  return (
    <Alert variant="destructive" role="status">
      <ShieldAlert aria-hidden="true" />
      <AlertTitle>No carrier contacted · pre-contact escalation</AlertTitle>
      <AlertDescription className="flex flex-col gap-3">
        <p>{escalation.conflict}</p>
        {escalation.attempted_alternatives?.length ? (
          <div>
            <p className="font-medium text-foreground">Checks completed</p>
            <ul className="mt-1 flex flex-col gap-1">
              {escalation.attempted_alternatives.map((alternative) => (
                <li key={alternative}>• {alternative}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <p>
          <span className="font-medium text-foreground">Next action:</span>{" "}
          {escalation.recommended_action}
        </p>
        <p className="font-mono text-xs">
          {escalation.resolution_state} · raised{" "}
          {formatDateTime(escalation.created_at)}
        </p>
      </AlertDescription>
    </Alert>
  );
}

function QuoteRecord({
  quote,
  recordLabel,
}: {
  quote: QuoteResponse;
  recordLabel: string;
}) {
  return (
    <article className="border-l-2 border-border pl-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-medium text-foreground">
            <History aria-hidden="true" />
            {recordLabel}
          </p>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {formatDateTime(quote.created_at)} · mandate v
            {quote.mandate_version}
          </p>
        </div>
        <StatusBadge
          tone={quoteStatusTone(quote.eligibility)}
          label={quote.eligibility}
        />
      </div>
      <p className="mt-3 font-display text-xl font-semibold text-foreground tabular-nums">
        {formatMoney(quote.terms.amount_minor)} {quote.terms.currency}
      </p>
      <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-medium text-foreground">Pickup window</dt>
          <dd className="mt-1 text-muted-foreground">
            {formatPickupWindow(
              quote.terms.pickup_window.start_date,
              quote.terms.pickup_window.end_date,
            )}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-foreground">Valid until</dt>
          <dd className="mt-1 text-muted-foreground">
            {formatDateTime(quote.valid_until)}
          </dd>
        </div>
      </dl>
      <div className="mt-3">
        <p className="text-sm font-medium text-foreground">Conditions</p>
        {quote.terms.conditions?.length ? (
          <ul className="mt-1 flex flex-col gap-1 text-sm text-muted-foreground">
            {quote.terms.conditions.map((condition) => (
              <li key={condition} className="wrap-break-word">
                • {condition}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-muted-foreground">
            No additional conditions recorded.
          </p>
        )}
      </div>
      {quote.eligibility === "REJECTED" ? (
        <div className="mt-4 rounded-md border border-destructive/30 bg-destructive/5 p-3">
          <p className="flex items-center gap-2 text-sm font-medium text-destructive">
            <ShieldAlert aria-hidden="true" />
            Mandate violations
          </p>
          <ul className="mt-2 flex flex-col gap-1 text-sm text-foreground">
            {quote.rejection_reasons?.map((reason) => (
              <li key={reason} className="wrap-break-word">
                • {reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
}

function SessionPanel({
  session,
  quotes,
}: {
  session: CarrierSessionResponse;
  quotes: QuoteResponse[];
}) {
  const chronologicalQuotes = quotes.toSorted((left, right) =>
    left.created_at.localeCompare(right.created_at),
  );

  return (
    <li>
      <Card className="overflow-hidden">
        <CardHeader className="border-b border-border bg-muted/35">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="font-mono text-xs font-medium text-primary">
                Rank {session.carrier.deterministic_rank} ·{" "}
                {humanize(session.channel)}
              </p>
              <CardTitle className="mt-1 wrap-break-word">
                {session.carrier.display_name}
              </CardTitle>
              <CardDescription className="mt-1">
                {humanize(session.direction)} · {session.call_id}
              </CardDescription>
            </div>
            <StatusBadge
              tone={sessionStatusTone(session.state)}
              label={session.state}
            />
          </div>
        </CardHeader>
        <CardContent className="grid gap-6 pt-5 lg:grid-cols-[minmax(13rem,0.7fr)_minmax(0,1.6fr)]">
          <div className="flex flex-col gap-5">
            <div>
              <p className="text-sm font-medium text-foreground">
                Selection evidence
              </p>
              <ul className="mt-2 flex flex-col gap-2 text-sm text-muted-foreground">
                {session.carrier.ranking_evidence?.map((evidence) => (
                  <li key={evidence} className="flex gap-2">
                    <CheckCircle2
                      aria-hidden="true"
                      className="mt-0.5 shrink-0 text-success"
                    />
                    <span>{evidence}</span>
                  </li>
                ))}
              </ul>
            </div>
            <Separator />
            <dl className="grid gap-3 text-sm">
              <div>
                <dt className="font-medium text-foreground">Started</dt>
                <dd className="mt-1 font-mono text-xs text-muted-foreground">
                  {session.started_at
                    ? formatDateTime(session.started_at)
                    : "Not contacted"}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-foreground">Ended</dt>
                <dd className="mt-1 font-mono text-xs text-muted-foreground">
                  {session.ended_at ? formatDateTime(session.ended_at) : "—"}
                </dd>
              </div>
            </dl>
          </div>
          <div className="min-w-0">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-heading text-sm font-semibold text-foreground">
                Quote history
              </h3>
              <span className="font-mono text-xs text-muted-foreground">
                {chronologicalQuotes.length} record
                {chronologicalQuotes.length === 1 ? "" : "s"}
              </span>
            </div>
            {chronologicalQuotes.length ? (
              <div className="mt-4 flex flex-col gap-6">
                {chronologicalQuotes.map((quote, index) => (
                  <QuoteRecord
                    key={quote.quote_id}
                    quote={quote}
                    recordLabel={
                      index === chronologicalQuotes.length - 1
                        ? "Latest recorded terms"
                        : `Earlier record ${index + 1}`
                    }
                  />
                ))}
              </div>
            ) : (
              <div className="mt-4 rounded-md border border-dashed border-border p-5">
                <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <MessageSquareText aria-hidden="true" />
                  No quote recorded
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Session state is {session.state.toLowerCase()}; no carrier
                  terms are fabricated in the browser.
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </li>
  );
}

export function SessionsView({ operation }: { operation: OperationResponse }) {
  const sessions = operation.sessions ?? [];
  const escalation = operation.open_escalation;

  return (
    <div className="flex flex-col gap-6">
      <OperationStrip operation={operation} />
      {escalation && sessions.length === 0 ? (
        <PreContactEscalation escalation={escalation} />
      ) : null}
      {sessions.length ? (
        <ol
          aria-label="Carrier workflow sessions"
          className="flex flex-col gap-5"
        >
          {sessions.map((session) => (
            <SessionPanel
              key={session.call_id}
              session={session}
              quotes={(operation.quotes ?? []).filter(
                (quote) => quote.call_id === session.call_id,
              )}
            />
          ))}
        </ol>
      ) : escalation ? null : (
        <Alert>
          <Clock3 aria-hidden="true" />
          <AlertTitle>No session selected</AlertTitle>
          <AlertDescription>
            This simulated operation contains no selected carrier session.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

function ComparisonPanel({
  quote,
  session,
  recordLabel,
}: {
  quote: QuoteResponse;
  session?: CarrierSessionResponse;
  recordLabel: string;
}) {
  return (
    <li>
      <Card className="h-full overflow-hidden">
        <CardHeader className="border-b border-border bg-muted/35">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle className="wrap-break-word">
                {session?.carrier.display_name ?? quote.carrier_id}
              </CardTitle>
              <CardDescription>
                {recordLabel} ·{" "}
                {session
                  ? `Rank ${session.carrier.deterministic_rank} · ${humanize(session.channel)}`
                  : quote.call_id}
              </CardDescription>
            </div>
            <StatusBadge
              tone={quoteStatusTone(quote.eligibility)}
              label={quote.eligibility}
            />
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-5 pt-5">
          <div>
            <p className="font-display text-2xl font-semibold text-foreground tabular-nums">
              {formatMoney(quote.terms.amount_minor)} {quote.terms.currency}
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              Recorded {formatDateTime(quote.created_at)} · mandate v
              {quote.mandate_version}
            </p>
          </div>
          <dl className="grid gap-4 text-sm">
            <div>
              <dt className="font-medium text-foreground">Pickup window</dt>
              <dd className="mt-1 wrap-break-word text-muted-foreground">
                {formatPickupWindow(
                  quote.terms.pickup_window.start_date,
                  quote.terms.pickup_window.end_date,
                )}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Valid until</dt>
              <dd className="mt-1 text-muted-foreground">
                {formatDateTime(quote.valid_until)}
              </dd>
            </div>
          </dl>
          <Separator />
          <div>
            <p className="text-sm font-medium text-foreground">Conditions</p>
            <ul className="mt-2 flex flex-col gap-1 text-sm text-muted-foreground">
              {quote.terms.conditions?.map((condition) => (
                <li key={condition} className="wrap-break-word">
                  • {condition}
                </li>
              ))}
            </ul>
          </div>
          {quote.eligibility === "REJECTED" ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
              <p className="flex items-center gap-2 text-sm font-medium text-destructive">
                <CircleAlert aria-hidden="true" />
                Rejected by mandate v{quote.mandate_version}
              </p>
              <ul className="mt-2 flex flex-col gap-1 text-sm text-foreground">
                {quote.rejection_reasons?.map((reason) => (
                  <li key={reason} className="wrap-break-word">
                    • {reason}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Eligible option returned by the server. No winner is inferred in
              this comparison checkpoint.
            </p>
          )}
        </CardContent>
      </Card>
    </li>
  );
}

export function ComparisonView({
  operation,
}: {
  operation: OperationResponse;
}) {
  const sessions = operation.sessions ?? [];
  const quotes = operation.quotes ?? [];
  const escalation = operation.open_escalation;
  const latestQuoteBySession = new Map<string, QuoteResponse>();

  for (const quote of quotes) {
    const current = latestQuoteBySession.get(quote.call_id);
    if (!current || current.created_at < quote.created_at) {
      latestQuoteBySession.set(quote.call_id, quote);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <OperationStrip operation={operation} />
      {escalation && sessions.length === 0 ? (
        <PreContactEscalation escalation={escalation} />
      ) : null}
      {quotes.length ? (
        <ul
          aria-label="Recorded quote comparison"
          className="grid items-stretch gap-5 lg:grid-cols-2 xl:grid-cols-3"
        >
          {quotes.map((quote) => (
            <ComparisonPanel
              key={quote.quote_id}
              quote={quote}
              session={sessions.find(
                (session) => session.call_id === quote.call_id,
              )}
              recordLabel={
                latestQuoteBySession.get(quote.call_id)?.quote_id ===
                quote.quote_id
                  ? "Latest recorded terms"
                  : "Earlier recorded terms"
              }
            />
          ))}
        </ul>
      ) : escalation ? null : (
        <Alert>
          <MessageSquareText aria-hidden="true" />
          <AlertTitle>No recorded quotes</AlertTitle>
          <AlertDescription>
            The selected carrier sessions have not returned terms. No winner is
            inferred from rank or an empty comparison.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

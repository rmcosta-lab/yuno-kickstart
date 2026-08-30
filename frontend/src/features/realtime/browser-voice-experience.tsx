"use client";

import { Headphones, Mic, RefreshCw, Send, Square } from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { StatusBadge } from "@/components/control-tower/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { createRealtimeClientSecret } from "@/lib/api/generated/api";
import type {
  AuditTimelineResponse,
  CommitmentEvidenceResponse,
  OperationResponse,
} from "@/lib/api/generated/models";

import {
  BrowserRealtimeError,
  connectBrowserRealtime,
  type BrowserRealtimeConnection,
  type BrowserRealtimeStatus,
} from "./browser-realtime";
import {
  createRealtimeToolDispatcher,
  type RealtimeOperationalContext,
} from "./tool-dispatcher";

type VoiceState =
  | { kind: "idle" }
  | { kind: "requesting_permission" }
  | { kind: "connecting" }
  | { kind: "connected" }
  | { kind: "reconciling" }
  | { kind: "reconnecting" }
  | { kind: "disconnected"; reason: "clean" | "unclean" }
  | { kind: "fallback" }
  | { kind: "error"; category: string };

type BrowserVoiceExperienceProps = Readonly<{
  operation: OperationResponse;
  audit?: AuditTimelineResponse;
  attachedEvidence: CommitmentEvidenceResponse | null;
  refreshAuthoritativeState: () => Promise<AuthoritativeVoiceState>;
}>;

export type AuthoritativeVoiceState = Readonly<{
  operation: OperationResponse;
  audit?: AuditTimelineResponse;
}>;

class CurrentVoiceContext {
  private context: RealtimeOperationalContext;
  private refresh: () => Promise<AuthoritativeVoiceState>;
  private attachedEvidence: CommitmentEvidenceResponse | null;

  constructor(
    context: RealtimeOperationalContext,
    refresh: () => Promise<AuthoritativeVoiceState>,
    attachedEvidence: CommitmentEvidenceResponse | null,
  ) {
    this.context = context;
    this.refresh = refresh;
    this.attachedEvidence = attachedEvidence;
  }

  getContext() {
    return this.context;
  }

  async refreshState() {
    const refreshed = await this.refresh();
    this.context = createOperationalContext(
      refreshed.operation,
      refreshed.audit,
      this.attachedEvidence,
    );
    return this.context;
  }

  update(
    context: RealtimeOperationalContext,
    refresh: () => Promise<AuthoritativeVoiceState>,
    attachedEvidence: CommitmentEvidenceResponse | null,
  ) {
    this.context = context;
    this.refresh = refresh;
    this.attachedEvidence = attachedEvidence;
  }
}

function createOperationalContext(
  operation: OperationResponse,
  audit: AuditTimelineResponse | undefined,
  attachedEvidence: CommitmentEvidenceResponse | null,
): RealtimeOperationalContext {
  const selected =
    audit?.quote_comparison.filter((quote) => quote.selected) ?? [];
  const selectedQuote = selected.length === 1 ? selected[0] : null;
  const matchingSession = selectedQuote
    ? operation.sessions?.find(
        (session) => session.call_id === selectedQuote.call_id,
      )
    : null;

  return Object.freeze({
    operationId: operation.operation_id,
    operationVersion: operation.operation_version,
    mandateVersion: operation.active_mandate.version,
    sessions: Object.freeze(
      (operation.sessions ?? []).map((session) =>
        Object.freeze({
          callId: session.call_id,
          carrierId: session.carrier.carrier_id,
        }),
      ),
    ),
    selectedQuote:
      selectedQuote && matchingSession
        ? Object.freeze({
            callId: selectedQuote.call_id,
            carrierId: matchingSession.carrier.carrier_id,
            quoteId: selectedQuote.quote_id,
          })
        : null,
    attachedEvidence:
      attachedEvidence && selectedQuote?.call_id === attachedEvidence.call_id
        ? Object.freeze({
            callId: attachedEvidence.call_id,
            evidenceId: attachedEvidence.evidence_id,
          })
        : null,
  });
}

function contextMessage(context: RealtimeOperationalContext): string {
  return JSON.stringify({
    context: "authoritative_current_operation",
    operation_id: context.operationId,
    operation_version: context.operationVersion,
    mandate_version: context.mandateVersion,
    sessions: context.sessions.map((session) => ({
      call_id: session.callId,
      carrier_id: session.carrierId,
    })),
    selected_quote: context.selectedQuote
      ? {
          call_id: context.selectedQuote.callId,
          carrier_id: context.selectedQuote.carrierId,
          quote_id: context.selectedQuote.quoteId,
        }
      : null,
    attached_evidence: context.attachedEvidence
      ? {
          call_id: context.attachedEvidence.callId,
          evidence_id: context.attachedEvidence.evidenceId,
        }
      : null,
    rule: "Use only these exact identifiers and versions. Ask for typed evidence before commitment when attached_evidence is null.",
  });
}

function safeErrorLabel(error: unknown): string {
  if (error instanceof BrowserRealtimeError) {
    const labels: Record<string, string> = {
      permission: "Microphone permission denied",
      microphone_unavailable: "Microphone unavailable",
      credential: "Voice credential unavailable",
      provider: "Realtime provider unavailable",
      credential_expired: "Voice credential expired",
      sdp: "Secure audio negotiation failed",
      timeout: "Realtime connection timed out",
      connection: "Voice connection failed",
    };
    return labels[error.category] ?? "Voice session failed";
  }
  return "Voice session failed";
}

export function BrowserVoiceExperience({
  operation,
  audit,
  attachedEvidence,
  refreshAuthoritativeState,
}: BrowserVoiceExperienceProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const attemptInProgressRef = useRef(false);
  const connectionRef = useRef<BrowserRealtimeConnection | null>(null);
  const generationRef = useRef(0);
  const sentContextRef = useRef<RealtimeOperationalContext | null>(null);
  const terminalStateRef = useRef<VoiceState>({
    kind: "disconnected",
    reason: "clean",
  });
  const toolPendingRef = useRef(false);
  const operationalContext = useMemo(
    () => createOperationalContext(operation, audit, attachedEvidence),
    [attachedEvidence, audit, operation],
  );
  const [current] = useState(
    () =>
      new CurrentVoiceContext(
        operationalContext,
        refreshAuthoritativeState,
        attachedEvidence,
      ),
  );
  const [state, setState] = useState<VoiceState>({ kind: "idle" });
  const [playback, setPlayback] = useState("waiting");
  const [microphone, setMicrophone] = useState("off");
  const [tool, setTool] = useState("ready");
  const [text, setText] = useState("");
  const [dispatcher] = useState(() =>
    createRealtimeToolDispatcher({
      getContext: () => current.getContext(),
      refreshAuthoritativeContext: () => current.refreshState(),
    }),
  );

  useEffect(() => {
    current.update(
      operationalContext,
      refreshAuthoritativeState,
      attachedEvidence,
    );
  }, [
    attachedEvidence,
    current,
    operationalContext,
    refreshAuthoritativeState,
  ]);

  useEffect(() => {
    const connection = connectionRef.current;
    if (
      state.kind !== "connected" ||
      tool === "running" ||
      toolPendingRef.current ||
      !connection ||
      sentContextRef.current === operationalContext
    ) {
      return;
    }
    connection.sendContext(contextMessage(operationalContext));
    sentContextRef.current = operationalContext;
  }, [operationalContext, state.kind, tool]);

  const reconcileDispatcher = useCallback(
    async (generation: number) => {
      try {
        if (dispatcher.isReconciling()) setState({ kind: "reconciling" });
        await dispatcher.reconcile();
        if (generation !== generationRef.current) return false;
        setState(terminalStateRef.current);
        return true;
      } catch {
        if (generation !== generationRef.current) return false;
        setState({
          kind: "error",
          category: "Authoritative voice reconciliation failed",
        });
        return false;
      }
    },
    [dispatcher],
  );

  const handleStatus = useCallback(
    (status: BrowserRealtimeStatus) => {
      if (status.category === "microphone") setMicrophone(status.state);
      if (status.category === "playback") setPlayback(status.state);
      if (status.category === "tool") setTool(status.state);
      if (status.category === "provider" && status.state === "error") {
        dispatcher.markDisconnected();
        terminalStateRef.current = {
          kind: "error",
          category: "Realtime provider reported a session error",
        };
        setState(terminalStateRef.current);
        void reconcileDispatcher(generationRef.current);
        return;
      }
      if (status.category !== "connection") return;

      if (status.state === "connected") setState({ kind: "connected" });
      if (status.state === "disconnected_clean") {
        dispatcher.markDisconnected();
        terminalStateRef.current = { kind: "disconnected", reason: "clean" };
        setState(terminalStateRef.current);
        void reconcileDispatcher(generationRef.current);
      }
      if (status.state === "disconnected_unclean") {
        dispatcher.markDisconnected();
        terminalStateRef.current = {
          kind: "disconnected",
          reason: "unclean",
        };
        setState(terminalStateRef.current);
        void reconcileDispatcher(generationRef.current);
      }
    },
    [dispatcher, reconcileDispatcher],
  );

  const closeActive = useCallback(() => {
    generationRef.current += 1;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    attemptInProgressRef.current = false;
    dispatcher.markDisconnected();
    connectionRef.current?.close();
    connectionRef.current = null;
    sentContextRef.current = null;
    setMicrophone("off");
    setPlayback("waiting");
  }, [dispatcher]);

  const start = useCallback(
    async (reconnecting = false) => {
      if (attemptInProgressRef.current) return;
      closeActive();
      attemptInProgressRef.current = true;
      const generation = generationRef.current;
      if (dispatcher.isReconciling()) {
        const reconciled = await reconcileDispatcher(generation);
        if (!reconciled || generation !== generationRef.current) {
          attemptInProgressRef.current = false;
          return;
        }
      }
      setState({
        kind: reconnecting ? "reconnecting" : "requesting_permission",
      });

      const remoteAudio = audioRef.current;
      if (!remoteAudio) {
        attemptInProgressRef.current = false;
        setState({ kind: "error", category: "Playback unavailable" });
        return;
      }

      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      let adoptedConnection = false;
      try {
        const connection = await connectBrowserRealtime({
          remoteAudio,
          signal: abortController.signal,
          onStatus: (status) => {
            if (generation === generationRef.current) handleStatus(status);
          },
          getAuthoritativeContext: () => {
            if (generation !== generationRef.current) {
              throw new BrowserRealtimeError("connection");
            }
            const context = current.getContext();
            sentContextRef.current = context;
            return contextMessage(context);
          },
          issueClientSecret: async () => {
            if (generation !== generationRef.current) {
              throw new BrowserRealtimeError("connection");
            }
            setState({ kind: "connecting" });
            try {
              const response = await createRealtimeClientSecret({
                signal: abortController.signal,
              });
              return response.data;
            } catch {
              throw new BrowserRealtimeError("credential");
            }
          },
          dispatchTool: async (request) => {
            if (generation !== generationRef.current) {
              throw new BrowserRealtimeError("connection");
            }
            toolPendingRef.current = true;
            try {
              return await dispatcher.dispatch(request);
            } finally {
              if (generation === generationRef.current) {
                toolPendingRef.current = false;
              }
            }
          },
        });
        if (generation !== generationRef.current) {
          connection.close();
          return;
        }
        connectionRef.current = connection;
        adoptedConnection = true;
        const context = current.getContext();
        connection.sendContext(contextMessage(context));
        sentContextRef.current = context;
      } catch (error) {
        if (generation !== generationRef.current) return;
        setState({ kind: "error", category: safeErrorLabel(error) });
        setMicrophone("off");
      } finally {
        attemptInProgressRef.current = false;
        if (
          !adoptedConnection &&
          abortControllerRef.current === abortController
        ) {
          abortControllerRef.current = null;
        }
      }
    },
    [closeActive, current, dispatcher, handleStatus, reconcileDispatcher],
  );

  useEffect(() => {
    return () => {
      generationRef.current += 1;
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      attemptInProgressRef.current = false;
      dispatcher.markDisconnected();
      connectionRef.current?.close();
      connectionRef.current = null;
      void dispatcher.reconcile().catch(() => undefined);
    };
  }, [dispatcher]);

  const stop = () => {
    closeActive();
    const generation = generationRef.current;
    terminalStateRef.current = { kind: "disconnected", reason: "clean" };
    setState(
      dispatcher.isReconciling()
        ? { kind: "reconciling" }
        : terminalStateRef.current,
    );
    void reconcileDispatcher(generation);
  };

  const useTextFallback = () => {
    closeActive();
    const generation = generationRef.current;
    terminalStateRef.current = { kind: "fallback" };
    setState(
      dispatcher.isReconciling()
        ? { kind: "reconciling" }
        : terminalStateRef.current,
    );
    void reconcileDispatcher(generation);
  };

  const sendText = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!connectionRef.current || state.kind !== "connected" || !text.trim())
      return;
    connectionRef.current.sendText(text);
    setText("");
  };

  const connected = state.kind === "connected";
  const active = [
    "requesting_permission",
    "connecting",
    "connected",
    "reconnecting",
  ].includes(state.kind);
  const stateLabel =
    state.kind === "disconnected"
      ? `DISCONNECTED · ${state.reason.toUpperCase()}`
      : state.kind.replaceAll("_", " ").toUpperCase();
  const stateAnnouncement =
    state.kind === "error"
      ? `Voice connection error. ${state.category}.`
      : state.kind === "disconnected"
        ? `Voice connection disconnected ${state.reason === "clean" ? "cleanly" : "unexpectedly"}.`
        : `Voice connection ${state.kind.replaceAll("_", " ")}.`;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <Headphones aria-hidden="true" className="size-5" />
            Browser voice simulator
          </span>
          <StatusBadge
            tone={
              connected
                ? "success"
                : state.kind === "error"
                  ? "warning"
                  : "neutral"
            }
            label={stateLabel}
          />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <p className="text-sm text-muted-foreground">
          English WebRTC simulation only. This does not dial a carrier or use
          PSTN telephony. Operational changes still pass through the typed Volta
          API.
        </p>

        <p className="sr-only" role="status" aria-live="polite">
          {stateAnnouncement} Microphone {microphone.replaceAll("_", " ")}.
          Playback {playback.replaceAll("_", " ")}. Tool boundary{" "}
          {tool.replaceAll("_", " ")}.
        </p>
        <div className="grid gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-md border border-border p-3">
            <p className="font-medium">Microphone</p>
            <p className="mt-1 text-muted-foreground">
              {microphone.replaceAll("_", " ")}
            </p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="font-medium">Playback</p>
            <p className="mt-1 text-muted-foreground">
              {playback.replaceAll("_", " ")}
            </p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="font-medium">Tool boundary</p>
            <p className="mt-1 text-muted-foreground">
              {tool.replaceAll("_", " ")}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            onClick={() => void start(false)}
            disabled={active}
          >
            <Mic aria-hidden="true" data-icon="inline-start" />
            Start voice
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={stop}
            disabled={!active}
          >
            <Square aria-hidden="true" data-icon="inline-start" />
            Stop
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => void start(true)}
            disabled={[
              "requesting_permission",
              "connecting",
              "reconnecting",
              "reconciling",
            ].includes(state.kind)}
          >
            <RefreshCw aria-hidden="true" data-icon="inline-start" />
            Reconnect
          </Button>
          <Button type="button" variant="ghost" onClick={useTextFallback}>
            Use text fallback
          </Button>
        </div>

        {state.kind === "error" ? (
          <Alert variant="destructive" role="alert">
            <AlertTitle>{state.category}</AlertTitle>
            <AlertDescription>
              Retry with explicit Reconnect, or continue with the text controls
              below.
            </AlertDescription>
          </Alert>
        ) : null}
        {state.kind === "disconnected" && state.reason === "unclean" ? (
          <Alert variant="destructive" role="alert">
            <AlertTitle>Voice connection ended unexpectedly</AlertTitle>
            <AlertDescription>
              Reconnect to mint a fresh voice credential, or continue with the
              text controls below.
            </AlertDescription>
          </Alert>
        ) : null}
        {state.kind === "reconciling" ? (
          <Alert role="status">
            <AlertTitle>Reconciling the last tool request</AlertTitle>
            <AlertDescription>
              New voice mutations remain blocked until the authoritative
              operation refresh completes.
            </AlertDescription>
          </Alert>
        ) : null}

        <form onSubmit={sendText} className="space-y-2">
          <Label htmlFor="voice-text-fallback">
            Send typed text into this voice session
          </Label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              id="voice-text-fallback"
              name="voice-text-fallback"
              autoComplete="off"
              value={text}
              onChange={(event) => setText(event.target.value.slice(0, 4_000))}
              maxLength={4_000}
              disabled={!connected}
              className="h-10 min-w-0 flex-1 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
            <Button
              type="submit"
              variant="outline"
              disabled={!connected || !text.trim()}
            >
              <Send aria-hidden="true" data-icon="inline-start" />
              Send
            </Button>
          </div>
        </form>

        <audio
          ref={audioRef}
          autoPlay
          aria-label="Volta simulated voice playback"
        />
      </CardContent>
    </Card>
  );
}

export type { BrowserVoiceExperienceProps };

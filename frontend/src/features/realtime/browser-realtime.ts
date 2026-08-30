import type {
  RealtimeToolOutput,
  RealtimeToolRequest,
} from "./tool-dispatcher";
import { parseRealtimeToolRequest } from "./tool-dispatcher";

const REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls";
const MAX_EVENT_BYTES = 65_536;
const MAX_SDP_BYTES = 262_144;
const MAX_TEXT_LENGTH = 4_000;
const DATA_CHANNEL_OPEN_TIMEOUT_MS = 10_000;
const SDP_EXCHANGE_TIMEOUT_MS = 10_000;

export type BrowserRealtimeStatus = Readonly<{
  category:
    "connection" | "microphone" | "playback" | "speech" | "tool" | "provider";
  state: string;
}>;

export type BrowserRealtimeOptions = Readonly<{
  issueClientSecret: () => Promise<
    Readonly<{
      client_secret: string;
      expires_at: number;
      session_id: string;
      model: string;
    }>
  >;
  dispatchTool: (request: RealtimeToolRequest) => Promise<RealtimeToolOutput>;
  getAuthoritativeContext: () => string;
  remoteAudio: HTMLAudioElement;
  onStatus: (status: BrowserRealtimeStatus) => void;
  signal: AbortSignal;
}>;

export type BrowserRealtimeConnection = Readonly<{
  sessionId: string;
  model: string;
  expiresAt: number;
  sendContext(text: string): void;
  sendText(text: string): void;
  close(): void;
}>;

export type BrowserRealtimeErrorCategory =
  | "permission"
  | "microphone_unavailable"
  | "credential"
  | "credential_expired"
  | "sdp"
  | "timeout"
  | "provider"
  | "connection";

export class BrowserRealtimeError extends Error {
  readonly category: BrowserRealtimeErrorCategory;

  constructor(category: BrowserRealtimeErrorCategory) {
    super(`Browser Realtime ${category}`);
    this.name = "BrowserRealtimeError";
    this.category = category;
  }
}

type RealtimeEventSender = (event: unknown) => void;

type SdpExchangeOptions = Readonly<{
  clientSecret: string;
  expiresAt: number;
  offerSdp: string;
  signal: AbortSignal;
  fetcher?: typeof fetch;
  now?: () => number;
  maximumTimeoutMs?: number;
}>;

export async function exchangeRealtimeSdp({
  clientSecret,
  expiresAt,
  offerSdp,
  signal,
  fetcher = fetch,
  now = Date.now,
  maximumTimeoutMs = SDP_EXCHANGE_TIMEOUT_MS,
}: SdpExchangeOptions): Promise<string> {
  const remainingMs = expiresAt * 1_000 - now();
  if (remainingMs <= 0) {
    throw new BrowserRealtimeError("credential_expired");
  }

  const abortController = new AbortController();
  const timeoutCategory =
    remainingMs <= maximumTimeoutMs ? "credential_expired" : "timeout";
  const onCallerAbort = () => abortController.abort();
  signal.addEventListener("abort", onCallerAbort, { once: true });
  if (signal.aborted) abortController.abort();
  const timeoutId = window.setTimeout(
    () => abortController.abort(),
    Math.min(remainingMs, maximumTimeoutMs),
  );

  try {
    const answer = await fetcher(REALTIME_CALLS_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${clientSecret}`,
        "Content-Type": "application/sdp",
      },
      body: offerSdp,
      signal: abortController.signal,
    });
    if (!answer.ok) throw new BrowserRealtimeError("provider");
    const answerSdp = await answer.text();
    if (new TextEncoder().encode(answerSdp).byteLength > MAX_SDP_BYTES) {
      throw new BrowserRealtimeError("sdp");
    }
    return answerSdp;
  } catch (error) {
    if (error instanceof BrowserRealtimeError) throw error;
    if (signal.aborted) throw new BrowserRealtimeError("connection");
    if (abortController.signal.aborted) {
      throw new BrowserRealtimeError(timeoutCategory);
    }
    throw new BrowserRealtimeError("sdp");
  } finally {
    clearTimeout(timeoutId);
    signal.removeEventListener("abort", onCallerAbort);
  }
}

export async function sendToolResultWithCurrentContext({
  dispatchTool,
  getAuthoritativeContext,
  onStatus,
  providerCallId,
  request,
  send,
}: Readonly<{
  dispatchTool: BrowserRealtimeOptions["dispatchTool"];
  getAuthoritativeContext: BrowserRealtimeOptions["getAuthoritativeContext"];
  onStatus: BrowserRealtimeOptions["onStatus"];
  providerCallId: string;
  request: RealtimeToolRequest;
  send: RealtimeEventSender;
}>): Promise<void> {
  onStatus({ category: "tool", state: "running" });
  const output = await dispatchTool(request);
  send({
    type: "conversation.item.create",
    item: {
      type: "function_call_output",
      call_id: providerCallId,
      output: JSON.stringify(output),
    },
  });
  const context = getAuthoritativeContext().trim().slice(0, MAX_TEXT_LENGTH);
  if (context) {
    send({
      type: "conversation.item.create",
      item: {
        type: "message",
        role: "user",
        content: [{ type: "input_text", text: context }],
      },
    });
  }
  send({ type: "response.create" });
  onStatus({
    category: "tool",
    state: output.ok ? "completed" : "failed",
  });
}

type SafeProviderEvent =
  | Readonly<{
      type: "response.output_item.done";
      item: Readonly<{
        type: "function_call";
        id: string;
        call_id: string;
        name: string;
        arguments: string;
      }>;
    }>
  | Readonly<{ type: string }>;

const OBSERVED_EVENTS = new Set([
  "session.created",
  "session.updated",
  "input_audio_buffer.speech_started",
  "input_audio_buffer.speech_stopped",
  "response.created",
  "response.done",
  "conversation.item.truncated",
  "output_audio_buffer.cleared",
  "rate_limits.updated",
  "error",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseRealtimeServerEvent(
  raw: unknown,
): SafeProviderEvent | null {
  if (typeof raw !== "string") return null;
  if (new TextEncoder().encode(raw).byteLength > MAX_EVENT_BYTES) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw) as unknown;
  } catch {
    return null;
  }

  if (!isRecord(parsed) || typeof parsed.type !== "string") return null;
  if (OBSERVED_EVENTS.has(parsed.type)) return { type: parsed.type };
  if (parsed.type !== "response.output_item.done" || !isRecord(parsed.item)) {
    return null;
  }

  const item = parsed.item;
  if (
    item.type !== "function_call" ||
    typeof item.id !== "string" ||
    item.id.length === 0 ||
    item.id.length > 128 ||
    typeof item.call_id !== "string" ||
    item.call_id.length === 0 ||
    item.call_id.length > 128 ||
    typeof item.name !== "string" ||
    typeof item.arguments !== "string"
  ) {
    return null;
  }

  return {
    type: "response.output_item.done",
    item: {
      type: "function_call",
      id: item.id,
      call_id: item.call_id,
      name: item.name,
      arguments: item.arguments,
    },
  };
}

function categorizedMediaError(error: unknown): BrowserRealtimeError {
  if (error instanceof BrowserRealtimeError) return error;
  if (error instanceof DOMException && error.name === "NotAllowedError") {
    return new BrowserRealtimeError("permission");
  }
  return new BrowserRealtimeError("microphone_unavailable");
}

function waitForDataChannelOpen(channel: RTCDataChannel): Promise<void> {
  if (channel.readyState === "open") return Promise.resolve();
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      clearTimeout(timeoutId);
      channel.removeEventListener("open", onOpen);
      channel.removeEventListener("close", onFailure);
      channel.removeEventListener("error", onFailure);
    };
    const onOpen = () => {
      cleanup();
      resolve();
    };
    const onFailure = () => {
      cleanup();
      reject(new BrowserRealtimeError("connection"));
    };
    const timeoutId = window.setTimeout(
      onFailure,
      DATA_CHANNEL_OPEN_TIMEOUT_MS,
    );
    channel.addEventListener("open", onOpen);
    channel.addEventListener("close", onFailure);
    channel.addEventListener("error", onFailure);
  });
}

export async function connectBrowserRealtime(
  options: BrowserRealtimeOptions,
): Promise<BrowserRealtimeConnection> {
  if (options.signal.aborted) {
    throw new BrowserRealtimeError("connection");
  }
  let microphone: MediaStream;
  options.onStatus({ category: "microphone", state: "requesting_permission" });
  try {
    microphone = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (options.signal.aborted) {
      for (const track of microphone.getTracks()) track.stop();
      throw new BrowserRealtimeError("connection");
    }
    options.onStatus({ category: "microphone", state: "active" });
  } catch (error) {
    throw categorizedMediaError(error);
  }

  let peer: RTCPeerConnection;
  let channel: RTCDataChannel;
  try {
    peer = new RTCPeerConnection();
    channel = peer.createDataChannel("oai-events");
  } catch {
    for (const track of microphone.getTracks()) track.stop();
    throw new BrowserRealtimeError("connection");
  }
  let closed = false;
  let ephemeralSecret: string | null = null;

  const send = (event: unknown) => {
    if (closed || channel.readyState !== "open") return;
    channel.send(JSON.stringify(event));
  };

  const close = (
    terminalState?: "disconnected_clean" | "disconnected_unclean",
  ) => {
    if (closed) return;
    closed = true;
    ephemeralSecret = null;
    channel.removeEventListener("open", onChannelOpen);
    channel.removeEventListener("close", onChannelClose);
    channel.removeEventListener("error", onChannelError);
    channel.removeEventListener("message", onMessage);
    peer.removeEventListener("track", onTrack);
    peer.removeEventListener("connectionstatechange", onConnectionStateChange);
    options.signal.removeEventListener("abort", onAbort);
    for (const track of microphone.getTracks()) track.stop();
    if (channel.readyState !== "closed") channel.close();
    peer.close();
    options.remoteAudio.pause();
    options.remoteAudio.srcObject = null;
    options.onStatus({ category: "microphone", state: "off" });
    options.onStatus({ category: "playback", state: "stopped" });
    if (terminalState) {
      options.onStatus({ category: "connection", state: terminalState });
    }
  };

  const onChannelOpen = () => {
    options.onStatus({ category: "connection", state: "connected" });
  };
  const onChannelClose = () => {
    options.onStatus({
      category: "connection",
      state: "data_channel_closed",
    });
    close("disconnected_unclean");
  };
  const onChannelError = () => {
    options.onStatus({ category: "connection", state: "data_channel_error" });
    close("disconnected_unclean");
  };
  const onTrack = (event: RTCTrackEvent) => {
    const [stream] = event.streams;
    if (!stream) return;
    options.remoteAudio.srcObject = stream;
    void options.remoteAudio.play().then(
      () => options.onStatus({ category: "playback", state: "playing" }),
      () => options.onStatus({ category: "playback", state: "blocked" }),
    );
  };
  const onConnectionStateChange = () => {
    const state = peer.connectionState;
    options.onStatus({
      category: "connection",
      state,
    });
    if (["closed", "disconnected", "failed"].includes(state)) {
      close("disconnected_unclean");
    }
  };
  const onAbort = () => close("disconnected_clean");
  const onMessage = (message: MessageEvent<unknown>) => {
    const event = parseRealtimeServerEvent(message.data);
    if (!event) return;

    if (event.type === "input_audio_buffer.speech_started") {
      options.onStatus({ category: "speech", state: "caller_speaking" });
      return;
    }
    if (event.type === "input_audio_buffer.speech_stopped") {
      options.onStatus({ category: "speech", state: "caller_stopped" });
      return;
    }
    if (event.type === "conversation.item.truncated") {
      options.onStatus({ category: "playback", state: "interrupted" });
      return;
    }
    if (event.type === "output_audio_buffer.cleared") {
      options.onStatus({ category: "playback", state: "cleared" });
      return;
    }
    if (event.type === "error") {
      options.onStatus({ category: "provider", state: "error" });
      close();
      return;
    }
    if (event.type === "session.created" || event.type === "session.updated") {
      options.onStatus({ category: "provider", state: "session_ready" });
      return;
    }
    if (event.type === "response.created") {
      options.onStatus({ category: "playback", state: "responding" });
      return;
    }
    if (event.type === "response.done") {
      options.onStatus({ category: "playback", state: "ready" });
      return;
    }
    if (event.type === "rate_limits.updated") {
      options.onStatus({ category: "provider", state: "limits_updated" });
      return;
    }
    if (event.type !== "response.output_item.done" || !("item" in event))
      return;

    const request = parseRealtimeToolRequest({
      providerCallId: event.item.call_id,
      name: event.item.name,
      argumentsJson: event.item.arguments,
    });
    if (!request) {
      options.onStatus({ category: "tool", state: "rejected" });
      return;
    }

    void sendToolResultWithCurrentContext({
      dispatchTool: options.dispatchTool,
      getAuthoritativeContext: options.getAuthoritativeContext,
      onStatus: options.onStatus,
      providerCallId: event.item.call_id,
      request,
      send: (outbound) => {
        if (!closed) send(outbound);
      },
    });
  };

  try {
    channel.addEventListener("open", onChannelOpen);
    channel.addEventListener("close", onChannelClose);
    channel.addEventListener("error", onChannelError);
    channel.addEventListener("message", onMessage);
    peer.addEventListener("track", onTrack);
    peer.addEventListener("connectionstatechange", onConnectionStateChange);
    options.signal.addEventListener("abort", onAbort, { once: true });
    if (options.signal.aborted) throw new BrowserRealtimeError("connection");
    for (const track of microphone.getTracks())
      peer.addTrack(track, microphone);
    options.onStatus({ category: "connection", state: "connecting" });
    let credential: Awaited<
      ReturnType<typeof options.issueClientSecret>
    > | null = await options.issueClientSecret();
    const expiresAt = credential.expires_at;
    const model = credential.model;
    const sessionId = credential.session_id;
    ephemeralSecret = credential.client_secret;
    credential = null;
    const offer = await peer.createOffer();
    const offerSdp = offer.sdp;
    if (
      typeof offerSdp !== "string" ||
      offerSdp.trim().length === 0 ||
      new TextEncoder().encode(offerSdp).byteLength > MAX_SDP_BYTES
    ) {
      throw new BrowserRealtimeError("sdp");
    }
    await peer.setLocalDescription(offer);
    const answerSdp = await exchangeRealtimeSdp({
      clientSecret: ephemeralSecret,
      expiresAt,
      offerSdp,
      signal: options.signal,
    });
    ephemeralSecret = null;
    await peer.setRemoteDescription({ type: "answer", sdp: answerSdp });
    await waitForDataChannelOpen(channel);

    const sendMessage = (text: string, requestResponse: boolean) => {
      const bounded = text.trim().slice(0, MAX_TEXT_LENGTH);
      if (!bounded) return;
      send({
        type: "conversation.item.create",
        item: {
          type: "message",
          role: "user",
          content: [{ type: "input_text", text: bounded }],
        },
      });
      if (requestResponse) send({ type: "response.create" });
    };

    return Object.freeze({
      sessionId,
      model,
      expiresAt,
      sendContext(text: string) {
        sendMessage(text, false);
      },
      sendText(text: string) {
        sendMessage(text, true);
      },
      close: () => close("disconnected_clean"),
    });
  } catch (error) {
    ephemeralSecret = null;
    close();
    if (error instanceof BrowserRealtimeError) throw error;
    throw new BrowserRealtimeError("sdp");
  }
}

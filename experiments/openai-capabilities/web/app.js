"use strict";

const state = {
  peer: null,
  channel: null,
  stream: null,
  startedAt: null,
  events: [],
};

const statusNode = document.querySelector("#status");
const eventsNode = document.querySelector("#events");
const startButton = document.querySelector("#start");
const stopButton = document.querySelector("#stop");
const toolButton = document.querySelector("#tool");
const safeTypes = new Set([
  "session.created",
  "session.updated",
  "input_audio_buffer.speech_started",
  "input_audio_buffer.speech_stopped",
  "conversation.item.added",
  "conversation.item.done",
  "response.created",
  "response.done",
  "response.cancelled",
  "conversation.item.truncated",
  "rate_limits.updated",
  "error",
]);

function setStatus(message) {
  statusNode.textContent = message;
}

function retainEvent(event) {
  if (!safeTypes.has(event.type)) return;
  const retained = {
    type: event.type,
    elapsed_ms: Math.round(performance.now() - state.startedAt),
  };
  for (const field of ["event_id", "item_id", "audio_start_ms", "audio_end_ms"]) {
    if (typeof event[field] === "string" || typeof event[field] === "number") {
      retained[field] = event[field];
    }
  }
  if (event.response && typeof event.response === "object") {
    if (typeof event.response.id === "string") retained.response_id = event.response.id;
    if (typeof event.response.status === "string") retained.response_status = event.response.status;
  }
  if (event.type === "error" && event.error && typeof event.error === "object") {
    retained.error_code = event.error.code || event.error.type || "unknown";
  }
  if (event.type === "rate_limits.updated" && Array.isArray(event.rate_limits)) {
    retained.rate_limits = event.rate_limits.map((limit) => ({
      name: limit.name,
      limit: limit.limit,
      remaining: limit.remaining,
      reset_seconds: limit.reset_seconds,
    }));
  }
  state.events.push(retained);
  eventsNode.textContent = JSON.stringify(state.events, null, 2);
}

function retainToolEvent(type, callId) {
  state.events.push({
    type,
    call_id: callId,
    elapsed_ms: Math.round(performance.now() - state.startedAt),
  });
  eventsNode.textContent = JSON.stringify(state.events, null, 2);
}

function send(event) {
  if (!state.channel || state.channel.readyState !== "open") {
    throw new Error("data_channel_not_open");
  }
  state.channel.send(JSON.stringify(event));
}

function handleToolCalls(event) {
  if (event.type !== "response.done" || !Array.isArray(event.response?.output)) return;
  for (const item of event.response.output) {
    if (item.type !== "function_call") continue;
    let argumentsValue;
    try {
      argumentsValue = JSON.parse(item.arguments);
    } catch {
      setStatus("Invalid synthetic tool arguments; no tool executed.");
      return;
    }
    if (
      !argumentsValue ||
      typeof argumentsValue !== "object" ||
      Array.isArray(argumentsValue) ||
      item.name !== "check_synthetic_availability" ||
      typeof item.call_id !== "string" ||
      argumentsValue.reference !== "SYN-2042" ||
      Object.keys(argumentsValue).length !== 1
    ) {
      setStatus("Unsafe or unexpected tool request rejected.");
      return;
    }
    retainToolEvent("tool.call", item.call_id);
    send({
      type: "conversation.item.create",
      item: {
        type: "function_call_output",
        call_id: item.call_id,
        output: JSON.stringify({ reference: "SYN-2042", available: true }),
      },
    });
    retainToolEvent("tool.output", item.call_id);
    send({ type: "response.create" });
    setStatus(`Synthetic tool output returned for call ${item.call_id}.`);
  }
}

function handleProviderMessage(message) {
  let event;
  try {
    event = JSON.parse(message.data);
  } catch {
    setStatus("Provider sent an invalid event.");
    return;
  }
  retainEvent(event);
  handleToolCalls(event);
  if (event.type === "input_audio_buffer.speech_started") {
    setStatus("Speech detected. If model audio was active, barge-in is in progress.");
  } else if (event.type === "error") {
    setStatus(`Provider error (${event.error?.code || event.error?.type || "unknown"}).`);
  }
}

async function disconnect() {
  if (state.channel) state.channel.close();
  if (state.peer) state.peer.close();
  if (state.stream) state.stream.getTracks().forEach((track) => track.stop());
  state.peer = null;
  state.channel = null;
  state.stream = null;
  startButton.disabled = false;
  stopButton.disabled = true;
  toolButton.disabled = true;
  setStatus("Disconnected. Deterministic text fallback remains available.");
}

async function connect() {
  startButton.disabled = true;
  setStatus("Requesting microphone permission…");
  state.startedAt = performance.now();
  state.events = [];
  eventsNode.textContent = "[]";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const tokenResponse = await fetch("/token", {
      method: "POST",
      cache: "no-store",
      headers: { "X-Phase02-Harness": "1" },
    });
    const tokenPayload = await tokenResponse.json();
    if (!tokenResponse.ok || typeof tokenPayload.value !== "string") {
      throw new Error(tokenPayload.error || "token_request_failed");
    }
    const ephemeralKey = tokenPayload.value;
    const peer = new RTCPeerConnection();
    const remoteAudio = document.querySelector("#remote-audio");
    peer.ontrack = (event) => {
      remoteAudio.srcObject = event.streams[0];
    };
    stream.getTracks().forEach((track) => peer.addTrack(track, stream));
    const channel = peer.createDataChannel("oai-events");
    channel.addEventListener("message", handleProviderMessage);
    channel.addEventListener("open", () => {
      setStatus("Connected. Speak a synthetic English turn.");
      stopButton.disabled = false;
      toolButton.disabled = false;
    });
    channel.addEventListener("close", () => setStatus("Data channel closed."));
    state.peer = peer;
    state.channel = channel;
    state.stream = stream;
    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);
    const sdpResponse = await fetch("https://api.openai.com/v1/realtime/calls", {
      method: "POST",
      body: offer.sdp,
      headers: {
        Authorization: `Bearer ${ephemeralKey}`,
        "Content-Type": "application/sdp",
      },
    });
    if (!sdpResponse.ok) throw new Error(`webrtc_${sdpResponse.status}`);
    await peer.setRemoteDescription({ type: "answer", sdp: await sdpResponse.text() });
  } catch (error) {
    await disconnect();
    const category = error instanceof DOMException ? error.name : String(error.message || error);
    setStatus(`Connection failed (${category}). Deterministic text fallback is available.`);
  }
}

startButton.addEventListener("click", connect);
stopButton.addEventListener("click", disconnect);
toolButton.addEventListener("click", () => {
  send({
    type: "conversation.item.create",
    item: {
      type: "message",
      role: "user",
      content: [
        {
          type: "input_text",
          text: "Check availability for the synthetic reference SYN-2042.",
        },
      ],
    },
  });
  send({ type: "response.create" });
  setStatus("Synthetic tool request sent.");
});
document.querySelector("#copy-fallback").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(document.querySelector("#fallback").value);
    setStatus("Fallback text copied.");
  } catch {
    setStatus("Clipboard unavailable; fallback text remains selected manually.");
  }
});
document.querySelector("#download").addEventListener("click", () => {
  const blob = new Blob(
    [JSON.stringify({ status: "operator_review_required", transport: "webrtc", events: state.events }, null, 2)],
    { type: "application/json" },
  );
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "phase02-webrtc-redacted.json";
  link.click();
  URL.revokeObjectURL(link.href);
});
window.addEventListener("beforeunload", () => {
  if (state.stream) state.stream.getTracks().forEach((track) => track.stop());
  if (state.peer) state.peer.close();
});

"use client";

import { CircleAlert, FileAudio, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { getEvidenceAudio } from "@/lib/api/generated/api";
import { ApiHttpError } from "@/lib/api/volta-fetch";

type AudioState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; url: string }
  | { kind: "error"; error: unknown };

function errorCopy(error: unknown) {
  if (!(error instanceof ApiHttpError)) {
    return "The audio request did not complete. Retry without changing the evidence record.";
  }
  if (error.status === 401)
    return "Reconnect the demo bearer before loading audio.";
  if (error.status === 403)
    return "This demo identity cannot load the evidence audio.";
  if (error.status === 404)
    return "Evidence audio is unavailable. The recap and brief remain available.";
  if (error.status === 413)
    return "Evidence audio exceeds the demo playback limit.";
  return error.data.message;
}

export function EvidenceAudioPlayer({
  audioStartMs,
  evidenceId,
}: {
  audioStartMs: number;
  evidenceId: string;
}) {
  const [state, setState] = useState<AudioState>({ kind: "idle" });
  const audioRef = useRef<HTMLAudioElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const urlRef = useRef<string | null>(null);

  const clearTransientAudio = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (audioRef.current) {
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
    }
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
  };

  useEffect(() => clearTransientAudio, []);

  const load = async () => {
    clearTransientAudio();
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ kind: "loading" });
    try {
      const response = await getEvidenceAudio(evidenceId, {
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(response.data);
      urlRef.current = url;
      abortRef.current = null;
      setState({ kind: "ready", url });
    } catch (error) {
      if (controller.signal.aborted) return;
      abortRef.current = null;
      setState({ kind: "error", error });
    }
  };

  const seekToEvidence = () => {
    const audio = audioRef.current;
    if (!audio) return;
    const offset = audioStartMs / 1000;
    audio.currentTime = Number.isFinite(audio.duration)
      ? Math.min(offset, Math.max(0, audio.duration))
      : offset;
  };

  if (state.kind === "ready") {
    return (
      <div className="flex flex-col gap-2">
        <audio
          ref={audioRef}
          className="w-full"
          aria-describedby={`audio-description-${evidenceId}`}
          controls
          preload="metadata"
          src={state.url}
          onLoadedMetadata={seekToEvidence}
        >
          Your browser does not support evidence audio playback.
        </audio>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p
            id={`audio-description-${evidenceId}`}
            className="text-sm text-muted-foreground"
            role="status"
          >
            Playback begins at {(audioStartMs / 1000).toFixed(3)} seconds. The
            written recap and call brief below provide the accessible text
            context for this recording.
          </p>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => void load()}
          >
            <RefreshCw aria-hidden="true" data-icon="inline-start" />
            Reload audio
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start gap-3">
      <Button
        type="button"
        variant="outline"
        onClick={() => void load()}
        disabled={state.kind === "loading"}
      >
        <FileAudio aria-hidden="true" data-icon="inline-start" />
        {state.kind === "loading"
          ? "Loading evidence audio…"
          : "Load evidence audio"}
      </Button>
      {state.kind === "error" ? (
        <Alert variant="destructive" role="alert">
          <CircleAlert aria-hidden="true" />
          <AlertTitle>Audio unavailable</AlertTitle>
          <AlertDescription>{errorCopy(state.error)}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}

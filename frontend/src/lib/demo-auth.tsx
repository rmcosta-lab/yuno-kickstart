"use client";

import { useState, useSyncExternalStore, type FormEvent } from "react";
import { KeyRound, LogOut } from "lucide-react";

import { StatusBadge } from "@/components/control-tower/status-badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

type DemoAuthSnapshot = {
  connected: boolean;
  revision: number;
};

type Listener = () => void;

const listeners = new Set<Listener>();
let bearerToken: string | null = null;
let snapshot: DemoAuthSnapshot = { connected: false, revision: 0 };

function notify() {
  snapshot = {
    connected: bearerToken !== null,
    revision: snapshot.revision + 1,
  };
  for (const listener of listeners) listener();
}

function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return snapshot;
}

const SERVER_SNAPSHOT: DemoAuthSnapshot = { connected: false, revision: 0 };

function getServerSnapshot() {
  return SERVER_SNAPSHOT;
}

export function getDemoBearerToken() {
  return bearerToken;
}

export function setDemoBearerToken(token: string) {
  const normalized = token.trim();
  bearerToken = normalized.length > 0 ? normalized : null;
  notify();
}

export function clearDemoBearerToken() {
  bearerToken = null;
  notify();
}

export function useDemoAuth() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

export function DemoAuthControl() {
  const auth = useDemoAuth();
  const [tokenInput, setTokenInput] = useState("");

  const connect = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!tokenInput.trim()) return;
    setDemoBearerToken(tokenInput);
    setTokenInput("");
  };

  return (
    <section
      aria-labelledby="demo-auth-title"
      className="rounded-lg border border-border bg-card p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2
              id="demo-auth-title"
              className="font-heading text-sm font-semibold text-foreground"
            >
              Demo API authorization
            </h2>
            <StatusBadge
              tone={auth.connected ? "success" : "pending"}
              label={auth.connected ? "CONNECTED" : "TOKEN REQUIRED"}
            />
          </div>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Enter the local demo bearer at runtime. It is kept only in memory
            for this tab and is cleared by a full reload.
          </p>
        </div>
        {auth.connected ? (
          <Button
            type="button"
            variant="outline"
            onClick={clearDemoBearerToken}
          >
            <LogOut aria-hidden="true" data-icon="inline-start" />
            Disconnect
          </Button>
        ) : null}
      </div>

      {!auth.connected ? (
        <form
          onSubmit={connect}
          className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"
        >
          <div className="min-w-0 flex-1 space-y-1.5">
            <Label htmlFor="demo-bearer-token">Demo bearer token</Label>
            <input
              id="demo-bearer-token"
              name="demo-bearer-token"
              type="password"
              autoComplete="off"
              spellCheck={false}
              value={tokenInput}
              onChange={(event) => setTokenInput(event.target.value)}
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
          <Button type="submit" disabled={!tokenInput.trim()}>
            <KeyRound aria-hidden="true" data-icon="inline-start" />
            Connect live API
          </Button>
        </form>
      ) : null}
    </section>
  );
}

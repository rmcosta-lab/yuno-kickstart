/**
 * Session-local handoff of the latest approval-eligible draft from `/intake`
 * to `/mandate`. Fase 07 has no backend list/read endpoint for drafts, so a
 * coordinator reviews one draft at a time within a browser session (see
 * `requirements.md` assumptions). This is browser-only state, never a
 * source of durable truth.
 *
 * Reads go through `useSyncExternalStore` (see `useApprovalEligibleDraft`)
 * so `/mandate` stays hydration-safe: the server and first client paint both
 * see `null`, and same-tab writes/clears from this module notify the
 * subscribed component directly (the native `storage` event never fires for
 * writes made in the same tab that made them).
 */
import { useSyncExternalStore } from "react";

import type { OperationDraftResponse } from "./api/generated/models";

const STORAGE_KEY = "volta.intake.approval-eligible-draft";

type Listener = () => void;
const listeners = new Set<Listener>();

let cachedRaw: string | null = null;
let cachedSnapshot: OperationDraftResponse | null = null;

function notifyListeners() {
  for (const listener of listeners) listener();
}

function readSnapshot(): OperationDraftResponse | null {
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (raw === cachedRaw) return cachedSnapshot;

  cachedRaw = raw;
  try {
    cachedSnapshot = raw ? (JSON.parse(raw) as OperationDraftResponse) : null;
  } catch {
    cachedSnapshot = null;
  }
  return cachedSnapshot;
}

function getServerSnapshot(): OperationDraftResponse | null {
  return null;
}

function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function saveApprovalEligibleDraft(draft: OperationDraftResponse) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
  notifyListeners();
}

export function clearApprovalEligibleDraft() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(STORAGE_KEY);
  notifyListeners();
}

export function useApprovalEligibleDraft(): OperationDraftResponse | null {
  return useSyncExternalStore(subscribe, readSnapshot, getServerSnapshot);
}

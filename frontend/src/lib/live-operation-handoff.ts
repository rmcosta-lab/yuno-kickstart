import { useSyncExternalStore } from "react";

type Listener = () => void;

const listeners = new Set<Listener>();
let operationId: string | null = null;

function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return operationId;
}

function getServerSnapshot() {
  return null;
}

export function saveCurrentOperationId(value: string) {
  operationId = value;
  for (const listener of listeners) listener();
}

export function useCurrentOperationId() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

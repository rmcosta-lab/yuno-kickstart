"use client";

import { useSyncExternalStore } from "react";

type DemoAuthSnapshot = {
  connected: true;
  revision: 0;
};

const AUTOMATIC_DEMO_AUTH: DemoAuthSnapshot = {
  connected: true,
  revision: 0,
};

const subscribe = () => () => undefined;

/**
 * Demo authorization is supplied by the same-origin Next.js proxy. The
 * browser never receives or stores the configured bearer token.
 */
export function useDemoAuth(): DemoAuthSnapshot {
  return useSyncExternalStore(
    subscribe,
    () => AUTOMATIC_DEMO_AUTH,
    () => AUTOMATIC_DEMO_AUTH,
  );
}

export function DemoAuthControl() {
  return null;
}

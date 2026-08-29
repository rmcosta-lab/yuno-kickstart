"use client";

import { useId, useState } from "react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type DemoState = "populated" | "loading" | "empty" | "error";

const STATE_OPTIONS: { value: DemoState; label: string }[] = [
  { value: "populated", label: "Populated" },
  { value: "loading", label: "Loading" },
  { value: "empty", label: "Empty" },
  { value: "error", label: "Error" },
];

type ScreenStateDemoProps = {
  loading: ReactNode;
  empty: ReactNode;
  error: ReactNode;
  populated: ReactNode;
  initialState?: DemoState;
};

/**
 * The only client boundary on each screen: a local toggle so a coordinator
 * (or the smoke test) can preview loading/empty/error without a live
 * provider or timer. All four slots are pre-rendered server content.
 */
export function ScreenStateDemo({
  loading,
  empty,
  error,
  populated,
  initialState = "populated",
}: ScreenStateDemoProps) {
  const [state, setState] = useState<DemoState>(initialState);
  const groupLabelId = useId();
  const content: Record<DemoState, ReactNode> = {
    loading,
    empty,
    error,
    populated,
  };

  return (
    <div className="space-y-6">
      <div>
        <span id={groupLabelId} className="sr-only">
          Preview state
        </span>
        <div
          role="group"
          aria-labelledby={groupLabelId}
          className="inline-flex flex-wrap gap-1 rounded-lg border border-border bg-muted/50 p-1"
        >
          {STATE_OPTIONS.map((option) => {
            const isActive = state === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={isActive}
                onClick={() => setState(option.value)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                  isActive
                    ? "bg-background text-foreground shadow-sm ring-1 ring-border"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
      <div>{content[state]}</div>
    </div>
  );
}

import Link from "next/link";
import type { ReactNode } from "react";

import { ControlTowerNav } from "@/components/control-tower/nav";

export default function ControlTowerLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <a
        className="sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:flex focus:h-10 focus:items-center focus:rounded-md focus:bg-primary focus:px-4 focus:font-mono focus:text-sm focus:text-primary-foreground focus:not-sr-only focus:outline-2 focus:outline-offset-2 focus:outline-ring"
        href="#main-content"
      >
        Skip to main content
      </a>
      <header className="border-b border-border">
        <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-2 px-6 py-4 sm:h-20 sm:flex-row sm:items-center sm:justify-between sm:gap-6 sm:px-10 lg:px-14">
          <Link
            className="flex shrink-0 items-center font-display text-lg font-bold tracking-[0.14em] text-foreground sm:text-xl"
            href="/"
            aria-label="Volta control tower home"
            translate="no"
          >
            VOLTA
          </Link>
          <ControlTowerNav />
        </div>
      </header>

      <main className="flex-1" id="main-content" tabIndex={-1}>
        <div className="mx-auto w-full max-w-[1600px] px-6 py-8 sm:px-10 sm:py-10 lg:px-14">
          {children}
        </div>
      </main>

      <footer className="border-t border-border px-6 py-6 text-center font-mono text-xs tracking-[0.04em] text-muted-foreground sm:px-10 lg:px-14">
        Volta control tower &middot; live text integration &middot; simulated
        fallback labeled no contact &middot;{" "}
        <Link
          className="underline underline-offset-4 hover:text-foreground"
          href="/health"
        >
          system health
        </Link>
      </footer>
    </div>
  );
}

import { CodeXml, PanelTop, Server } from "lucide-react";

import { HealthExperience } from "@/components/health-experience";

const layers = [
  { label: "Browser", technology: "Next.js", icon: PanelTop },
  { label: "API", technology: "FastAPI", icon: Server },
  { label: "Core", technology: "Python", icon: CodeXml },
] as const;

export default function Home() {
  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <a
        className="sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:flex focus:h-10 focus:items-center focus:rounded-md focus:bg-primary focus:px-4 focus:font-mono focus:text-sm focus:text-primary-foreground focus:not-sr-only focus:outline-2 focus:outline-offset-2 focus:outline-ring"
        href="#main-content"
      >
        Skip to main content
      </a>
      <header className="border-b border-border">
        <div className="mx-auto flex min-h-20 w-full max-w-[1600px] flex-col justify-between gap-4 px-6 py-4 sm:h-20 sm:flex-row sm:items-stretch sm:gap-0 sm:px-10 sm:py-0 lg:px-14">
          <a
            className="flex items-center font-display text-lg font-bold tracking-[0.14em] text-foreground sm:text-xl"
            href="#architecture"
            aria-label="Yuno and Nauta home"
            translate="no"
          >
            YUNO × NAUTA
          </a>
          <nav
            className="flex w-full items-stretch justify-between gap-6 font-mono text-xs font-medium sm:w-auto sm:gap-12 sm:text-sm"
            aria-label="Primary navigation"
          >
            <a
              className="flex items-center border-b-2 border-primary text-primary transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
              href="#architecture"
              aria-current="location"
            >
              Architecture
            </a>
            <a
              className="flex items-center border-b-2 border-transparent text-foreground transition-colors hover:border-border hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
              href={`${apiBaseUrl}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              API contract
            </a>
          </nav>
        </div>
      </header>

      <main className="flex-1" id="main-content" tabIndex={-1}>
        <section
          className="foundation-canvas mx-auto w-full max-w-[1600px] scroll-mt-4 px-6 sm:px-10 lg:px-14"
          aria-labelledby="foundation-title"
          id="architecture"
        >
          <div className="signal-line" aria-hidden="true" />

          <div className="hero-region">
            <div className="hero-copy">
              <h1
                className="max-w-[1000px] font-display text-[clamp(2.75rem,4.2vw,4.5rem)] leading-[1.02] font-semibold tracking-[-0.052em] text-balance text-foreground"
                id="foundation-title"
              >
                Three layers.
                <br />
                One demo-ready foundation.
              </h1>
              <p className="mt-7 max-w-[740px] font-mono text-[clamp(1rem,1.6vw,1.55rem)] leading-[1.6] text-muted-foreground text-pretty">
                A clean Next.js, FastAPI, and Python core baseline for the Yuno
                × Nauta hackathon.
              </p>

              <HealthExperience apiDocsUrl={`${apiBaseUrl}/docs`} />
            </div>
          </div>

          <ul className="architecture-list" aria-label="Application layers">
            {layers.map(({ label, technology, icon: Icon }) => (
              <li className="architecture-row" key={label}>
                <div className="architecture-layer">
                  <span className="layer-icon" aria-hidden="true">
                    <Icon strokeWidth={1.5} />
                  </span>
                  <span>{label}</span>
                  <span className="text-muted-foreground" aria-hidden="true">
                    /
                  </span>
                  <span translate="no">{technology}</span>
                </div>
                <span className="layer-marker" aria-hidden="true">
                  <span />
                </span>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="border-t border-border px-6 py-8 text-center font-mono text-xs tracking-[0.04em] text-muted-foreground sm:text-sm">
        Challenge logic intentionally left open.
      </footer>
    </div>
  );
}

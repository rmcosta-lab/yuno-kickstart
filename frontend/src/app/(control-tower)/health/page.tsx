import { CodeXml, PanelTop, Server } from "lucide-react";

import { HealthExperience } from "@/components/health-experience";

const layers = [
  { label: "Browser", technology: "Next.js", icon: PanelTop },
  { label: "API", technology: "FastAPI", icon: Server },
  { label: "Core", technology: "Python", icon: CodeXml },
] as const;

export default function HealthPage() {
  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  return (
    <section className="foundation-canvas" aria-labelledby="foundation-title">
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
          <p className="mt-7 max-w-[740px] font-mono text-[clamp(1rem,1.6vw,1.55rem)] leading-[1.6] text-pretty text-muted-foreground">
            A clean Next.js, FastAPI, and Python core baseline for the Yuno ×
            Nauta hackathon, relocated here from the original bootstrap homepage
            now that the control tower shell owns the root route.
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
  );
}

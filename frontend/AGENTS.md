<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Frontend engineering instructions

These rules specialize the repository instructions for `frontend/`. Preserve the root architecture and security boundaries.

## Frontend ownership and boundaries

The frontend owns presentation, browser state, forms, accessibility, and user interaction:

- Call only this repository's FastAPI BFF for application data through `NEXT_PUBLIC_API_BASE_URL`.
- Do not introduce Next.js Route Handlers or Server Actions as a second backend-for-frontend (BFF), and do not place business or payment rules in this package.
- Keep strict TypeScript enabled and avoid untyped provider payloads outside their integration boundary.

## Next.js rendering and component boundaries

Use the App Router and React Server Components (RSC) as the default rendering model:

- Keep pages, layouts, and non-interactive components as Server Components.
- Add `"use client"` only at the smallest component boundary that needs state, effects, event handlers, browser APIs, context, TanStack Query hooks, React Hook Form, or the Yuno Web SDK.
- Extract an interactive leaf instead of converting an entire page or layout into a Client Component.
- Do not declare an async Client Component. Pass only serializable props across the server-to-client boundary.
- Keep client providers as narrow and as deep in the tree as their consumers allow.

## UI composition and accessibility

Build interfaces from the configured shadcn/ui primitives and Tailwind CSS utilities:

- Check the configured shadcn registry before creating a replacement primitive. Review every generated file and dependency.
- Reuse design tokens and existing variants instead of adding isolated styling conventions.
- Use semantic HTML, associated form labels, keyboard access, visible focus states, and sufficient color contrast.
- Design loading, empty, error, disabled, processing, and success states for every asynchronous journey.
- Verify layouts at mobile and desktop widths. Prevent overflow, clipped controls, and touch targets that are difficult to activate.

## Remote state and forms

Separate server state from local interaction state:

- Use generated TanStack Query hooks for remote state in interactive Client Components. Model loading, errors, retries, invalidation, and stale data explicitly.
- Do not mirror query data into React context or local state without a concrete editing or synchronization need.
- Use React Hook Form with Zod schemas and the configured resolver for non-trivial forms.
- Keep transient presentation state local to the smallest component that owns it.

## OpenAPI and generated client

Treat `../api/openapi.json` as the source of truth for browser-to-server contracts:

- Generate `src/lib/api/generated/` through Orval with `pnpm api:generate` from `frontend/`.
- Never hand-copy Python data transfer objects, maintain parallel request or response types, or edit generated files.
- After an API contract change, regenerate the client before fixing consumers. Commit the contract and generated changes together when they belong to the same change.

## Yuno browser payment boundary

The official Yuno Web SDK is the only direct Yuno integration allowed in browser code. Keep its flow within this boundary:

1. Request a checkout session from this repository's FastAPI BFF.
2. Initialize and mount the Yuno Web SDK in a Client Component with the public API key and checkout session.
3. Let the SDK render or tokenize payment fields. Do not create a raw card collection form.
4. Send the one-time token from the SDK callback to the FastAPI BFF for server-side payment creation.
5. Continue or unmount the SDK according to the BFF result and the current Yuno Web SDK documentation.
6. Show the immediate result for user experience, but reconcile durable payment state through this repository's API.

Apply these payment-data rules:

- Only `NEXT_PUBLIC_YUNO_PUBLIC_API_KEY` may expose a Yuno credential to browser code.
- Never expose a private Yuno key, call a Yuno private API, or add a private secret under any `NEXT_PUBLIC_` name.
- Never collect, persist, inspect, or log a primary account number (PAN), card verification value (CVV), or full sensitive SDK payload.
- Treat a one-time token as ephemeral: pass it directly to the BFF, and never persist or log it.
- Treat the browser callback as transient user experience, not the durable source of payment truth.

## Validation and commands

Run these commands from `frontend/`; they are defined in `frontend/package.json`:

| Command             | Purpose                                                 |
| ------------------- | ------------------------------------------------------- |
| `pnpm dev`          | Start the development server for browser verification   |
| `pnpm build`        | Create the production build                             |
| `pnpm start`        | Serve an existing production build                      |
| `pnpm lint`         | Run ESLint with zero warnings allowed                   |
| `pnpm typecheck`    | Run TypeScript without emitting files                   |
| `pnpm api:generate` | Regenerate the Orval client from `../api/openapi.json`  |
| `pnpm format:check` | Check formatting without changing files                 |
| `pnpm format`       | Format this package; review the complete resulting diff |

For frontend code changes, run `pnpm lint`, `pnpm typecheck`, and `pnpm build`. Run `pnpm api:generate` first when the OpenAPI contract changed. The package currently has no automated `test` script, so do not report one as executed or add test dependencies without a concrete task.

For rendered changes, start `pnpm dev`, follow the verification order in Capability routing, and exercise the affected journey at mobile and desktop widths. Inspect keyboard and focus behavior, loading states, and error recovery. Prioritize behavioral coverage for checkout-session creation, Yuno SDK initialization, payment outcomes, and retry or error paths over broad snapshot suites.

## Capability routing

Follow the [development tooling guide](../docs/development-tooling.md) for setup and official MCP sources. Use only the capabilities whose trigger matches the task:

- **Playwright MCP:** exercise deterministic user journeys, forms, navigation, responsive states, and browser smoke or end-to-end checks.
- **Chrome DevTools MCP:** inspect the rendered DOM, console, network requests, runtime failures, screenshots, and performance traces after exercising the journey.
- **shadcn MCP:** search the configured registry and add existing primitives or blocks before hand-building replacements. Review every generated file and dependency.
- **Vercel MCP:** inspect current Vercel documentation, deployments, build/runtime logs, and domains when relevant. Keep deployment and configuration mutations within explicit scope.
- **Rendered verification order:** run the Playwright user flow first, then use Chrome DevTools to inspect console and network errors.

## Required skill routing

Use each skill when its trigger matches the task:

- `implement-frontend-phase` for an isolated frontend roadmap workstream.
- `vercel:nextjs` for App Router, Server Components, route organization, and Next.js architecture. Read the versioned local Next.js documentation required by the managed block first.
- `frontend-design` before defining or substantially changing the visual direction, and `frontend-app-builder` for a new application surface or major redesign.
- `react-best-practices` during React implementation. Reserve `vercel:react-best-practices` for a dedicated Vercel performance review instead of duplicating the same pass.
- `shadcn` or `vercel:shadcn` for current registry and composition guidance before hand-building a primitive.
- `frontend-testing-debugging` for rendered behavior and interaction debugging, then `web-design-guidelines` for accessibility, responsive behavior, and user experience review.
- `vercel:agent-browser-verify` for browser smoke verification and `vercel:verification` for the complete frontend-to-API-to-backend journey.

## Official references

- [Yuno SDK quickstart](https://docs.y.uno/docs/sdks/overview/quickstart)
- [Yuno Full Checkout Web Payments](https://docs.y.uno/docs/sdks/full-checkout/web-payments)

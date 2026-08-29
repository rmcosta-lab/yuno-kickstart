<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Frontend engineering instructions

- Keep pages and layout components server-rendered unless browser state requires a client boundary.
- Call only this repository's FastAPI API, except for browser-side Yuno SDK tokenization.
- Generate request, response, and TanStack Query types from `api/openapi.json`; never hand-copy API data transfer objects.
- Never expose Yuno private credentials through a `NEXT_PUBLIC_` variable.
- Prefer configured shadcn primitives and review every generated file before committing it.
- Run `pnpm api:generate`, `pnpm lint`, `pnpm typecheck`, and `pnpm build` after contract or rendered changes.
- Verify rendered changes in a browser at desktop and mobile sizes, including console and network health.

## Frontend scope

- Keep App Router pages and layouts as Server Components by default. Add client boundaries only for browser state, event handlers, providers, or generated TanStack Query hooks.
- Treat `../api/openapi.json` as the browser contract source of truth. Regenerate `src/lib/api/generated/` with `pnpm api:generate`; never hand-copy Python DTOs or edit generated files.
- Call only the FastAPI BFF through `NEXT_PUBLIC_API_BASE_URL`. Yuno private APIs and server secrets never belong in this package.
- Use TanStack Query for remote state, React Hook Form plus Zod for real forms, and shadcn/ui primitives before inventing replacements.
- Preserve strict TypeScript and verify changes with `pnpm lint`, `pnpm typecheck`, and `pnpm build`. Rendered changes also require a browser smoke test and console/network inspection.

# Frontend

Next.js App Router frontend for the Yuno × Nauta hackathon foundation.

## Commands

```bash
pnpm dev
pnpm api:generate
pnpm lint
pnpm typecheck
pnpm build
```

`pnpm api:generate` reads `../api/openapi.json` and replaces `src/lib/api/generated/`. Do not edit generated files manually.

The browser calls the FastAPI BFF at `NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8000`). No Yuno private credential belongs in this package.

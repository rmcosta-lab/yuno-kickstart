# Yuno × Nauta hackathon engineering instructions

> Repository-wide engineering instructions for Codex.
>
> **Objective:** ship a working, polished demo within the hackathon schedule while keeping the frontend, HTTP API, and backend/core clearly separated.

## Purpose and instruction routing

This file is the repository constitution. It applies to every path. Scoped `AGENTS.md` files add local conventions; they must not silently weaken the architecture, security rules, or cross-layer contracts defined here.

Before changing a scoped path, read its additional instructions even when the Codex session started at the repository root:

<!-- prettier-ignore -->
| Path | Required instructions | Primary ownership |
| --- | --- | --- |
| `frontend/**` | [`frontend/AGENTS.md`](frontend/AGENTS.md) | Rendering, browser state, forms, generated API client, Yuno Web SDK |
| `api/**` | [`api/AGENTS.md`](api/AGENTS.md) | HTTP contracts, validation, auth boundaries, errors, webhook ingress |
| `backend/**` | [`backend/AGENTS.md`](backend/AGENTS.md) | Domain rules, application services, persistence, Yuno server adapter |
| Cross-layer change | This file and every affected scoped file | End-to-end contract and integration |

For a cross-layer task, name one writer for each affected path and verify the complete journey. Deeper instruction files may specialize their own subtree without duplicating this entire file.

## Mission and decision order

Optimize decisions in this order:

1. A compelling vertical demo works end to end.
2. Payment data and credentials remain secure.
3. Contracts and ownership stay explicit.
4. Behavior is observable and testable.
5. Operational complexity remains low.

A smaller complete demo is better than a sophisticated incomplete platform.

## Architecture constitution

Build three logical application layers:

<!-- prettier-ignore -->
| Layer | Owns | Must not own |
| --- | --- | --- |
| Frontend | Presentation, browser state, forms, user interaction, public Yuno Web SDK flow | Business rules, private Yuno APIs, server credentials |
| API / backend for frontend (BFF) | FastAPI routes, Pydantic contracts, validation, auth boundaries, CORS, error translation, webhook ingress, dependency wiring | Pricing, payment strategy, domain transitions, database queries, provider payload mapping |
| Backend / Core | Plain-Python domain and application services, repositories, persistence, Yuno server integration, AI integration, external adapters | FastAPI or browser concerns |

The allowed dependency direction is:

```text
Browser / Next.js
        │ HTTPS / JSON through generated OpenAPI client
        ▼
FastAPI API / BFF
        │ typed Python calls
        ▼
Backend / Core ──> PostgreSQL/Supabase
        │
        └─────────> Yuno API ──> payment providers
```

The Yuno Web SDK is the sole payment-specific browser exception and may handle payment UI and tokenization with public configuration.

For the hackathon, the API may import the backend package directly. Do not add a network hop between them. Preserve the code boundary so it can be split later if a real need appears.

Hide external providers behind protocols and adapters. Keep deployment-specific code out of the domain. Avoid Kafka, Kubernetes, service mesh, event sourcing, Celery, extra microservices, or Redis unless the challenge demonstrates a concrete need. Create architecture folders only when their first real module exists.

## Sources of truth and cross-layer contracts

Use these canonical sources:

<!-- prettier-ignore -->
| Concern | Source of truth |
| --- | --- |
| Mission, stack, roadmap, challenge decisions | `docs/project-specs/` and accepted decision records |
| Browser/server contract | FastAPI Pydantic models and the generated `api/openapi.json` |
| TypeScript API access | Orval output under `frontend/src/lib/api/generated/` |
| Database schema | Versioned migrations |
| Configuration inventory | `.env.example`; never a committed `.env` |
| Yuno contracts and behavior | Current official Yuno documentation or official Yuno Model Context Protocol (MCP) schemas |
| Durable payment state | Verified webhooks and server-side reconciliation, not a browser callback |

Never hand-copy Python API data transfer objects into TypeScript and never edit generated API files. Version application routes under `/v1`.

When an API contract changes:

1. Update the Pydantic request or response model.
2. Update and run API tests.
3. Regenerate `api/openapi.json` and the Orval client with `make generate`.
4. Fix frontend type errors and consumers.
5. Run `make check` and verify the affected journey.

The frontend calls only this repository's API/BFF, except for the documented Yuno browser SDK flow. The API delegates application behavior to typed backend services. The backend keeps Yuno-specific URLs, headers, payloads, and responses inside its adapter.

## Yuno and payment invariants

Yuno changes over time. Never guess endpoint payloads, enum values, SDK methods, authentication behavior, webhook formats, or retry semantics.

Before implementing or changing a Yuno integration:

1. Prefer the official Yuno MCP `documentation.read` tool when available.
2. Start with the [official Yuno documentation index](https://docs.y.uno/llms.txt).
3. Read the relevant official reference linked by the scoped layer instructions.
4. Use machine-readable Markdown by appending `.md` to a Yuno Docs URL when useful.
5. Prefer official Yuno sources over memory, blogs, or old examples.

The Yuno MCP is a development tool, not a production dependency. Production code integrates through the official API or SDK behind the correct application boundary.

Use sandbox credentials until production is explicitly required. A payment, refund, cancellation, capture, database mutation, deployment, or other external state change must remain within the user's explicit task scope. Never perform an autonomous financial mutation because an MCP exposes the tool.

Payment mutations must be safe to retry. Generate and persist one idempotency key per logical operation, and reuse it when retrying an uncertain request. Do not create concurrent duplicate mutations for the same attempt.

For Yuno webhooks, preserve this boundary:

```text
API ingress: raw bytes -> HMAC verification -> JSON parsing -> typed delegation
Backend: deduplicate -> process -> persist -> reconcile
```

Do not assume webhook delivery order. Return success only according to the verified, durable processing contract defined by the current Yuno documentation.

## Global security rules

- Never store or log primary account numbers (PAN), card verification values (CVV), raw payment credentials, authentication headers, private keys, or full sensitive payloads.
- Never expose `YUNO_PRIVATE_SECRET_KEY`, `YUNO_WEBHOOK_HMAC_SECRET`, database administrative credentials, or `OPENAI_API_KEY` to the browser.
- Never create a `NEXT_PUBLIC_YUNO_PRIVATE_SECRET_KEY` or equivalent public alias for a server secret.
- Keep sandbox and production credentials separate. `.env` is gitignored and `.env.example` contains names or safe defaults only.
- Prefer Yuno Web SDK tokenization so sensitive payment data does not transit our backend.
- Use HTTPS outside local development, explicit CORS origins, inbound validation, verified webhook signatures, and redacted structured logs.
- Never commit `.env`, live credentials, service-role keys, database passwords, or tokens.
- Do not copy personal browser profiles, disable sandboxing, or embed credentials to work around remote-environment limitations.

## Engineering standards

- Python uses the configured Python 3.13 target, public type hints, Ruff, pytest, and small testable functions.
- TypeScript stays in strict mode. Prefer composition and local ownership over global state.
- Use Pydantic models for every HTTP request and response contract exposed by the API.
- Use structured logs with correlation/request IDs and redact sensitive data before emission.
- Add a dependency only when it removes more complexity than it introduces.
- Prefer deterministic code and structured outputs before adding agents, tool loops, or handoffs. Add AI only when the challenge benefits from it.
- Do not silently change an architecture convention. Record a justified exception in `docs/decisions/`.

Layer-specific stack choices, implementation conventions, commands, tests, skills, and official references belong in the corresponding scoped `AGENTS.md`.

## Codex tooling and source routing

Use official, current, task-relevant MCP servers, skills, and plugins. They support development but do not replace application dependencies, generated clients, tests, migrations, or production integrations.

Before a task that needs GitHub, browser validation, UI components, Supabase, Vercel, or Yuno, confirm the required capability in the environment that will execute it. Follow [`docs/development-tooling.md`](docs/development-tooling.md) for discovery, installation, project-scoped configuration, authentication, remote environments, and smoke tests.

If setup requires a shared or machine-global change, an interactive login, or OAuth, tell the user and request approval or participation. Never install a similarly named unofficial package. Keep mutating tools approval-gated and within the explicit task.

Route documentation lookups as follows:

- Yuno: official Yuno MCP and Yuno Docs first.
- OpenAI or Codex: the `openai-docs` skill and official OpenAI sources first.
- Other libraries, frameworks, SDKs, APIs, CLIs, and cloud services: use `context7-mcp` when its current documentation lookup matches the task; otherwise use the provider's official documentation.

Use `.agents/skills` as the only repository-scoped skill source. Do not create `.claude/skills` or duplicate the same physical skill in multiple directories. Preserve existing project-authored skills and managed package symlinks. Use `uvx library-skills --check` to validate managed symlinks without changing them; do not pass `--claude`.

Before starting implementation, confirm the exact task-relevant skill identifiers with `/skills`; inspect `.agents/skills` when necessary. If a required skill or plugin is missing, use the development tooling guide, restart Codex, and confirm it before continuing. Repeat discovery in remote and ephemeral environments.

## Roadmap and phase coordination

Once shared specifications have been initialized, treat `docs/project-specs/roadmap.md` as a lightweight dependency graph. Every `### Fase NN — Nome` section declares `Slug:`, `Depends on:`, `Conflicts with:`, and `Gate:`. Use `none` for empty lists, require lowercase kebab-case slugs, and do not infer dependencies from phase numbers.

Use these project workflow skills when their trigger matches:

<!-- prettier-ignore -->
| Skill | Responsibility |
| --- | --- |
| `manage-shared-specs` | Initialize or update global mission, stack, roadmap, or challenge decisions |
| `start-phase` | Claim an eligible phase and write its specification without implementing it |
| `implement-phase` | Coordinate a complete phase across affected layers |
| `implement-frontend-phase` | Implement an isolated frontend workstream |
| `implement-api-phase` | Implement an isolated API/BFF workstream |
| `implement-backend-phase` | Implement an isolated backend/core workstream |
| `deep-review` | Run an explicitly requested read-only review; only a merge verdict is tied to a published SHA |
| `finish-phase` | Submit or reconcile a verified phase through its pull request; never deploy |
| `changelog` | Prepare release notes from merged phase pull requests |

Use ordinary GitHub branches and pull requests as the coordination mechanism:

- One remote branch `phase/NN-{slug}` indicates that a phase is being worked on.
- At most one pull request from that branch may be open for review. Preserve closed pull-request history; a phase is done only when its required validation is recorded and a pull request is merged.
- An Issue `[Fase NN] Nome` may record the owner and notes, but it is not a lock or prerequisite when Issues are unavailable.
- Dependencies must be done, with their required validation recorded and pull requests merged, before a dependent phase starts.
- Phases that declare a conflict must not run concurrently.

Before starting or publishing work, refresh remote branch and pull-request state. Publish the planning commit as a new phase ref with an operation that fails when the branch exists, so the first remote commit includes the owner and phase requirements. If another developer created it first, coordinate instead of overwriting it. Use an optional Issue for convenient assignment. Do not use coordination mutexes, attempt UUIDs, synthetic lifecycle records, force-pushes, or repository-wide locks.

After publishing a claim, refresh declared conflicts once more before implementation. If two conflicting phases were claimed concurrently, both stop; the owners choose which phase proceeds, and the other planning-only claim remains untouched until its owner explicitly releases it. Do not resolve that collision by force-push or by deleting uninspected work.

Frontend, API, and backend work may run in parallel when one writer owns each path. Separate phases may run in parallel when dependencies and conflicts allow it. When pull requests touch the same shared file, communicate, merge one first, and refresh the other before publication.

Global specifications are living documents. A phase may update `tech-stack.md`, `roadmap.md`, `mission.md`, or `challenge-plan.md` in its pull request when the change is directly required only by that phase and nothing else must depend on it before that pull request merges. Record the reason and impact in the phase plan and pull-request body, notify affected owners, and keep one writer per shared file. Use `manage-shared-specs` and a short-lived `docs/specs-{topic}` branch for broader work, a decision another active phase needs, or a supporting phase that must enter the roadmap before the current phase can finish.

Do not silently rename, remove, or weaken the gate of an active or merged phase. Clarify it only with an explicit team decision. When new work must merge before an active phase resumes, add the supporting prerequisite through a dedicated specs pull request based on the remote default branch, then record the temporary wait in the active phase plan or Issue. Use a follow-up phase when the original outcome or gate is no longer valid. Future unstarted phases may be reorganized if the graph remains valid. Keep mutable status, assignees, branch names, and completion markers out of the roadmap.

An urgent shared decision does not require all phases to finish. Pause only affected integration work and require approval from the user, designated team lead, or all affected phase owners. Publish the small specification decision, let affected branches refresh, and continue. Record a temporary wait in an active phase plan or Issue when a new prerequisite must merge first.

## Working method

Before editing:

1. Read this file and every scoped `AGENTS.md` for affected paths.
2. Inspect the existing repository and current worktree; preserve unrelated user changes.
3. Read the relevant specifications and decision records.
4. Confirm task-relevant skills, plugins, MCPs, and official documentation.
5. If touching Yuno, inspect its current official schema before implementation.
6. Make the smallest coherent change that completes the requested vertical slice.

After editing:

1. Run the checks proportional to the changed paths and risk.
2. Regenerate committed contracts or artifacts when their source changes.
3. Browser-test rendered frontend changes and inspect console, network, and runtime errors.
4. Review the diff, including generated files and new dependencies.
5. Confirm that no secret, sensitive log, or unrelated change was introduced.
6. Update documentation only when behavior, architecture, setup, or an accepted decision changed.

When the hackathon challenge is first announced, use `manage-shared-specs` to define `docs/decisions/challenge-plan.md` before implementation. Capture the problem, target user, value proposition, demo journey, P0 scope, non-goals, required Yuno and AI capabilities, data and API changes, main risks, and fallback plan.

## Verification matrix

Run commands from the repository root unless scoped instructions say otherwise:

<!-- prettier-ignore -->
| Change | Required verification |
| --- | --- |
| Python/API/backend | `make python-check` |
| Frontend | `make frontend-check` |
| Cross-layer | `make check` plus the end-to-end journey |
| API contract | API tests, `make generate`, then frontend typecheck/build |
| Rendered UI | Browser smoke test plus console and network inspection |
| Yuno integration | Current official docs/schema, unit tests with mocks, and separately marked sandbox tests when credentials and scope allow |
| Database schema/query | Migration review, tests, and Supabase security/performance advisors when Supabase is used |
| Documentation only | Link/fence review and `git diff --check`; code tests only when documented behavior changed |

Scoped commands are focused iteration checks. Before handoff, use the applicable root target in this matrix unless the change is documentation-only or a narrower check is explicitly justified and reported.

At minimum, inspect `git diff` and run `git diff --check` before handoff. Report skipped checks and unavailable credentials or external dependencies explicitly.

## Documentation map and official references

- [`README.md`](README.md): bootstrap, local services, generated contracts, and team workflow.
- [`docs/architecture.md`](docs/architecture.md): request flow, ownership, contract generation, and provider isolation.
- [`docs/api.md`](docs/api.md): running the API, adding endpoints, generating clients, and webhook overview.
- [`docs/development-tooling.md`](docs/development-tooling.md): MCP, skill, plugin, authentication, and remote-environment setup tutorials.
- `docs/project-specs/`: mission, accepted technology choices, and phase dependency graph after initialization.
- [`docs/decisions/challenge-plan.md`](docs/decisions/challenge-plan.md): current challenge scope and demo plan.
- [OpenAI's official `AGENTS.md` guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md): instruction discovery and precedence.
- [Yuno AI integrations and MCP](https://docs.y.uno/docs/ai-capabilities/building-ai-integrations-with-yunos-llms-and-mcp): official development-tool integration.

Layer-specific official references live in the corresponding scoped `AGENTS.md`; do not recreate a repository-wide link catalog here.

## Hackathon prioritization

- **P0: vertical demo:** one compelling journey, real frontend, typed API contract, backend service, Yuno sandbox integration when possible, required persistence, and webhook handling when state is asynchronous.
- **P1: polish:** loading and error states, observability, graceful fallback, visual quality, architecture explanation, and demo instructions.
- **P2: sophistication:** AI agents, Redis, background work, analytics, extra payment paths, and advanced optimization only after P0 works.

When in doubt, optimize for:

```text
working demo
> secure payment integration
> clean contract
> observable behavior
> low-complexity architecture
> clever architecture
```

Keep each layer understandable enough that another team member or Codex worktree can change it without loading the entire application into context.

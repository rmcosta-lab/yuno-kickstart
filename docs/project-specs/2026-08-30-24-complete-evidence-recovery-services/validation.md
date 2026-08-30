# Fase 24 — Validation

## Backend quality

- [ ] `cd backend && uv run ruff check .`
- [ ] `cd backend && uv run pytest`
- [ ] `make python-check`
- [ ] `git diff --check`

## Application contracts

- [ ] Public recovery commands, models, services, repositories, results, exceptions, and exports match `requirements.md` and remain independent of FastAPI, Pydantic, SQLAlchemy sessions, and provider payloads.
- [ ] Mandate replacement creates immutable version `current + 1`, activates it, resolves only the named same-operation escalation, advances operation state once, and emits safe coordinator audit events.
- [ ] Missing, foreign, resolved, stale, or invalid mandate-replacement input rolls back without changing durable state.
- [ ] Explicit escalation round-trips bounded structured context and changes no commitment.
- [ ] Notification acknowledgement records the first actor and aware UTC timestamp; identical retries are read-only replays and a different actor cannot overwrite them.

## PostgreSQL and migration

- [ ] Focused tests run with `TEST_DATABASE_URL` against PostgreSQL.
- [ ] Alembic upgrade, downgrade, and re-upgrade succeed.
- [ ] Old and new mandate rows round-trip, with only the new mandate referenced as active.
- [ ] Escalation context and notification decision/acknowledgement fields round-trip identically.
- [ ] Constraints reject partial acknowledgement state, invalid relationships, unsafe bounds, and more than one unresolved escalation per operation.
- [ ] Injected failures and stale-version races preserve the previous active mandate, escalation, notification, operation version, commitment history, and audit trail.

## Security and scope

- [ ] Audit metadata is event-allowlisted and contains no raw conflict text, attempted-alternative text, recording reference, transcript, contact data, provider payload, or secret.
- [ ] Exceptions and logs expose only safe codes, identifiers, versions, and normalized state.
- [ ] No FastAPI or Pydantic import appears in backend domain/application modules.
- [ ] No `api/**`, `frontend/**`, `api/openapi.json`, generated-client, provider, deployment, manifest, lockfile, shared-spec, or unrelated file changed.
- [ ] Full diff review finds no credentials, personal data, remote mutation, or unsupported behavior claim.

## Not applicable

- OpenAPI/Orval generation and API route tests: no HTTP contract change.
- Frontend lint/build and browser smoke tests: no frontend change.
- Yuno, OpenAI, Twilio, webhook, or credentialed sandbox tests: no provider integration.
- Supabase advisors: the phase uses the existing local PostgreSQL/SQLAlchemy boundary and adds no Supabase-specific configuration.

## Final gate evidence

- [ ] Record exact command outputs and pass/skip counts.
- [ ] Record the focused PostgreSQL command and migration evidence.
- [ ] Record any approved deviation, fallback activation, or unavailable external dependency.

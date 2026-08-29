# Work with the HTTP API

FastAPI exposes this Hypertext Transfer Protocol (HTTP) application programming interface (API). The bootstrap includes an unversioned health check and reserves `/v1` for application contracts. Its OpenAPI document generates the frontend client, so contract changes start in Pydantic and never in generated TypeScript files.

## Run and inspect the API

Start the development server from the repository root:

```bash
make dev-api
```

Inspect the service at these local addresses:

- Health check: `http://localhost:8000/health`
- Interactive documentation: `http://localhost:8000/docs`
- OpenAPI document: `http://localhost:8000/openapi.json`

## Use the current endpoint

The bootstrap exposes one health endpoint:

| Method | Path | Response | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | `{"status":"ok"}` | Confirms that the API process can serve requests |

The health route contains no database or provider check. Add dependency health only when the demo needs that distinction.

## Regenerate the frontend client

Update browser contracts in this order:

1. Change the Pydantic request or response model
2. Add or update API tests
3. Run `make generate`
4. Fix frontend type errors
5. Run `make check`

`api/openapi.json` is the serialized contract. Orval reads it and writes the generated client under `frontend/src/lib/api/generated/`. Never edit generated files by hand.

## Add an application endpoint

Add new application routes under `/v1`. Keep routers limited to transport work:

- Parse and validate input with Pydantic
- Resolve authentication and dependencies
- Call a typed backend application service
- Translate domain or integration errors into HTTP responses
- Return a declared response model

Place pricing, payment strategy, state transitions, database queries, and provider payload translation in `backend/`.

## Handle payment webhooks safely

When a Yuno webhook route is added, verify its signature before parsing JavaScript Object Notation (JSON). Read the raw request bytes, verify the Base64 hash-based message authentication code (HMAC) with SHA-256 from `x-hmac-signature`, deduplicate the event, then return HTTP 200 after durable processing.

The bootstrap includes the verification utility and tests, but it does not expose a webhook route until a challenge phase defines the event contract.

# API/BFF engineering instructions

- Keep FastAPI routers thin: validate HTTP contracts, enforce transport security, call backend services, and translate errors.
- Do not place pricing, payment strategy, domain transitions, or provider-specific rules here.
- Define every public request and response with typed Pydantic contracts and stable operation IDs.
- Read Yuno webhook request bytes before JSON parsing and verify `x-hmac-signature` before delegation.
- Never log secrets, authorization headers, card data, or full sensitive payloads.
- After a contract change, run API tests and regenerate `api/openapi.json` before regenerating the frontend client.
- Run `uv run ruff check api` and `uv run pytest api/tests` after changes.

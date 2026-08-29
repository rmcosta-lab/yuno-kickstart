# Backend/Core engineering instructions

- Keep this package independent of FastAPI and other transport frameworks.
- Put business rules and provider-neutral application contracts here.
- Hide Yuno, database, and other external details behind typed adapters.
- Use `Decimal` for money and never collect, persist, or log PAN or CVV.
- Keep secrets out of representations, exceptions, and structured logs.
- Confirm endpoint paths, payloads, enums, and webhook formats against current official Yuno documentation before implementing provider calls.
- Run `uv run ruff check backend` and `uv run pytest backend/tests` after changes.

# Serve private demo evidence through the authenticated BFF

Status: accepted for Fase 16 on 2026-08-30.

## Context

The accepted Fase 16 gate requires the browser to play an agreement turn at the persisted
`audio_start_ms`. The current contract exposes `recording_reference`, but Fase 14 deliberately
defines that value as an opaque private-storage pointer. It is not a URL, and exposing or
interpreting it in the browser would violate the storage and security boundary.

## Decision

- Add `GET /v1/evidence/{evidence_id}/audio` behind the existing demo bearer authorization.
- Resolve `evidence_id` to private bytes through a provider-neutral backend application service
  and `EvidenceStorage.retrieve`; never accept or return `recording_reference` at this route.
- Remove `recording_reference` from browser-facing evidence response DTOs. The value remains in the
  backend evidence model and persistence projection only; compatibility checks must confirm no
  current frontend consumer reads it before OpenAPI/Orval regeneration.
- Close the persistence unit of work before awaiting storage retrieval. No database transaction
  remains open while reading the artifact.
- Support only RIFF/WAVE demo evidence with a 25 MiB response-acceptance cap. The existing trusted
  P0 storage port returns bytes eagerly, so this cap rejects the response after retrieval rather
  than claiming to bound adapter read-time memory. Return a safe not-found response when the
  evidence is absent or not playable and a safe payload-too-large response above the cap.
- Return `200 audio/wav` with `Cache-Control: private, no-store`, `Pragma: no-cache`,
  `X-Content-Type-Options: nosniff`, and no filename, storage path, or provider metadata.
- Fetch the bytes through the generated authenticated client, create a browser Blob URL, seek to
  `audio_start_ms / 1000` after metadata loads, and revoke the URL when it is replaced or unmounted.
- Update the shared generated-client fetch mutator to preserve `audio/*` successes as `Blob` while
  retaining JSON parsing for typed error responses; never decode audio through `Response.text()`.
- Do not add public or signed object-storage URLs, Range support, a storage provider, deployment,
  or production recording behavior in this phase.

The binary success body is a deliberate narrow exception to the repository's JSON/Pydantic
response convention. FastAPI remains the OpenAPI source of truth: the operation declares its
`audio/wav` binary schema and every error remains a typed Pydantic `ApiErrorResponse`. Orval
generates the browser client from that contract.

## Consequences

- Private audio remains behind the BFF and existing authorization boundary.
- Existing JSON responses stop disclosing private storage topology through an opaque reference.
- The browser can satisfy the observable offset gate without learning filesystem structure or
  storing audio durably.
- The P0 implementation downloads the bounded artifact before playback; byte-range streaming and
  provider-backed expiring delivery remain future work if real recording sizes require them.
- Missing or invalid audio is shown honestly as unavailable, with the evidence metadata and text
  audit still visible. It is never represented as successful playback.
- A transient `blob:` source may exist only on the in-memory audio element. It is not copied into
  visible text, logs, history, persistent browser storage, screenshots, or retained after teardown.
- Audio uses the generated imperative fetch function rather than a TanStack Query cache, so raw
  Blob data is released with the revoked URL and cleared component reference.

## Alternatives rejected

- Treating `recording_reference` as a URL: it is explicitly opaque and may contain a private path.
- Serving an ignored frontend static asset: it bypasses authorization and disconnects playback
  from durable evidence identity.
- Adding signed object-storage delivery now: no production storage provider has been selected, and
  the added credential and expiry machinery does not advance the P0 gate.

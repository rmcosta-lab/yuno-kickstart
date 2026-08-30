# Present Volta in five minutes

This deck explains Volta’s demonstrated browser journey, its bounded authority, and the unproved telephony work. Slides 1 through 8 form a 4:50 core. The final two slides are optional discussion material.

## Slide 1: Turn transport calls into auditable operations, 0:00 to 0:25

Ground transport coordination depends on calls whose quotes and changes rarely become structured operation data. Volta helps a coordinator compare synthetic carrier negotiations, enforce an approved mandate, and audit every resulting decision.

> Speaker cue: “Volta turns a transport request into one mandate-safe, auditable commitment. Today’s proof uses synthetic carriers and no real booking.”

Evidence: [project mission](../project-specs/mission.md#ground-transport-coordination-problem) and [challenge decision](../decisions/challenge-plan.md#problem-to-solve).

## Slide 2: The coordinator grants bounded authority, 0:25 to 0:55

The canonical synthetic request is Manzanillo to Guadalajara, Thursday pickup, and a maximum of MXN 9,000. Volta extracts a draft, but only explicit coordinator approval creates an immutable mandate.

> Speaker cue: “Artificial intelligence interprets the request. Deterministic rules enforce price, currency, date, conditions, and mandate version.”

Evidence: [canonical scenario](../decisions/challenge-plan.md#canonical-scenario) and [accepted browser journey](../project-specs/2026-08-30-17-pass-browser-trial/validation.md#canonical-browser-journey).

## Slide 3: Deterministic selection makes the decision inspectable, 0:55 to 1:25

Fixed rules select three eligible synthetic carriers: Puerto Azul Drayage, Ruta Norte Intermodal de Occidente, and Altamar Logistica Portuaria del Pacifico. Volta rejects an above-cap quote and compares only eligible options.

> Speaker cue: “The model does not choose the winner. The same approved mandate and deterministic ranking produce the same eligible set.”

Evidence: [synthetic catalog](../../backend/src/yuno_backend/volta/text_slice/demo.py) and [deterministic browser evidence](../project-specs/2026-08-30-17-pass-browser-trial/validation.md#deterministic-browser-and-repair-evidence).

## Slide 4: One winner remains active, 1:25 to 2:10

The control tower retains quotes, rejections, and the selected result. Exactly one evidence-backed `CANDIDATE` is `ACTIVE`; a later replacement marks the earlier commitment `SUPERSEDED` without erasing it.

> Speaker cue: “Evidence lifecycle and operational disposition answer different questions. `CANDIDATE` describes proof. `ACTIVE` identifies the current operational choice.”

Evidence: [commitment states](../decisions/challenge-plan.md#commitment-states) and [operation reload evidence](../project-specs/2026-08-30-17-pass-browser-trial/validation.md#canonical-browser-journey).

## Slide 5: Evidence remains private and honest, 2:10 to 2:45

The winner links to authenticated private audio at the agreeing turn, plus a structured brief and a recap labeled `SIMULATED`. Volta does not claim external delivery, a real booking, or `VERIFIED` evidence.

> Speaker cue: “The recording stays outside Git. The interface requests bounded audio through FastAPI and keeps the recap usable when playback fails.”

Evidence: [audio and fallback validation](../project-specs/2026-08-30-17-pass-browser-trial/validation.md#evidence-audio-and-fallback-recording) and [data model decision](../decisions/challenge-plan.md#data-model-changes).

## Slide 6: Recovery preserves authority, 2:45 to 3:25

A mandate-safe disruption can atomically replace the winner and notify the coordinator. An out-of-mandate request preserves the active commitment and creates a human escalation. Veracruz to Puebla separately demonstrates the no-eligible-carrier path before any session starts.

> Speaker cue: “Volta can act only inside the mandate. When authority ends, automation stops and the audit explains why.”

Evidence: [recovery validation](../project-specs/2026-08-30-17-pass-browser-trial/validation.md#required-failure-and-recovery-matrix) and [canonical no-eligible test](../../frontend/tests/e2e/complete-browser-trial.spec.ts).

## Slide 7: One core serves browser and phone channels, 3:25 to 4:05

Next.js uses generated Hypertext Transfer Protocol (HTTP) contracts through FastAPI. Browser voice uses a scoped Web Real-Time Communication (WebRTC) credential. The implemented Twilio Media Streams bridge enters through FastAPI and delegates to the same plain-Python rules.

> Speaker cue: “Channels carry conversation. They do not grant authority or select a winner.”

Evidence: [architecture guide](../architecture.md) and [Twilio bridge validation](../project-specs/2026-08-30-19-bridge-twilio-media/validation.md#media-websocket-and-realtime-bridge).

## Slide 8: Show the proof and the gaps, 4:05 to 4:50

The deterministic browser and text journey is demonstrated. The owner accepted Phase 17 with an explicit Realtime waiver because qualitative voice checks and the complete two-tool provider roundtrip remain unchecked. The consent-gated outbound control passed credential-free UI tests, and the Twilio bridge is implemented, but no authorized sandbox call proved the complete live path. Three overlapping public switched telephone network calls, inbound recovery, and live human takeover remain final-trial outcomes.

> Speaker cue: “Our claim is bounded: the operational logic is reproducible. Live telephony outcomes remain unproved until the authorized final trial records them.”

Evidence: [Phase 17 waiver](../project-specs/2026-08-30-17-pass-browser-trial/validation.md#final-commands-and-review), [Phase 19 sandbox gap](../project-specs/2026-08-30-19-bridge-twilio-media/validation.md#authorized-sandbox-evidence), [Phase 20 control evidence](../project-specs/2026-08-30-20-add-outbound-call-controls/validation.md#focused-and-deterministic-checks), and [Phase 21 truth table](../project-specs/2026-08-30-21-prepare-public-submission/plan.md#implementation-ownership-and-frozen-public-claims).

## Optional slide 9: Inspect the architecture boundaries

Use this slide only for technical questions. FastAPI owns transport validation and provider ingress. The plain-Python core owns mandate checks, ranking, commitment transitions, persistence, and audit. PostgreSQL stores structured state, while audio stays in private storage outside Git.

> Speaker cue: Open the [architecture guide](../architecture.md) and trace one typed action from the browser to the core.

## Optional slide 10: Reproduce the deterministic proof

The public guide documents setup and validation without provider credentials. The [timed demo script](demo-script.md) defines live and fallback branches. The [recorded fallback guide](recorded-fallback.md) keeps private access and deletion responsibilities out of Git.

> Speaker cue: “Reviewers can reproduce the deterministic journey without interpreting a private provider result as proof.”

# Run the five-minute Volta demo

This script gives the operator a 4:50 core run with explicit stop and fallback decisions. It demonstrates only synthetic browser behavior. It does not prove a public switched telephone network (PSTN) call or a real carrier booking.

## Complete the preflight

Finish this checklist before the audience enters:

- Confirm the checkout, local database, frontend, and FastAPI process match the [public setup guide](../../README.md)
- Use a fresh synthetic operation and the canonical Manzanillo to Guadalajara prompt
- Confirm the Thursday pickup and MXN 9,000 mandate render correctly
- Confirm three synthetic carriers appear after deterministic selection
- Confirm the Evidence, Recovery, Escalation, and Audit views load
- Test private audio playback without exposing its storage reference
- Keep text fallback ready and obtain out-of-band access to the private recording
- Close consoles, terminals, provider dashboards, environment files, and unrelated browser tabs
- Start a visible timer and keep [the presentation](presentation.md) open in a separate window

Stop before the live run if any screen exposes a credential, authorization value, private path, phone number, participant detail, or raw provider payload. Switch to the private recording only after closing the exposed surface.

## Run the core journey

| Time | Operator action | Expected visible result | Spoken point |
| --- | --- | --- | --- |
| 0:00 to 0:25 | Open **Intake** and show the canonical synthetic prompt. | The route reads Manzanillo to Guadalajara, pickup is Thursday, and the cap is MXN 9,000. | Volta begins with a natural-language request, but the prompt grants no authority. |
| 0:25 to 0:50 | Open **Mandate review** and approve only if the prepared values match. | An approved immutable mandate version appears with the route, date, currency, cap, and allowed conditions. | The coordinator grants bounded authority. Deterministic rules enforce it. |
| 0:50 to 1:20 | Open **Carrier sessions** and start server selection. | Three synthetic carriers appear in fixed rank order. | The model does not select carriers. Route coverage, availability, and fixed priority do. |
| 1:20 to 1:55 | Open **Comparison**. Show one above-cap rejection and the eligible alternatives. | The rejected MXN 9,500 quote has mandate reasons. Eligible quotes remain comparable. | Invalid terms cannot become a commitment. |
| 1:55 to 2:25 | Show the selected commitment. | Exactly one evidence-backed `CANDIDATE` is `ACTIVE`. | `CANDIDATE` describes evidence; `ACTIVE` identifies the current winner. Neither means a real booking. |
| 2:25 to 2:55 | Open **Evidence** and load the prepared private audio. | Playback starts at the stored turn offset. A structured brief and a recap labeled `SIMULATED` remain visible. | The timestamp is turn-level evidence. The recap was not sent externally and is not `VERIFIED`. |
| 2:55 to 3:30 | Open **Recovery** and run the mandate-safe simulation. | A replacement becomes active, the earlier commitment becomes `SUPERSEDED`, and a notification appears. | Volta changes the winner atomically only inside the approved mandate. |
| 3:30 to 4:00 | Run the out-of-mandate simulation, then open **Escalation**. | The active commitment stays unchanged and an open human escalation explains the conflict and attempted alternatives. | When authority ends, automation stops. |
| 4:00 to 4:25 | Open **Audit trail**. | Quotes, evidence, recap, brief, replacement, notification, and escalation appear in ordered history. | The durable record explains both action and refusal. |
| 4:25 to 4:50 | Show the status statement on [slide 8](presentation.md#slide-8-show-the-proof-and-the-gaps-405-to-450). | The audience sees demonstrated, waived, implemented, and final-trial states separately. | Browser and text are demonstrated. The outbound control passed credential-free UI checks, but Twilio lacks live proof. Overlapping PSTN, inbound recovery, and handoff remain final-trial outcomes. |

## Use the browser fallback branch

Switch branches at the first failed prerequisite:

1. If microphone permission or OpenAI Realtime fails, select **Use text fallback** and continue the same deterministic core journey.
2. If private evidence playback fails, state that audio is unavailable. Keep the recap and brief visible, then continue to Recovery.
3. If one prepared page fails to load, retry once. Stop the live browser run if the retry fails.
4. If state becomes ambiguous, do not create another mutation. Stop the run and switch to the private recording.

Say: “The live channel is unavailable, so I am switching to the deterministic fallback. This does not count as live provider evidence.”

## Use the telephony branch only after final-trial proof

Do not improvise a PSTN call. Show a live telephony segment only when the authorized final-trial operator confirms all required evidence for that exact run.

If that confirmation exists, replace the browser transport segment without changing the mandate, winner, recap, evidence, or gap language. If it does not exist, keep slide 8 unchanged and state that the Twilio bridge is implemented but not live-proven.

Stop any telephony segment immediately if consent, allowlisting, call state, or participant identity differs from the approved rehearsal. Return to text mode and preserve the failure as an unproved outcome.

## Switch to the private recording

Use the [recorded fallback procedure](recorded-fallback.md) when the browser cannot reach a trustworthy terminal state within 15s. Announce the switch, play the bounded recording, and resume at the matching timestamp in this script.

Never call the recording a live run, a PSTN call, or final-trial evidence. After playback, return to slide 8 and report the unavailable channel.

## Close the demo

Stop all playback and browser voice. Close the demo tab, verify that no microphone indicator remains active, and tell the access custodian whether the fallback was played. Do not retain new screenshots, traces, recordings, transcripts, or exported browser data.

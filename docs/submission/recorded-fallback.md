# Play and retire the private fallback safely

This guide lets an authorized operator play the existing synthetic fallback without publishing its location or metadata. The recording supports the deterministic browser story. It is not live provider, public switched telephone network (PSTN), or final-trial evidence.

## Confirm roles out of band

Assign these roles in the approved private team channel before rehearsal:

- **Access custodian**: verifies the operator and grants time-bounded playback access
- **Demo operator**: plays the recording and reports only bounded results
- **Deletion owner**: applies the agreed retention decision and confirms deletion

Do not record names, contact details, access links, object identifiers, filesystem paths, passwords, or storage-provider details in Git, chat screenshots, tickets, or presentation notes.

## Obtain access

Follow this sequence:

1. Ask the access custodian for access through the approved out-of-band channel.
2. Confirm your operator role and the scheduled rehearsal or presentation.
3. Accept the minimum time-bounded permission needed for playback.
4. Do not forward, bookmark, synchronize, download, or copy the access locator.
5. Stop if the artifact requests a repository credential, provider credential, or participant detail.

## Check playback before the demo

Use an approved local player or access-controlled browser window. Keep all storage navigation and private metadata outside screen sharing.

Confirm only these outcomes:

- Playback starts from the first frame and reaches the terminal browser state
- The recording shows synthetic Volta interface content only
- The mandate, one active result, `SIMULATED` recap, recovery, escalation, and audit story match the [timed script](demo-script.md)
- No credential, authorization value, private locator, phone number, participant identity, transcript, or provider payload appears
- Audio output and screen sharing reveal only the intended recording area

Record the check as `PASS` or `BLOCKED`. You may record the duration bucket, access-custodian role, and deletion-owner role. Do not record the exact media size, checksum, codec metadata, creation time, access time, filename, or location.

## Play during the demo

Announce: “The live browser path is unavailable. This private recording shows the accepted deterministic browser journey and does not count as live telephony evidence.”

Then complete these actions:

1. Share only the player window.
2. Start from the first frame.
3. Stop if unrelated content or private metadata appears.
4. Resume the [demo script](demo-script.md) at the matching segment.
5. End on the status statement that separates demonstrated browser behavior from unproved telephony outcomes.

Do not scrub through storage, show player information panels, or expose recent-file menus. Do not send the recording to a judge or publish it with the repository.

## End access after playback

After the demo:

1. Stop playback and screen sharing.
2. Close the player and revoke temporary access.
3. Clear only application-level recent-item history when the approved player supports it. Do not use destructive system-wide cleanup.
4. Tell the access custodian whether playback completed or was blocked.
5. Confirm that no local copy, screenshot, transcript, browser export, or new recording remains.

## Apply retention and deletion

The deletion owner keeps the recording only through the retention event agreed out of band. The event must be one of: submission completion, review completion, or an approved extension with a new deletion date.

At the retention event, the deletion owner must revoke access, delete the recording from its private store, and remove recoverable copies under the same approved retention policy. The access custodian then confirms that shared access no longer works.

Record only `RETAINED UNTIL AGREED EVENT`, `DELETED`, or `BLOCKED`, plus the responsible role and confirmation date. If deletion is blocked, restrict access immediately, record the blocker without locator details, and escalate through the approved private channel.

## Reproduce instead of recovering a deleted copy

Do not restore deleted media for convenience. If a later authorized demo needs a new fallback, reproduce it from a fresh isolated database and synthetic operation under a separate recording authorization. Keep the new artifact outside Git and repeat this access, playback, retention, and deletion process.

The accepted handling evidence is recorded in [Phase 17 validation](../project-specs/2026-08-30-17-pass-browser-trial/validation.md#private-fallback-recording-and-cleanup).

# Work C — real HTTP media identity on b838540

Source: `b8385407425ea8f8c05de044b1c1a8728cdd5eab`.

## What changed

Closed the previously unexecuted **real localhost HTTP byte/PCM identity** edge for retained 10.5-second R1/R2 media. No new render or music measurement was performed. This is not the separate fresh 50.5-second pair already measured in this PR.

The probe commits the retained fixture SongSpecs into one fresh project, submits their already-retained WAVs through the existing R3 render publication API, and retrieves them using the unmodified session/capability-protected POST `/api/projects/audio`. It never inserts objects directly into CAS or patches authorization. This is retained-media delivery qualification, not proof that Generate rendered these bytes in a browser.

Eight successful WAV responses: R1/R2 × desktop/phone User-Agent headers × before/after server restart. Every response equals the authoritative CAS file byte for byte, hashes to the bound artifact, and independently FFmpeg-decodes to the canonical PCM. Python wave and FFmpeg PCM match. Each revision has one binding; R2 stays current. The restart uses a new server process and new sessions against the same durable state.

Eight negative checks: wrong-revision artifact and missing session, across both client labels and both server lifetimes, return HTTP 403 with no WAV.

## Evidence ceiling

- AUDIO_VALIDITY: retained bounded validity; no new quality claim.
- MUSICAL_EDIT_CORRECTNESS: retained prior result; no edit performed by this probe.
- PLAYBACK_ARTIFACT_IDENTITY: PASS for real HTTP delivery of these retained fixtures.
- MUSICAL_POSITION_ALIGNMENT: UNVERIFIED.
- BROWSER_PLAYBACK: UNVERIFIED; AF_UNIX socket creation is denied in this executor.
- RESPONSIVE_PARITY: UNVERIFIED; no exact Work A RS-001 candidate found in open PR inventory.
- User-Agent variation is not browser, viewport, phone hardware, touch or accessibility qualification. Both sessions resolve the existing local principal, not two principals.
- No Range, hosted deployment, fault-injected crash recovery, listening or creative approval claimed.

## Reproduce

Exact source above; Python 3 + FFmpeg. Run `python3 tools/work_c_http_identity.py /tmp/work-c-http-evidence` from checkout root. It uses temporary durable state, prints a summary, writes a secret-free JSON receipt, and kills both test server processes. No third-party Python dependencies.

## Owner / next edge

Work A publishes exact RS-001 integration SHA. Work C uses a browser-capable executor to capture R1/R2 from the same project/revision pair across all six viewports, decode actual network responses, and establish measured same-position A/B. Work B retains promotion authority. Existing R3/PR22 qualifications remain closed.

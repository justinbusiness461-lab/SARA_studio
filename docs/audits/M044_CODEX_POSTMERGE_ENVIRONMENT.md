# M044 post-merge environment receipt

Verified 2026-11-13. No product changes.

Repository: justinbusiness461-lab/SARA_studio (1427534706).
PR 22: merged; head 91ed45f67f8c0bd432a7f4afb5de7a9ebe1dbdf5;
merge 1ea3909a25a2365862bd6a1106cfb386d933a504.
Fetched main: 749127ce0ce2cd08cdc5a6354626a078064f4704.
The only candidate-to-main difference is docs/audits/PF_MISSION_044_PR22_WORK_B.md.
Product source, backend, tests and dependency definitions are identical.

## Executed environment checks

- Python 3.12.14; Node v24.22.1.
- `npm ci --ignore-scripts --offline`: PASS, 18 packages installed.
- `PYTHONPATH=tools python3 -m unittest discover -s tests -v`: 66/66 PASS.
- `node --test tests/*.test.cjs`: 11/11 PASS.
- ffmpeg and ffprobe available at /usr/bin; no new audio measurement claimed.
- Playwright resolves from the executor runtime; Chromium exists at /usr/bin/chromium.
- `CHROMIUM_PATH=/usr/bin/chromium node --test tests/*.browser.cjs`: BLOCKED at browser launch. Direct launch reproduces `process_singleton_posix.cc: socket() failed: Operation not permitted`. No Studio browser assertions were earned by this run. This does not invalidate Work B's independent receipt.

## Product-shell integration map

Current HTML exposes prompt/Generate, Open/New, Play, a fixed Verse 2 Bass octave-edit button, R1/R2 switches and Save. app-ui.js owns presentation integration; existing projectRequest, renderAndVerifyRevision, applyVerse2BassOctave, selectABRevision and restoreProjectFromStorage must be reused.

The fixed edit button is not proof of contextual natural-language chat editing. The requested Chat/Canvas/Workstream/Proof musician journey still requires connected shell work and browser validation. Do not add a second revision store or derive authority from the selected A/B presentation.

Minimum next slice: contextual Verse 2/Bass command invokes the existing scoped operation; expose accepted/saved/rendering/playable states from real responses; keep selected historical R1 distinct from backend-current R2. Validate the complete journey on the exact implementation SHA, including Save/reopen and both lawful artifacts.

## Boundary and wake condition

Environment owner: executor/browser runtime. Boundary: Chromium process socket permission before page creation. Wake when an authorized browser executor can launch Chromium. Product owner: Work A for the shell; Work B retains independent qualification. Human listening, hosted deployment, mobile parity and creative approval remain unverified here.


## Follow-up: media transport contract, source evidence only

The follow-up local execution attempt failed before shell creation: exec-server rejected request, No such file or directory. No clean-tree tests, browser tests or new media measurements ran in this follow-up. The earlier 66/66 and 11/11 results remain historical evidence, not fresh execution.

GitHub reread confirms tools/studio_server.py on default branch matches exact main 749127ce0ce2cd08cdc5a6354626a078064f4704: blob 55a2b3b54fbc162faaa1b2c401ca979f3a210cea.

Finding M044-MEDIA-TRANSPORT-001: MEDIUM functional deployment contract gap, not a demonstrated security bypass.

- Owner: Bobby/backend transport; Railway/App Deploy consume the contract.
- Source: project_audio_bytes at line 642 authorizes project owner and revision membership, requires lawful output/historical association, validates audio, then reads immutable bytes. It does not reconcile orphan ownership during read.
- StudioHandler.do_POST serves /api/projects/audio as a complete 200 audio/wav response after session/capability/origin checks. The payload carries projectId/revisionId/artifactId.
- StudioHandler.do_GET at line 938 admits only the page and enumerated public assets; no project audio GET route exists.
- No request Range parsing or 206/Content-Range response is implemented in this source. A Range header on the POST is ignored; the complete authorized response remains 200. This is source interpretation, not an executed HTTP observation.
- Failed boundary: the supplied specification explicitly requires an authorized Range path. The existing full-buffer POST can support current client playback, but does not prove that transport requirement.
- Minimum repair: rightful owner must either explicitly retain full-buffer POST for the bounded local product and defer Range, or add an authorized range surface that reuses project_audio_bytes admission before slicing. No public CAS/path endpoint.
- Qualification on any implementation: authorized full response and valid single ranges; unauthorized/wrong-project/orphan requests deny before any audio body; invalid/unsatisfiable ranges fail explicitly; returned partial bytes match the authoritative artifact; malformed/corrupt artifact never reaches a range response.

Do not roll back merged R3/PR22 or claim the prior full-buffer playback gate failed. This finding narrows the remaining hosted-media contract. Wake on an owner-approved transport decision or implementation SHA, plus a working execution vantage.

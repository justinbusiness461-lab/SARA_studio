# PLATFORM ROUND 4 — Engineer #1 · Studio browser & Chat approval controls

**Canonical owner:** `justinbusiness461-lab/SARA_studio` repository ID `1427534706`.
**Source branch:** `feat/platform-identity-and-catalog` · source intake head `546c6a6def951b020f5a42a2c03415751d281af3`.
**Campaign:** PF-COMPLETION-001 · M045 · November 20 2026.
**Status at source-commit creation:** source and focused tests executed, full sequential Python + Node + all 28 browser cases in progress; release, creative approval, deployment and main promotion HOLD.

## WHAT CHANGED BECAUSE THIS WORKER EXISTED

1. **Server-issued, single-use durable approval challenges:** `tools/platform_chat_approval.py` extends **existing PlatformStore SQLite database** (same session/principal/tenant owner). Random 256-bit `appr-` challenge, 300-second expiry, source principal, project, exact expected current ProjectRevision and SHA-256 canonical action digest. Digest binds exact artist creative instruction *and* canonical operation parameters; darker versus brighter must never share approval digest. Atomic SQLite `BEGIN IMMEDIATE` transitions PENDING→CLAIMED, then SUCCEEDED, MASTER_REJECTED_BY_INDEPENDENT_METER, RIGHTS_POLICY_UNQUALIFIED, OWNER_UNQUALIFIED or RECONCILIATION_REQUIRED. Never reverts to pending or blindly retries ambiguous effects. Stored status is subordinate custody, **not ProjectManifest.currentRevisionId or audio ownership**.
2. **Authenticated Studio Chat:** `POST /api/m045/chat` and `POST /api/m045/chat/approve` use the **same existing platform Chat, Account, session, and Studio services** as `POST /api/platform/chat`. No client `confirmed:true` or client-owned digest. `MASTER` approval executes the canonical `authorized_master` owner and physically SHA-verifies revision-assigned master readback; `TRANSCRIBE_MIDI` returns a candidate without revision promotion; `PUBLISH` requires the existing host rights policy and exact explicit-publication owner. `REPAINT`, `ADD_SCRATCH`, `TOGGLE_LOCK`, `CREATE_MUSIC_VIDEO_GRANT` still return an explicit **409 OWNER_EXECUTOR_UNQUALIFIED** after approval; they never fabricate effects while canonical owner operations are unqualified.
3. **Artist UI:** `platform-ui.js`, `index.html`, `studio-shell.css` add a separate 48px master/publication/operation approval control. Before submitting, compare the original authenticated account, current project+source revision+artifact and 300-second deadline; show explicit human confirmation. Hide/consume local button before any request, do not retry ambiguous failures, and show output revision/digest/rights/telemetry only after owner readback.
4. **Independent mastering safety:** A real 50.5-second generated-song master returned `INDEPENDENT_TRUE_PEAK_CEILING_FAILED`. The token is consumed and the user receives **409 MASTER_TRUE_PEAK_CEILING_NOT_VERIFIED**. No master output is promoted on a failed independent ceiling. UI/browser RED then GREEN proves visible **NOT VERIFIED** and original audio selection remains unchanged. Do not relax/omit true-peak or claim streaming certification.
5. **DJ test clock:** The 12-second render response budget in `tests/m045-dj-grid.browser.cjs` now starts when `/api/projects/render` is actually dispatched, not before preceding commit; the request still has a strict 12-second response limit. The reproduced 8.9–9.6-second render now clears that boundary, exposing a **separate remaining `#djDeck` actionability timeout**. No Playwright actionability workaround, false click or deadline extension.
6. **Chromium telemetry:** `tests/qa-longtasks.cjs` optionally observes Chromium PerformanceObserver longtasks and the actual detached canonical `verifiedPlayback.media` playback readiness/position on DJ, RS-002, R2 A/B failure paths. It never changes audio, state, revision, selection, delay, crypto proof or deadlines.

## FOCUSED RED→GREEN RECEIPT

- New approval HTTP acceptance matrix: 8 cases RED against missing endpoints; 12/12 GREEN after implementation, including forged/expired/cross-user/stale/double-use/concurrent approval, actual WAV master digest/immutable revision, publication only with host rights, transcription P3 candidate, blocked unsupported music edits and different creative-intent digest.
- Targeted TDD RED for identical `REPAINT` operation digest despite darker-versus-brighter instruction, GREEN with exact artist instruction included.
- Generated-song mastering safety RED then GREEN: independent TP meter failure reports 409 and no committed revision or replay.
- 360px artist-facing master UI RED (missing second approval), GREEN for separate click and precise **NOT VERIFIED** at independently rejected generated master. Physical positive master approval validated in Python HTTP fixture; live publication requires separate host rights.
- Scratch Surgeon render-clock correction: correct HTTP render phase clears, but subsequent grid actionability remains unqualified in the 1 GiB CPU browser VM. Full suite must independently prove 28/28.

## EVIDENCE LADDER / HARD GATES

- `SOURCE` for modules, `EXECUTED` for focused Python and Playwright, `PHYSICALLY VERIFIED` only for actual source-bound WAV readback in positive master test. No release certification on partial browser success.
- Full Python/Node/28 Chromium regression is in execution when this source snapshot is published. Append exact terminal result + raw log digests before any certification escalation.
- True-peak rejection remains a genuine flagged mastering-engine limitation for this generated 50.5-second song; do not bypass independent check or invent creative approval.
- No GPU expense, Sentry prod authorization, Android physical device, cinema repo edits, main merge, public deployment or billing.
- The browser `25/28` Round2 receipt remains the last **completed full-suite** evidence until exact Round4 suite terminates.

## JUSTIN 101

WHAT CHANGED: durable single-use approval issuance/redemption using existing owners, mobile separate approval flow, truthful true-peak denial, DJ render-clock correction, exact active-media and main-thread diagnostics.
FAILED: browser DJ select/click still stalls after the HTTP render completes; full 28-case rerun pending at this receipt creation.
PROVEN: 12 focused approval HTTP tests and mobile true-peak failure UI test, unchanged source/revision security gates.
UNPROVEN: 28/28 Chromium; full creative-protected mutation parity; certified 210s meter and deployed security; human audition/approval.
TEAM NEXT: Browser QA use longtask/active-media measurements to pinpoint UI stall, ScoreCore owner implement actual edit/scratch/lock executors with immutable revision and P0/P1 proof, cinema owner remains independent.
JUSTIN ACTION: None for draft branch review; keep PR #37 DRAFT and main unchanged.


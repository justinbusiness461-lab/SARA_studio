# Chat D — M044 post-merge product-lie attack: failed A/B retrieval

**Date:** 2026-11-13. **Repo:** `justinbusiness461-lab/SARA_studio`. **Exact reviewed main:** `749127ce0ce2cd08cdc5a6354626a078064f4704`. **PR #22:** merged at `1ea3909a25a2365862bd6a1106cfb386d933a504`; **candidate:** `91ed45f67f8c0bd432a7f4afb5de7a9ebe1dbdf5`.

**Disposition:** P1 source-confirmed inconsistent failure-state handling; **live browser reproduction not performed**. The Work B receipt certifies the bounded positive/negative cases it actually ran, but did not explicitly report checking transition after an asynchronous project-open rejection with stale prior A/B Proof.

## Exact code path, merged `app-ui.js`

- `selectABRevision(label)` publishes `SWITCH_REQUESTED`, calls `clearVerifiedPlayback()`, then publishes `TARGET_LOADING`.
- Next it awaits `projectRequest('open', ...)` and `verifyPlayableRevision(...)` **outside any catch** inside `selectABRevision`.
- Button handlers at end of `app-ui.js` do catch promise rejection and call `setStatus('A/B failed: ...', 'warn')`, but **do not call** `publishABSwitchState(..., 'FAILED')` or clear `window.__M044_AB_PROOF__`.
- `clearVerifiedPlayback()` resets `window.__M044_PLAYBACK_PROOF__` and disables Play, but does **not** reset `window.__M044_AB_PROOF__`.
- The `media.play()` rejection branch **does** transition to `FAILED`; the earlier failed-open/failed-decode branches do not.
- A/B Proof is set on successful earlier COMPLETE; it can therefore remain on the client from an earlier successful switch after a later switch fails to load.

### Smallest reproducer for independent browser qualification
1. Generate lawful R1/R2. Complete A/B selection to R1 (A/B Proof reports R1).
2. Click R2. Intercept `POST /api/projects/open` for R2 with a controlled 503 (or return an otherwise lawful open but reject `POST /api/projects/audio`).
3. Observe `window.__M044_AB_SWITCH__.state` after request rejects, `window.__M044_AB_PROOF__`, `window.__M044_PLAYBACK_PROOF__`, disabled Play, and visible A/B label/status.
4. Expected: switch generation resolves to `FAILED`, matching target and reason; failed R2 is not playable; old A/B Proof is marked stale/cleared; no `COMPLETE`; project R2 current authority unchanged.
5. Repeat with delayed first request followed by a successful second request. The first rejection must not overwrite newer success.
6. Repeat with WAV decoder failure and fresh browser reload.

**Fix owner:** Bobby / Work A Studio client, only after owning team accepts reproduced defect. Preferred smallest change: guarded `try/catch` around pending open/decode path with request-generation test; use existing FAILED publication mechanism; clear/replace previous A/B Proof explicitly on switch initiation or failure. No new operation owner. No backend ProjectRevision mutation.

## Scope and evidence limits
Source checked through live GitHub fetch of merged `app-ui.js`. No authenticated browser/server was launched in this executor. Product behavior remains **UNVERIFIED** until a browser reproducer runs on the merged main or a successor. No musical listening or release approval.

## JUSTIN 101
WHAT CHANGED: Identified one exact merged-client failure-state gap and a six-step real-browser falsification sequence.
WHAT FAILED/BLOCKED: Live browser reproduction requires accessible qualified Studio runtime/fixture.
WHAT IS PROVEN: Source control-flow differences between media.play failure and project open/audio decode failures, plus retained GitHub audit.
WHAT IS NOT PROVEN: Browser-observed stuck loading / user impact, production fix, listening.
TEAM NEXT: Bobby/Work A reproduces and repairs smallest scope; B qualifies changed client; Chat D retests the live product.
JUSTIN ACTION: None.

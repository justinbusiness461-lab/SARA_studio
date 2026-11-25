# ENGINEER #1 — R31 Strict Player Physical-Clock Proof Gate

Date: 2026-11-24 · Repo: `justinbusiness461-lab/SARA_studio` · Owner: ENGINEER_1_SARA · Mode: $0, no synthetic substitution.

## Actual bug/failed boundary

The existing `tests/m045-three-song-player.browser.cjs` only clicked **Play** once (desktop, one song) and accepted `window.__M044_PLAYBACK_STARTED__===true`. The other five song/viewport combinations asserted artifact/ready status but not actual clock progress. That test could report a complete three-master browser pass without proving that all three were playing. R1/R2 comparisons trusted the UI-published A/B positions without a second, direct decoded-media clock readback.

## Minimal owner-preserving repair

1. Existing Chromium test now plays **all three masters at both 390px and 1440px**, waits for real `verifiedPlayback.media` readiness and independently observes the HTMLMediaElement's `currentTime` advancing over wall time. It verifies the active revision/artifact identity against the selected canonical Studio reference.
2. On R1/R2 switching, it maintains the existing 50ms `__M044_AB_PROOF__` restoration gate while independently sampling the selected media clock. The independent late sample's 150ms tolerance is **only** a Playwright observation-delay guard, not a weakened musical-position certification criterion.
3. `tools/m045_browser_media_clock.cjs` is a **test-only** validator; it does not write to ProjectManifest, CAS, SongSpec, Studio rights or browser media current selection.
4. `tests/test_m045_browser_media_clock.cjs` supplies eleven adversarial fixtures for: fake started flag; no element; no decoded ready/playing state; stale artifact/revision; impossible seek jump; wall-time reversal; sample-vs-UI A/B disagreement; malformed proof.

## RED→GREEN and source identity

- RED: missing validator module caused `MODULE_NOT_FOUND` exit 1; this was deliberately captured before implementation.
- GREEN: `node --test tests/test_m045_browser_media_clock.cjs`: **11 PASS / 0 FAIL / 0 SKIP** on local Node 22.16.0.
- Local `node --check` syntax PASS for both new files; after patching, JavaScript syntax parse PASS for the existing Chromium file.
- Independent GitHub readback source Git blob `4d493927a6b7c5b0f6f8111761217f1e3b8c5b09`; new test Git blob `df480905fd464b1374178d362941641fc393cdc9`; changed browser file Git blob `9260a960123953e68a79a678575891b06e2d9d98`.
- Full exact PR37/PR44 Chromium test **NOT EXECUTED**; a parsed script is not a browser pass.

## Remaining mandatory P0 boundaries

- `EXECUTOR_VANTAGE_MISSING=EXACT_PR37_SOURCE_TREE_LOCAL_AND_HOST_PRIVATE_R2_CAS_RECEIPTS`. Local Python/Node and original real media exist, but direct GitHub DNS checkout blocked; authenticated GitHub source/PR APIs work separately. No reconstructed v2.18 fallback.
- Positive `SARA_R25_REAL_MEDIA_STRICT=1` cold process restart + actual 390px/1440px six playback checks, exact WAV digest, R1/R2 <=50ms **UNVERIFIED**.
- Full combined exact-head Python+Node+Chromium, no skips, security/rightful-grants, Denial & Error lawful lyric evidence, merge PR36→PR37→PR44→main **HOLD**.
- `rightsStatus=UNVERIFIED_HELD`, commercial release false, creative approval false; no human audition implied and external spend $0.

## Required wake

Engineer #1/runtime QA must hydrate the exact PR37/PR44 runnable tree and host-private R2 receipt, execute `SARA_R25_REAL_MEDIA_STRICT=1 node --test tests/m045-three-song-player.browser.cjs` with real staging root+receipts, and run the full exact-head suite. Record physical logs/exit codes and independent authoritative readbacks before integration. Preserve Drive continuity with this R31 source/test checkpoint.

Outcome: **SOURCE TEST GATE HARDENED; PLAYER CERTIFICATION AND MAIN PROMOTION NOT EARNED.**

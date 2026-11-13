# Chat D — post-merge failed A/B retrieval RED handoff

**Target:** `justinbusiness461-lab/SARA_studio` main `749127ce0ce2cd08cdc5a6354626a078064f4704`.
**PR #22:** merged `1ea3909a25a2365862bd6a1106cfb386d933a504`.
**Source readback:** `app-ui.js` GitHub blob SHA `a2185db2044074518658cfb8f62bf97ac7c14cb5`; Work B qualified exact app-ui.js SHA256 `90b683b4096353975660511ed06e9ff21d088fafc240dc7fc69b8b3c70f67867`.
**Project-source check:** `Sara studio 10.txt` was physically mounted and contained candidate `91ed45f...`; historical Team Lead content superseded by live main.
**Status:** HARNESS_PREPARED / JS_SYNTAX_PASS / ACTUAL_SOURCE_EXECUTION_NOT_RUN / BROWSER_NOT_RUN.

## Exact source issue

`selectABRevision()` publishes TARGET_LOADING, then awaits `projectRequest('open')` and `verifyPlayableRevision` without its own catch. The button handlers catch exceptions to `setStatus('A/B failed: ...')`, but do not publish FAILED or clear earlier `window.__M044_AB_PROOF__`. `clearVerifiedPlayback` only clears playback proof. Unlike the media.play() failure path, an early network/decode rejection can leave the switch lifecycle pending and previous A/B Proof stale.

## New executable contribution

RED regression file `test_m044_ab_failed_fetch_red.cjs`:
- reads **real** `app-ui.js` from an exact checkout;
- checks SHA256 against Work B's pinned merged source;
- extracts the actual `selectABRevision` function into isolated Node VM;
- injects project-open rejection;
- asserts `__M044_AB_SWITCH__.state === FAILED`;
- asserts stale `__M044_AB_PROOF__ === null`.

Command from checkout root:
`node audits/chat-d/test_m044_ab_failed_fetch_red.cjs`.

Prepared ZIP: `M044_CHAT_D_Postmerge_AB_FailedFetch_RED_2026-11-13.zip` SHA256 `a16104695d4b6ea12f8c76eb140cca08b48c88832204dc0788af769d029d3458`.
JS test SHA256: `195ee6a3443df6f52382f14bfc8263004cdbd2b7c6827ee6fde75e501a9f634b`.
ZIP integrity PASS; Node syntax check PASS.
Executable test currently lives in downloadable ZIP, **not in this GitHub branch**. The test has **not** been run against a mounted authoritative checkout; do not report a RED runtime result until that execution occurs.

## First material finding

**P1** — stale A/B execution/proof presentation on an early failed revision-open or audio-decode request.
- Owner: Bobby/Work A Studio client.
- Impact: misleading pending Workstream and earlier Proof despite unavailable target audio.
- Failure boundary: async failed fetch before `COMPLETE`, after older A/B Proof exists.
- Smallest repair: generation-guarded catch, switch FAILED + stale proof invalidation, and no older request overwriting a newer selection.
- Wake: exact source executor runs pinned RED; owner repairs; Work B qualifies; Chat D verifies actual browser execution. Do not reopen M043/PR #10/R3 authority.

## JUSTIN 101
WHAT CHANGED: Created a pinned source-level Node RED test for merged client and checked its syntax; retained GitHub audit.
FAILED/BLOCKED: No exact checkout mounted in this executor, so no actual execution or browser reproduction was claimed.
PROVEN: current main/PR22 states, source-level catch asymmetry, JS syntax and package digest.
UNPROVEN: reproducibility of the browser state, owner fix, deployment, human listening.
TEAM NEXT: run pinned test in Codex/Work B clean checkout; fix smallest client cone.
JUSTIN ACTION: none.

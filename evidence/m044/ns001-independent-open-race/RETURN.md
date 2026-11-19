# NASA-001 — Independent Studio PR31 cross-project open race
Date: 2026-11-19 ET · Lead QA, owner-disjoint from Z implementation

## Authenticated exact evidence
- Rightful owner: `SARA_studio`, repo ID `1427534706`.
- Live Studio main at intake: `d6aa889a0def72bb8e1c87009a98d6c29e47067e`.
- Z implementation PR #31: https://github.com/justinbusiness461-lab/SARA_studio/pull/31
- PR #31 exact independently read head: `51b928e653896bf2558748f8967b05bd7798146e`.
- Exact read source `app-ui.js` Git blob: `db0220fceb9ef61076e5b1149802ccf3bc8b4c92`.
- Z's own browser.log checked through GitHub: 20/20 Chromium test entries PASS; reported 66/66 Python and 11/11 Node. This is **historical Z execution evidence**; this independent QA executor has not run Chromium.
- Test in this audit branch: `tests/ns001-overlapping-project-open.red.test.cjs`. Designed to execute directly against checked-out `app-ui.js` without third-party libraries.

## New independently reproduced source-level failure
I retrieved the exact PR #31 `app-ui.js` bytes and executed its unchanged `restoreProjectFromStorage()` function body in an isolated JavaScript runtime, injecting bounded controllable asynchronous project-open and WAV-verification dependencies. The sequential A→B positive preserved B. Two adversarial interleavings violated the latest-request-wins invariant:

1. Open A; request to open B later; B server result completes first; A server result completes last. **Actual outcome:** project display A, audio transport A, despite B being the last requested. The function has no request-generation identity at its first project-open await.
2. Open A; let A reach audio verification and wait; open and verify B; allow A audio verification to finish last. **Actual outcome:** project display B, audio transport A. `verifyPlayableRevision(result)` is called without an active request guard and can publish stale audio.

An earlier request's lawful audio may be valid for its *own* revision, but it must not become the selected transport or Proof of a later project. This is not a cross-project unauthorized server fetch finding. No full Chromium replay of these new interleavings has yet occurred.

Severity: **P1** at active product client-selection/preservation boundary. This defect is **separate** from Z's fixed delayed A/B request when opening B; it arises from *two concurrent project-open operations*.

## Required TDD/repair
Owner: **Work Z** in PR #31, not independent QA. Preserve authority and R1/R2 historical access.

- Allocate a monotonically increasing open-operation generation **when** a project-open request starts, before network await. Supersede or abort previous open; never accept an old return.
- Check current generation before mutating `skeleton`, `durableProjectRef`, titles, status, A/B inventories, target controls, or verified transport, after each awaited open/audio/ancestry step.
- Stage decoded WAV with guarded `verifyPlayableRevision(result, current, false)`; publish transport and its Proof only for the currently selected project/revision/artifact after all final guards. Revoke every superseded Blob URL.
- Do not publish `COMPLETE` for incorrect musical position or unauthorized source. A current failed open reports a truthful failure; older failures cannot replace newer success.
- Supersede outstanding open requests on New Project as well; do not let a pending old open resurrect the project.
- Run the new source-extract regression RED→GREEN, then the existing 20-entry browser suite, Python 66, Node 11, and fresh-process R1/R2 preservation proof. For production qualification, add two actual Chromium route-gated overlapping-open cases and one New Project mid-flight test.

## Evidence ceiling and preservation
Independent execution: exact extracted source function with controlled I/O dependencies, sequential positive correct, two missing-rejection cases reproduced. Test script committed for replay but **fresh Node execution of that committed file is not claimed here**. Z historical logs read, not independently reproduced. No application product changes, no ProjectRevision mutations, no media writes, no main merge/deploy/approval.

REPAIR_OWNER=WORK_Z; REVIEW_OWNER=NIGHT_LEAD; FIRST_FAILED_BOUNDARY=UNGUARDED_CONCURRENT_PROJECT_OPEN_AND_AUDIO_PUBLICATION; WAKE=EXACT_Z_REPAIR_HEAD_WITH_NODE_RED_GREEN_AND_CHROMIUM_INTERLEAVING_CONTROLS.

**JUSTIN 101** — CHANGED: authenticated PR31 and discovered two additional stale-open transport regressions; independent source-level replay performed and runnable RED committed. FAILED: old open/audio may outrun newer selection. PROVEN: bounded exact-function behavior and GitHub file identity. UNPROVEN: real Chromium replay and product fix. TEAM NEXT: Z resolves in same PR31; Night Lead independently replays repaired exact SHA. JUSTIN ACTION: none.

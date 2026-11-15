# M044-AB-FAILURE-001 — Work B independent RED

## Target
MAIN_SHA = `b8385407425ea8f8c05de044b1c1a8728cdd5eab`

## Reproduction (Chromium + Playwright)

Test: `tests/r2-ab-failure.browser.cjs`

### Case 1 — audio fetch failure during A/B
**FAIL (product RED confirmed)**

After a successful R1 A/B COMPLETE Proof exists:
1. Route `/api/projects/audio` → HTTP 503
2. Click R2 A/B

Observed residual state:
- `__M044_AB_SWITCH__.state` = **TARGET_LOADING** (expected **FAILED**)
- Prior successful `__M044_AB_PROOF__` retained
- Play disabled (good)
- No silent audio fallback (good)

Root cause (source read of `selectABRevision` in `app-ui.js`):
- `projectRequest('open')` / `verifyPlayableRevision` throw or return false
- function `return false` without `publishABSwitchState(..., 'FAILED', ...)`
- outer `onclick` catch only `setStatus('A/B failed: ...')`
- only the media.play() catch path publishes FAILED today

### Case 2 — stale failure vs newer success
**PASS (generation fencing already holds)**

Late 503 on generation N does not erase COMPLETE of generation N+1.

## Work B gate status

```
GATE1_AB_FAILURE_RED = CONFIRMED
SILENT_FALLBACK = NO (not observed)
STALE_SUCCESS_PROOF_RETAINED_ON_FAIL = YES
TERMINAL_STATE = TARGET_LOADING (defect)
STALE_FAILURE_CANNOT_ERASE_NEWER_SUCCESS = PASS (already)
```

Bobby owns mutation on exact main `b838540...`.
Work B will re-run this RED against `BOBBY_AB_FIX_SHA`.
RS-001 remains not on main — separate gate.

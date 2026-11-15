# Mission 044 — Work B merged-main golden journey (post PR #22)

## Identity

| Field | Value |
|-------|--------|
| **MAIN_SHA** | `3c2fa7f908ff0463f3f67109321d5e2f329dae22` |
| Parent | `749127ce0ce2cd08cdc5a6354626a078064f4704` |
| Product tree | PR #22 qualified product preserved (docs-only tip commit) |
| PR #22 | closed — not re-qualified |

## RS-001 status on this tip

| Check | Result |
|-------|--------|
| `studio-shell.css` | **ABSENT** |
| `tests/responsive-shell.contract.test.cjs` | **ABSENT** |
| `index.html` still has `.app{max-width:560px}` | **YES** |
| `user-scalable=no` | **still present** |
| Open PR delivering RS-001 | **NONE found** |

`RS001_ON_MAIN = NO` — integration candidate remains Work A / Grimoire work, not a Work B merge gate yet.

## Independent golden-journey execution (desktop Chromium)

Fresh clone @ `3c2fa7f…`.

| Suite | Result |
|-------|--------|
| Python | **66/66 PASS** |
| Node unit | **11/11 PASS** |
| Generate / PWA browser | **2/2 PASS** |
| R1 playback browser | **3/3 PASS** |
| R2 / A-B browser | **4/4 PASS** |
| R2 cold reopen browser | **1/1 PASS** |
| **Browser golden total** | **10/10 PASS** |

### Product discriminators

```text
MERGED_MAIN_GOLDEN_JOURNEY = PASS — DESKTOP / DEFAULT LAYOUT
R1_REAL_PLAYBACK = PASS
R2_REAL_PLAYBACK = PASS
A_B_SAME_POSITION = PASS  (≤ 50 ms)
PROOF_ATOMICITY = PASS
FAILED_FETCH_TRUTH = PASS  (audio retrieval failure never presents as playable)
COLD_REOPEN = PASS
HISTORY_REBUILTS_FROM_BACKEND = PASS
NO_BROWSER_SHADOW_AUTHORITY = PASS — bounded by existing tests
```

### Explicitly not certified this turn

```text
PHONE_GOLDEN_JOURNEY = UNVERIFIED
SPLIT_SCREEN_GOLDEN_JOURNEY = UNVERIFIED
SIX_VIEWPORT_MATRIX = UNVERIFIED
RS001_INTEGRATION = NOT_ON_MAIN
HOSTED_DEPLOY = UNVERIFIED
GRAVEYARD_FREQUENCY = UNSTARTED
```

## Next Work B gate

Wake only when Work A publishes exact:

`WORK_A_RS001_SHA` rebased on current main

Then: product-byte diff → existing M044 suite → six-viewport golden journeys → merge same cycle if green.

Until then, merged-main **desktop** musician path remains green; responsive parity is the open product edge.

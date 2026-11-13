# PF-M044-RUNNABLE-NASA-002 — Post-Merge Product Reproduction

**Program:** PF-COMPLETION-001  
**Mission:** M044  
**Lane:** Runnable deterministic reproduction  
**Canonical repo:** `justinbusiness461-lab/SARA_studio`  
**Repo ID:** `1427534706`  
**Dispatch date:** 2026-11-13

## Current authenticated frontier

- PR #22 merged.
- Qualified candidate: `91ed45f67f8c0bd432a7f4afb5de7a9ebe1dbdf5`.
- PR #22 merge/product SHA: `1ea3909a25a2365862bd6a1106cfb386d933a504`.
- Post-merge evidence-only main tip at dispatch: `749127ce0ce2cd08cdc5a6354626a078064f4704`.
- Delta from `1ea3909...` to `749127c...`: one documentation file only; no product-byte delta.

Runnable asks one question:

> If Bobby's machine disappeared, can a fresh exact checkout reproduce the connected R1 → R2 → A/B → reopen product path from durable repository authority?

## Required clean-room execution

Use a fresh checkout at exact `749127ce0ce2cd08cdc5a6354626a078064f4704`.

Run:

```bash
EXPECTED_MAIN_SHA=749127ce0ce2cd08cdc5a6354626a078064f4704 \
EXPECTED_PRODUCT_SHA=1ea3909a25a2365862bd6a1106cfb386d933a504 \
CHROMIUM_PATH=<real chromium executable> \
bash tools/runnable_m044_postmerge.sh
```

The harness must execute, from clean source:

1. dependency installation;
2. full Python suite;
3. ScoreCore / M044 session / prompt UI Node tests;
4. R1 revision-bound playback browser tests;
5. Generate/PWA browser path;
6. R2 scoped Verse 2 Bass −12 edit;
7. authenticated R2 playback;
8. R1/R2 A/B with same-position contract;
9. completion/proof consistency;
10. fresh server + fresh browser cold reopen;
11. reconstruction of R1/R2 A/B handles from backend history.

## Required product truths

PASS is permitted only if execution establishes all applicable facts:

```text
R1_PLAYBACK = PASS
R2_EDIT = PASS
R2_PLAYBACK = PASS
A_B = PASS
A_B_COMPLETION_CONSISTENCY = PASS
A_B_POSITION_DELTA_MS <= 50
LATE_R1_REPLACES_R2 = NO
SILENT_FALLBACK = NO
R2_CURRENT_AFTER_RESTART = PASS
R1_HISTORICAL_AFTER_RESTART = PASS
DUPLICATE_R1_BINDINGS = 0
DUPLICATE_R2_BINDINGS = 0
PHANTOM_PROJECT_REVISION = 0
```

A top-level PASS never overrides contradictory facts.

## Evidence ceiling

This specification and harness are repository changes only until executed in the qualified Codex/Runnable environment.

Do not claim browser, audio, listening, hosted deployment, or release proof from the existence of this file.

## Stop conditions

Stop at first material contradiction:

- checkout SHA mismatch;
- dirty source before execution;
- qualified merge SHA not in ancestry;
- dependency install failure;
- any existing suite regression;
- R1/R2 wrong artifact identity;
- R2 not current after restart;
- R1 absent from lawful history;
- stale R1 publishes as current;
- A/B Proof and transport disagree;
- same-position delta exceeds 50 ms;
- browser uses silent fallback.

## Required return

```text
RUNNABLE_NASA002 = PASS|FAIL|BLOCKED

MAIN_SHA = 749127ce0ce2cd08cdc5a6354626a078064f4704
PRODUCT_MERGE_SHA = 1ea3909a25a2365862bd6a1106cfb386d933a504

PYTHON = <passed/total>
NODE = <passed/total>
R1_BROWSER = <passed/total>
GENERATE_BROWSER = <passed/total>
R2_AB_BROWSER = <passed/total>
R2_COLD_REOPEN = <passed/total>

R1_PLAYBACK = PASS|FAIL
R2_EDIT = PASS|FAIL
R2_PLAYBACK = PASS|FAIL
A_B = PASS|FAIL
A_B_COMPLETION_CONSISTENCY = PASS|FAIL
A_B_POSITION_DELTA_MS = <actual>
LATE_R1_REPLACES_R2 = YES|NO
SILENT_FALLBACK = YES|NO
R2_CURRENT_AFTER_RESTART = PASS|FAIL
R1_HISTORICAL_AFTER_RESTART = PASS|FAIL

SOURCE_MUTATION_BY_RUNNABLE = NONE
PRODUCT_AUTHORITY_CREATED = NONE
RELEASE_CERTIFIED = false
```

Then JUSTIN 101: changed / failed / proven / unproven / action.

# Engineer #1 R32 — Strict-Mode Real-Media Source and R1/R2 Admission

**Date:** 2026-11-25 · **Owner:** `SARA_studio` · **Scope:** Existing R25 test harness only · **Main / playback release:** HOLD.

## Proven failure boundary

At PR #37 head `d876cad4d55aadee144e7bf6756c224b41a8c117`, `tests/r25_three_song_fixture_server.py` declared `stagingRealMedia=bool(real)` after checking only the presence of two JSON files, the existence of a staging directory, and three unique title labels. It did **not** bind the files to the source SHA-256, sample-level WAV identity, actor/project lineage, or current R2 ancestry. An attacker could construct non-authentic receipts and claim a strict real-media test setup. A browser test that starts on this basis is not automatically qualified.

## Exact minimal repair

- Existing strict fixture server calls `verify_real_staging` *before starting StudioHandler*. The helper is strictly a test precondition and does **not** create a new media, revision, grant, or project authority.
- The fixed cohort of three artist masters is pinned to independent source/WAV/decoded-PCM/frame-count identities from the **R30 real-media receipt** (12/12 matching constants); all original media remains private.
- For every master, verify held-rights claims, exact Studio ProjectRevision source membership, lawful authorized historical audio read, exact WAV/PCM SHA-256 and sample frames. Raw source CAS is accessed only **after** project authorization and membership; source bytes must match SHA.
- R2 must be an immutable, distinct, unapproved edit bound to R1's exact project/revision, selected current revision, lawful CAS WAV bytes, matching full-song sample count, and actual parent/source ancestry. Arbitrary R2 JSON, rebranded R1, or orphan CAS objects do not qualify.
- No grants, commercial or creative approval, background work, expense, or changes outside Studio.

## TDD / physical proof

1. **RED:** initial new test module returned `ModuleNotFoundError` (test failure reproduced before helper).
2. **GREEN:** local `python -m unittest discover`: **16 PASS / 0 FAIL / 0 SKIP**, plus `python -m compileall`. Explicit fake local WAV fixtures are for **unit tests only** and cannot be used as strict real-media certification.
3. Independent GitHub blob readbacks match exact local tested files:
   - `tools/r25_strict_staging_binding.py` — `fb8603c0a00541a231f8cc9ab35e710373e45d2c`
   - `tests/test_r32_strict_staging_binding.py` — `b124a2d723267849ea3beef58d5c2b651b9a6151`
   - `tests/r25_three_song_fixture_server.py` — `c2d20db273520551dbe7c1c1270bab8a51f8aef3`.
4. Historical evidence retained (not rerun as R32): R30 three real artist master independent decodes **3/3**; prior VocalOccurrence candidate tests **14/14**; R31 browser-clock helper tests **11/11**.

## What is still NOT proven

- `SARA_R25_REAL_MEDIA_STRICT=1` **positive** actual master playback in cold-reopened Chromium at 390/1440, independent audio clocks for 6 song/viewport combinations, exact R1/R2 <=50ms musical position, full exact-head Python/Node/Chromium and authenticated host-private R2 receipt are **NOT EXECUTED / UNVERIFIED**.
- `Denial & Error` lawful Studio LyricTimelineRevision and trusted VocalOccurrence issuer: **NOT PUBLISHED**.
- PR #36→#37→#44 reviewed `main` merge: **HOLD**, rights `UNVERIFIED_HELD`, `productionGrantsIssued=0`, external spend USD 0.
- `EXECUTOR_VANTAGE_MISSING=EXACT_PR37_PR44_RUNNABLE_TREE_AND_HOST_PRIVATE_R2_RECEIPT`. Repo file API authenticates blobs, but local runner's direct github.com checkout DNS is blocked; the private R2 receipt has not crossed this executor's boundary.

## Justification for main HOLD

`WORKER REPORT != SOURCE BYTES != CANONICAL MAIN != DEPLOYED RUNTIME.`
This PR raises strict positive test integrity, but cannot turn candidate code or synthetic unit vectors into a musical playback certificate. Merge only after independent full-tree exact-SHA regressions, lawful source and grant authorization, and real-media cold restart proof.

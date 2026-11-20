# SJ³ donor Wave 001 — ScoreCore boundary qualification (REVIEW CANDIDATE)

**Date:** 2026-11-19. **Campaign:** PF-COMPLETION-001 / M044. **Canonical owner:** SARA_studio / ScoreCore. **Proposed reviewing owner:** Work B / Bobby-Cody coordination. **This is a DRAFT PR, not a product release.**

## Provenance and mechanism

Source: research1 (1).zip SHA-256 `06690b4d8b8f6c3a35bb349a6ee730d12d983083ae1ea41ca3fd7ce6aabe4a0e`; MINT donor nested SHA-256 `7a7ff63b1aa4ce89b4728289f96b5c6415eced4851d45b482d324787f69d1dfd`. Source reviewed, no MINT code imported.

Baseline: `main` `d6aa889a0def72bb8e1c87009a98d6c29e47067e`, `scorecore.js` Git blob `6ee01fbfdf6f2b4cebcfc9cbc533aa28f59175da`; `tools/scorecore.cjs` delegates to `../scorecore.js`. Preserve SongSpec and existing ProjectRevision/ProductionTimeline authority.

## Source-level adverse findings

1. **P1 / overlapping named sections:** transposeSection accepted section intervals that overlap. An edit of chorus bass can also fall inside a simultaneously named verse. Under CHANGE ONLY THIS™, fail closed until authoritative target and overlap policy are declared.
2. **P1 / unsafe integer timebase:** Number.isInteger accepts numbers beyond MAX_SAFE_INTEGER; section times and note endpoint addition can silently lose tick precision. Require safe integers at boundaries, including computed note end.

### Local independent verification

Local Node.js `v22.16.0` on Git-blob-identical baseline: **5 tests: 2 PASS, 3 RED** (all three expected missing rejection cases). Isolated patched candidate: **5/5 PASS**. Candidate source blob `4bb93a73c7fafd2b90216c3d3d2729e9be9e18f2` matched the exact patch pushed to this branch.

These checks do **not** imply full repository tests, backend integration, render/media listening, deployed verification, P0/P1 audio preservation or creative acceptance. Full repo CI must be run on PR head.

## Scope of proposed patch

- Reuse the existing `transposeSection` method; no second compiler or authority introduced.
- Reject overlapping named sections (selected vs any neighbor).
- Enforce safe integer sections, note starts, note durations and computed note ends.
- Add five focused source regressions at `tests/scorecore_donor_boundaries.test.cjs`.
- Do not change generated music, persisted revision authority, renderer, lyrics, auth or cinema.

## Required independent owner follow-up

1. Run `node --test tests/scorecore_donor_boundaries.test.cjs`, `node --test tests/scorecore.test.cjs`, and `python3 -m unittest discover -s tests -v` on **this exact branch head**.
2. Check intended overlap semantics against the canonical SongSpec schema; if legitimate overlapping named sections exist, specify a target-event disambiguation mechanism instead of blanket rejection.
3. Run the real M044 R1/edit/R2/render/kill/reopen probe, physical audio preservation, legal historical access, and exact musical-position A/B.
4. Work B approves/rejects and merges only after evidence; branch/PR existence is not product release.

**Decision:** CANDIDATE_FOR_OWNER_REVIEW. No certification or deployment claim.

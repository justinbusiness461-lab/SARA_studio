# SJ³ WAVE 004 — Native mastering, provenance and artist-facing Wave 003 controls

**Campaign:** PF-COMPLETION-001 · Mission 045 · SJ³ Full Native Absorption  
**Authority:** `justinbusiness461-lab/SARA_studio` (repo ID `1427534706`)  
**Branch:** `feat/m045-native-generation-attempt`  
**Date:** 2026-11-19 campaign / 2026-11-20 UTC KERNEL execution  
**Prior Wave 003 branch source SHA:** `7f5470a6bf3ba65ddad9763660d6da4e3b89e9e4`  
**Evidence manifest:** `evidence/m045-wave004/source-manifest.json` (9 source files; SHA-256 and Git blob IDs)

## What the native owner actually does

1. **Mastering processor:** `tools/m045_wave4_mastering_provenance.py` implements bounded CPU-only two-pass FFmpeg loudnorm processing, calibrated to artist-selectable **−14** or **−9 LUFS** and **−1 dBTP** ceiling. It decodes physical PCM16 WAV, rejects invalid or silent audio, independently re-measures rendered output loudness and true peak, and returns the measured outcome. An unreachable target is reported as **TARGET_UNREACHED_LIMITED**, not falsely marked PASS.
2. **Authorized master publication:** `tools/m045_wave4_service.py` plus existing `tools/studio_server.py` implement `POST /api/m045/master`. Session, principal, project, source revision, accepted source artifact, expected-current CAS and Sonic Lock are validated. All media reads go through the existing **lawful revision→artifact association**. Render publication invokes the **existing** durable render-attempt staging/CAS/revision owner, not a duplicate publisher. The source revision and its original WAV are retained.
3. **Subordinate provenance:** `CanonicalProvenanceRecord` is held inside the durable render-attempt identity and referenced by the existing operation meaning digest. Records include source project and revision, parent audio digest, output WAV digest, **physically decoded PCM digest**, DSP transform/measurement, preservation claim, and `rights_status=UNVERIFIED_HELD`. Source and output digests are rechecked independently. **This is NOT a separate SampleAsset rights authority and cannot grant clearance.**
4. **Mobile artist controls:** existing `index.html`, `studio-shell.css` and `app-ui.js` now expose **Audition FM Preview**, **Audio → MIDI (P3 Candidate)** and **Master Verified Revision** with −14/−9 presets, ≥48 px controls and six-viewport overflow checks. The artist's selected project and verified playback artifact are pinned before requesting transcription/mastering. Responses that arrive after project change may not publish stale UI. Mastering success is not shown as VERIFIED until the new revision and its **exact audio artifact** have been read back and browser-decoded.
5. **No false audio promotion:** estimated audio→MIDI notes are still `P3_RECONSTRUCTION` relative to the original recorded audio, not P0 audio. FM previews remain **unpublished** until separately accepted by existing authority. An explicit master operation produces a new revision but **not** creative approval or rights clearance.

## Precise RED → GREEN evidence

| Gate | Authentic result |
|---|---|
| Missing mastering engine/routes | RED before implementation (route absent) |
| Incorrect `mastered[44:]` PCM identity | RED reproducer → fixed by decoding the actual WAV PCM payload |
| Sonic Lock accidentally permitting whole-mix mastering | RED reproducer → fail-closed repair |
| Missing artist-facing UI controls | RED → six-viewports GREEN |
| Unsaved project control showing no actionable error | RED → visible NOT VERIFIED message |
| Master commit succeeded but corrupted mastered WAV still shown VERIFIED | RED → repaired, exact-artifact/decoded-audio check |
| Final full Python suite | **187/187 PASS**, 0 failures, log SHA-256 `24b88aaa6c7302da8dcda1669e6162af59732fe39f957e6ee7829757a1c9beef` |
| Final full Node+Chromium suite | **56/56 PASS, 0 failures, 0 skips**, log SHA-256 `6b676513367245d5f12e20931c7c237c952aeee184833478f62abc7ef876163f` |
| Mobile end-to-end | Browser tested project open → FM preview → P3 MIDI candidate → source-bound master → R3 reopen and verified audio |
| Fresh process recovery | Exact new/current master and original historical artifact verified through independent Studio read API |
| External GPU model calls | None; FFmpeg CPU process only |
| GitHub contents | All 9 code/test blobs matched the frozen independently executed KERNEL candidate |

**Commands** (isolated KERNEL checkout, Node Playwright test-only deps installed, no runtime package manifest change):  
`PYTHONPATH=tools:tests python3 -m unittest discover -s tests -p 'test_*.py' -v`  
`CHROMIUM_PATH=/usr/local/bin/chromium node --test --test-concurrency=1 tests/*.cjs`

Raw evidence: `evidence/m045-wave004/{python-full.log,node-chromium-full.log,master-adversarial-red.log,browser-false-proof-red.log,browser-focused-green.log,master-focused-green.log,route-missing-red.log,browser-missing-controls-red.log,browser-unsaved-action-red.log,fresh-process-recovery.log}`.

## Critical, unresolved release boundaries

1. **NOT full-length 180–210-second mastering:** this candidate intentionally accepts 44.1-kHz PCM16 sources up to **75 seconds** and at most **16 MiB**. The existing canonical media-publish limit is 16 MiB; full-song 3–3½-minute 44.1-kHz stereo PCM16 is larger. A streaming/bounded-memory, durable full-length render publication extension requires separate owner review and tests. **OWNER: Work B / Sound Forge render authority. WAKE: full-length streaming/CAS contract, independent 210-second audio + crash recovery tests.**
2. **NOT formal ITU-R BS.1770-4 or true-peak metering certification:** this candidate uses FFmpeg `loudnorm` (EBU R128 / BS.1770-derived) and independently reads output measures. It does **not** claim formal reference-vector conformance of the host binary, all sample rates, codecs, oversampling filters or meter interoperability. ITU specifies measurement algorithms; −14/−9 LUFS are product presets, not ITU-mandated delivery targets. **OWNER: independent Audio QA. WAKE: independent reference-vector meter + codec/resample attack suite + measured tolerance and listening.**
3. **FFmpeg redistribution/legal qualification:** KERNEL binary `n7.1.5-12-g1fdbca85aa-20260731` reports `--enable-gpl --enable-version3`. Calling it locally does not grant blanket permission to redistribute that build with a proprietary packaged app. **OWNER: packaging/legal. WAKE: appropriate deployment/runtime strategy and third-party rights documentation.**
4. **NOT full mopy-inspired SampleAsset rights registry:** master render provenance is immutable and bound to the existing operation/revision identity, but full rights-registration evidence, rights grants, stem/sample ancestry, source license readback, release gating and migration for all pre-existing render artifacts are not implemented. No unverified source may silently become `LICENSE_CLEARED`. **OWNER: SampleAsset/ProjectRevision authority. WAKE: accepted rights source/proof contract and existing-asset migration tests.**
5. **NOT P0 audio preservation for transcription or whole-mix mastering:** loss-reported estimated MIDI is reconstruction; master DSP changes the full waveform. P0 symbolic event locality is a different proof requirement. No creative approval, full device certification, actual artist audition or production deployment is claimed.
6. **Failure injection for new mastering:** existing render attempt durability/recovery mechanisms were reused; Wave 004-specific crash injection at all publication boundaries remains to be performed, before certification.

## Source state / impact

- **Canonical owner only:** `SARA_studio`. No write to `dj_rezrxtion` or legacy `song_forge`.
- **Authority reused:** `ProjectManifest.currentRevisionId`, immutable `ProjectRevision`, render attempt, lawful selected revision/audio association, Studio session, Sonic Lock and existing mobile/AB generation fences.
- **No competing ledger/owner:** provenance lives subordinate to render-attempt and operation digests, never authorizes a media read by digest alone.
- **No product-release claim:** tested branch source ≠ independently deployed artifact ≠ actual listening ≠ technical meter conformance ≠ creatively approved master.

## JUSTIN 101

**WHAT CHANGED:** Native CPU mastering and immutable transform lineage, authenticated master API, three user-facing mobile operations, exact browser playback proof fence, nine source/test files and ten raw test logs saved to rightful repository.

**WHAT FAILED:** Reproduced incorrect fixed-header PCM digest, missing Sonic Lock master guard, unsaved-action error and false verified UI on corrupted output. All four repaired with regression coverage.

**PROVEN:** 187 Python tests, 56 Node/Chromium tests, source SHA/remote Git blob parity, lawful master/historical readback and exact browser-backed Wave 004 flow.

**UNPROVEN:** Full-song duration, certified BS.1770 reference meter, cleared SampleAsset rights registry, Android device, full crash injection, creative/listening approval and production release.

**TEAM NEXT:** Work B qualifies full-length render authority and provenance scope; Audio QA independently compares meters/codecs; Work Z validates RS-002 cross-session behavior on the exact eventual integrated head; packaging/legal qualifies FFmpeg; artist reviews listening.

**JUSTIN ACTION:** None for this technical branch delivery.

**Disposition:** `SOURCE COMMITTED → KERNEL EXECUTED → REGRESSION GREEN`; release/creative/certification gates remain HELD.

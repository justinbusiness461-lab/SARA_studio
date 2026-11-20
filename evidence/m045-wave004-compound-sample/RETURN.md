# SJ³ Wave 004 — Compound Intent and Sample Lab native extension

**Canonical owner:** `justinbusiness461-lab/SARA_studio` · repo ID `1427534706`  
**Source branch:** `feat/m045-native-generation-attempt` · reconciled base `08ec8abf861cca6a7f4ce3ec7d575dbf0d09b12e`  
**Campaign:** PF-COMPLETION-001 · M045 · November 20, 2026 UTC  
**Disposition:** SOURCE + CPU LOCAL TESTS + CHROMIUM EXECUTED, **not** release certified.

## What changed because this worker existed

The previously integrated Wave004 mastering/FM/MIDI branch was independently inspected and **preserved**. Existing `authorized_master`, mastering provenance, `POST /api/m045/master`, and its lawful durable render-attempt/CAS publication **were not replaced**. The earlier concurrent worker had already delivered a stronger mastering owner; this extension ports only missing capabilities.

1. **Non-authoritative compound intent planner** (`tools/m045_edit_proposal.py`, extended `scorecore.js` validator). Strict multi-clause phrase compilation, canonical second-Verse selection from actual SongSpec, preservation scopes, lock rejection, duplicate/conflicting clause rejection, explicit P2/P3 claim and artist approval requirement. Example: *Keep hook exactly the same, slow down middle verse, make bass darker, add weird metallic sound.* This **creates a plan**, not a render or a P0 preserved revision. Unsupported prose fails closed.
2. **Non-destructive Sample Lab DSP** (`tools/m045_sample_lab_dsp.py`): exact-frame source seeking, PCM16 stereo 44.1/48-kHz selected-region slicing, deterministic resonant low-pass, metallic comb, coupled varispeed pitch/rate and bounded acyclic modular FX chain. Source CAS bytes never mutate; previews carry source digest. Sample FX selected regions max 10 seconds; full-song streaming stem routing is **not** certified.
3. **Authorized Studio service extension** (`tools/m045_wave4_service.py`, `tools/studio_server.py`): `POST /api/m045/compound-plan`, `POST /api/m045/sample-preview`. Same canonical session → principal → project → revision → lawful revision-to-audio association → digest check. No client-supplied CAS authorization or new rights authority. `CanonicalProvenanceRecord` **reuses the integrated Wave004 master's provenance class**, with `UNVERIFIED_HELD` and P3 preview. Preview is never auto-committed or master-promoted.
4. **Same mobile shell and truthful Proof** (`index.html`, `studio-shell.css`, `app-ui.js`, `service-worker.js`): added compound/sample controls inside existing Wave004 card, not a duplicate FM/MIDI/master area. Touch targets ≥48 px with 8 px gaps, source/revision generation guards, client-side SHA-256 verification, explicit preview/unpublished status and clean invalidation on project changes. Offline service worker cache updated.
5. **Independent RED/GREEN**: new Python, Node, and Chromium tests prove live source authority, missing/foreign session rejection, orphan SHA denial, exact-frame cuts, lock conflicts, dual-layer SongSpec plan checking, actual waveform preview hash, source revision unchanged after operation, 390px UI and browser cold reopen. `tests/test_m045_wave4_parity.py` also verifies a 44.1kHz fs/4 intersample-peak master and explicitly rejects unsupported 48kHz mastering.

## Full updated exact-branch test inventory

- Python: **196/196 PASS**, zero failures; `PYTHONPATH=tools:tests python3 -m unittest discover -s tests -p 'test_*.py' -v`.
- Node unit: **39/39 PASS**, zero failures/skips; `node --test --test-concurrency=1 tests/*.test.cjs`.
- Chromium: **21/21 PASS**, zero failures/skips, all `tests/*.browser.cjs` executed as three synchronous groups due KERNEL per-command run limits. Actual Chromium executable `/usr/local/bin/chromium`.
- Combined = **256/256 PASS**. One-command full Node+Chromium invocation was **not** executed as one process; all the exact files were executed across the bounded groups, recorded in logs.
- Source/test SHA-256 and each raw test-log digest are durably described by `source-manifest.json`; publication requires independent GitHub readback to separate local execution from repository receipt.

## Honest HOLD boundaries

- **P0:** Compound plan compiler is deliberately bounded, not generalized natural-language parsing or an actual atomic multi-domain edit executor. It does **not** guarantee locked audio exactness when P3 provider generation might bleed.
- **P0:** SampleAsset provenance and rights registration are not a full mopy ontology/rightful durable SampleAsset authority; `CanonicalProvenanceRecord` is subordinate lineage only. Sample Lab effects create *unpublished* candidates; production-level save/instrument mapping, batch stems, full routing, artifact association and crash recovery are not yet physically qualified.
- **P0:** Mastering owner from the earlier Wave004 has a 44.1-kHz PCM16, ≤75s ceiling and existing canonical 16 MiB media limit; 48kHz and full 3½-minute masters remain blocked. No false BS.1770-4 accredited meter claim. Existing local FFmpeg build advertises GPLv3 flags; packaging/legal must qualify redistribution or alternate DSP.
- **P1:** Varispeed changes pitch **and duration together**, not independent pitch-preserving time stretch. Real artist audition, full Android device and deployed service not executed. Sample preview rights remain `UNVERIFIED_HELD`.
- **P1:** All 30 donor parity contracts and PulseForge Wave005 film-global audio authority are **not** certified by this source change.

## JUSTIN 101

**WHAT CHANGED:** Bounded compound intent + immutable-source Sample Lab, canonical-service admission, phone controls, tests and durable evidence.

**FAILED AND REPAIRED:** Initial full-song WAV expansion exhausted a 1 GiB Chromium executor; exact-frame WAV seeking repaired source preview RAM usage. A concurrent Wave004 master owner was already present and was preserved rather than overwritten.

**PROVEN:** 196 Python + 60 Node/Chromium local tests; actual authorized HTTP, real decoded PCM previews, source/revision readback, mobile touch sizes, clean current and historical authority behavior.

**UNPROVEN:** Release, 48kHz mastering, 210-second master, independent meter accreditation, human creative approval, comprehensive rights ontology, Wave005.

**TEAM NEXT:** Sound Forge Work B + Audio QA resolve full-song mastering/meter/rights; ScoreCore owner extends compound plan to atomic dependency-aware musical edits; SampleAsset owner implements durable source/rights and modular routing; mobile QA certifies actual Android; PulseForge owner receives accepted soundtrack grant only.

**JUSTIN ACTION:** None needed for source-review stage. No production release or protected-main promotion.
# M045 / HVC003 — Gates 1+2 exact-head replay and 210-second mastering repair

**Date:** 2026-11-20 · **Owner:** SARA_studio (music authority, repo ID 1427534706)  
**PR:** #36 (draft, not merged) · **Baselined start:** `15b6d3f15fe2a122933133f34d43c7dc7aaba28c`  
**Main at execution:** `d6aa889a0def72bb8e1c87009a98d6c29e47067e`, unchanged.  
**Executor:** isolated KERNEL full exact GitHub source archive (287 ZIP entries; CRC PASS), Python 3.10.12, Node 22.23.2, system Chromium 156.0.8078.79, Playwright 1.56.1, real CPU FFmpeg n7.1.5.

## Baseline first (before any Gate2 mutations)

Full canonical Studio source archive from SHA above was unpacked and executed, not merely inspected. CI-pinned Playwright had to be installed in the ephemeral environment; an initial browser invocation without \`playwright\` failed at module import and is **not** represented as an application failure.

| Suite | Command | Result |
|---|---|---|
| Python | \`PYTHONPATH=tools:tests python3 -m unittest discover -s tests -p 'test_*.py' -v\` | **201/201**, 0 fail/skip |
| Node | \`node --test --test-concurrency=1 tests/*.test.cjs\` | **39/39**, 0 fail/skip |
| Chromium | \`CHROMIUM_PATH=/usr/local/bin/chromium node --test --test-concurrency=1 tests/*.browser.cjs\` | **21/21**, 0 fail/skip |

Baseline **261/261** independently executed at `15b6d3f1`. This supersedes the **previously supplied** 256/256 report because 5 HVC003 issuer tests were already in the head.

## Gate1: Real localhost HVC003 issuer verification

Added \`tests/test_m045_hvc003_http_endpoint.py\` (5 tests) against the **real \`StudioHandler\` TCP listener**:
- **503 BLOCKED** until host explicitly configures both \`HostSigningKeyRing\` and an independent rights callback.
- **403** for missing/invalid Studio session or missing host capability.
- **403** for wrong principal; **403** for a different project with exactly the **same physical CAS digest**; legitimate ownership cannot be inferred from CAS equality.
- **403** for caller-supplied sample coordinates; fail-closed.
- **200** with a genuine test-host-issued HMAC grant, exact decoded PCM sample bounds, unchanged authoritative current revision; signature tamper and revoked key rejection. Uses a **synthetic test-only cleared-rights callback**. This is not proof of actual artist licensing or production host configuration.

Added \`tests/m045-hvc003-grant.browser.cjs\` (1 Chromium test):
- Real 390px viewport, minimum 48×48 grant button, no horizontal overflow.
- Real unconfigured host 503 rendered as **NOT ISSUED**; fake client-side 200 used **only to verify truthful UI presentation** ("Film NOT created or verified").
- RED test confirmed an in-flight grant could leave stale "Checking" status after \`New Project\`. Minimal fix to shared \`m045Wave4Clear()\` invalidates the status under the existing canonical project generation token. GREEN confirms stale responses cannot impersonate current grant success.
- Existing R1 cold-reopen Chromium test intermittently observed HTTP response before browser WAV metadata decoding. Test now waits for **exact expected project/revision/artifact playback proof**, not merely any proof, before asserting. Full group rerun passed.

## Gate2: Full-length CPU mastered WAV (no GPU)

**Independent RED**: \`tests/test_m045_full_length_mastering.py\` failed twice against original 16 MiB / 75-second \`_validate_audio()\`.  
**Scoped GREEN**:
1. \`tools/m045_wave4_mastering_provenance.py\` now validates up to **210 seconds** of 44.1 kHz PCM16 WAV within **40 MiB**, walks audio frames in 65,536-frame blocks for format/completeness checks, and processes two-pass FFmpeg loudnorm + independent output metering in a temporary disk workspace. \`-threads 1\`, CPU only. This is **bounded-memory processing**, not a claim that the Python source and result are never held in bounded RAM.
2. \`tools/studio_server.py\` retains the original **16 MiB** ordinary export/untrusted-render ceiling. Only \`render_publish_operation\` invoked with a validated **host-constructed \`CanonicalProvenanceRecord\`** is allowed a 40 MiB master. No parallel CAS/project authority, no raw HTTP file-path ingestion, no bypass through client JSON.
3. Physically decoded an actual **210-second stereo** mastered WAV at 44,100 Hz and measured LUFS/true-peak, with independently checked digest. Tested the existing \`NOT_INDEPENDENTLY_CERTIFIED\` meter ceiling and under **850 MiB** process high-water constraint.
4. Authenticated an actual **180-second stereo** source into Studio's **existing** revision/CAS authority, mastered it with lawful \`authorized_master()\`, obtained immutable new revision/artifact, read both current and historical audio, and verified after a **fresh Python interpreter restart**. The historical original remains lawfully accessible and unchanged; mastering returns \`rightsStatus=UNVERIFIED_HELD\`, \`releaseCleared=false\`, P3—not fabricated artist approval or P0 preservation.

The host still needs to lawfully **ingest/generate 210s source audio**, independently attest SampleAsset/license rights, and configure actual grant signing. The generic 16 MiB JSON export/input path has intentionally **not** been widened. Thus **full-length CPU mastering of an existing authorized WAV is demonstrated**, not a complete artist-upload→commercial release pipeline.

## Exact post-change full regressions

| Suite | Evidence path | Result |
|---|---|---|
| Python | \`evidence/m045-gate12-20261120/python-full-208.log\` | **208/208** |
| Node | \`evidence/m045-gate12-20261120/node-full-39.log\` | **39/39** |
| Chromium M045 | \`evidence/m045-gate12-20261120/chromium-group-a-10.log\` | **10/10** |
| Chromium non-M045 | \`evidence/m045-gate12-20261120/chromium-group-b-12.log\` | **12/12** |
| **Total** | **All four raw logs committed and read back** | **269/269**, zero failures/skips |

Chromium was run in **two exhaustive, non-overlapping groups** to respect the bounded executor timeout. An intermediate 11/12 pass exposed the cold-reopen test race; the exact-identity wait was introduced and the entire second group rerun **12/12**. This intermediate failure is **not** suppressed or represented as a pass.

The following immutable TDD receipts are also in this directory: \`full-length-master-RED.log\`, \`full-length-master-GREEN.log\`, \`stale-grant-browser-RED.log\`, \`stale-grant-browser-GREEN.log\`, and \`http-grant-live-GREEN.log\`.

### Source readback identifiers (exact GitHub blobs)

| File | Expected verified Git blob |
|---|---|
| \`tools/m045_wave4_mastering_provenance.py\` | \`7989ff54fcaf77819b9b9d678b79b14fa68d4992\` |
| \`tools/studio_server.py\` | \`96c34bde7eb8c81993f26f5588663a3a6ffe4635\` |
| \`app-ui.js\` | \`f205ff433013c56bd438f8e31d541601067ea5dd\` |
| \`tests/test_m045_hvc003_http_endpoint.py\` | \`1b52b24e8c3dc9ef320b59f6089bb0fa19a29474\` |
| \`tests/test_m045_full_length_mastering.py\` | \`62d252cd9ff7018f4fda027de99a690a5fac4daa\` |
| \`tests/m045-hvc003-grant.browser.cjs\` | \`9b6d6e0c81b962c58ab78658cffe09cf7b0276f4\` |
| \`tests/r1-playback.browser.cjs\` | \`4542667db916ad0b9b52f3a82e9cb27a34bad8aa\` |

## Evidence ceilings and remaining owners

- **Full suite:** EXECUTED in KERNEL, not automatically **GitHub Actions CI** or production runtime. CI status must be inspected separately. Exact checked bytes were independently read back after branch writes.
- **Real Studio rights:** HOST CONFIG / LEGAL RELEASE HELD. Test-owner rights callback only; \`UNVERIFIED_HELD\` default does not become \`ARTIST_OWNED\` or \`LICENSED_FOR_CINEMA\` without rightful evidence.
- **Full-length ingestion:** source/upload/provisioning beyond legacy 16 MiB generic export still requires a safe owner-backed ingestion pathway; this mastering repair does not bypass it.
- **Cinema integration:** PulseForge owns visual revisions, seven actual engines, full 18-scene EQ semantic inventory, 021L independent film qualification, real artist approval.
- **No GPU credits, Modal deployment, production merge, release, or audio listening/creative approval** from this execution.

## JUSTIN 101

**WHAT CHANGED:** Full-length 210s mastering technical boundary, host-provenanced 40 MiB publication allowance, stale grant UI status fix, strengthened exact-identity cold-reopen test, 5 new HTTP + 2 new mastering + 1 browser test.  
**FAILED:** RED source limits (repaired), stale UI status (repaired), one flaky asynchronous baseline test assertion (repaired and full-group replayed).  
**PROVEN:** 261/261 baseline and 269/269 new-head executor tests, actual 210s master and 180s durable cold-reopen, 503/403/200 route behavior, signed synthetic grant, exact blob readbacks.  
**UNPROVEN:** real SampleAsset license registry, large authorized artist input, GitHub CI signoff, real hosted signer, independent meter certification, accepted real song and music-to-film approval.  
**TEAM NEXT:** Studio Work A owns source ingestion, rights, host configuration and CI; PulseForge owner owns real film binding and full G-EQ/021L qualification.  
**JUSTIN ACTION:** None to preserve this draft. Do not merge/deploy until owner approval gates are independently earned.

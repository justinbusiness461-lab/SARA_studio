# M045 — Native Integration Security, Durability and Proof Gate
**Campaign:** M045 / Full Capability Parity · **Date:** 2026-11-19  
**Disposition:** REVIEW / BLOCK DIRECT MERGE OF PROPOSED CODE · **Owner:** SARA_studio  
**Base:** created from live `main`; current source inspected: `tools/studio_server.py`, `scorecore.js`, `tools/scorecore.cjs`, `app-ui.js`, `app-cinema.js`, `tests/test_m044_r3_durability.py`, `tools/m042_project_probe.py`.  
**Source:** owner-supplied M045 GenerationOwner, SoundtrackIssuer, ScoreCore extension, benchmark, server bridge, subprocess runner and UI controller in DJ RezrXtion project conversation, 2026-11-19. No implementation files from the pasted proposal have been installed. **A review is not an execution receipt.**

## Exact owner mapping: reuse rather than duplicate
- `scorecore.js` declares that `app-core.parsePrompt` owns SongSpec and `tools/studio_server.py` owns ProjectRevision/ProductionTimeline. `tools/scorecore.cjs` only reexports the ScoreCore adapter. Do not promote a second owner by naming an adapter “canonical.”
- Server already has `atomic_write_bytes`, `durable_mkdir`, `project_json`, content-addressed objects under `objects/<prefix>/<sha>`, exact-origin capability handling, session principals, project/revision read and commit, and `render_publish_operation`. A new `blobs/sha256` tree is **not** an authorized additional CAS namespace without an explicit migration/ownership contract.
- Preserve four tiers: P0 exact non-target event identity; P1 exact unrelated PCM outside target + declared dependency/tail; P2 best effort isolation with risk and mandatory audition; P3 generative reconstruction with no exact preservation promise.

## Blocking defects and minimum repairs
| ID | Severity | Proposed code defect / failed boundary | Minimum lawful repair |
|---|---|---|---|
| M045-SEC-01 | P0 | `X-Sara-Principal` arrives from browser; `headers.get(..., "local-artist")` supplies default impersonation. Authentication ≠ caller-supplied identity. | Use server-validated session/capability → principal, enforce per-project authorization via existing read APIs, no guest default or user-controlled principal assertion. |
| M045-OWN-02 | P0 | Bridge assumes `manifest.owner_id`, `manifest.revisions` and `revision.accepted_artifacts`; M042 manifest is `projectId,currentRevisionId,formatVersion` and immutable revision records live under revisions/. | Call existing project's authorized manifest/revision/association reader, verify source revision ancestry, decoded audio, digest and lawful artifact membership; never deduce ownership by scanning CAS. |
| M045-JOB-03 | P0 | `execute_generation_job` commits, then writes COMMITTED; if latter fails or response is lost, blanket `except` writes FAILED after a committed revision. Idempotency key has no authoritative uniqueness or recovery fence. | Durable attempt identity before inference; unique (project, idempotency key) under lock; record validated artifact identity before CAS publication; publish+associate durably; reconcile on cold start; only optionally promote current with expected revision. Post-commit failure must be `COMMIT_UNCERTAIN` until authoritative reread, never blindly FAILED/retry. |
| M045-ART-04 | P0 | `_store_cas_blob` invokes replacement-capable atomic write on a digest path, no verified existing-object reuse, no durable job→artifact association, arbitrary new namespace. | Use canonical object publication/digest verification and R3 render attempt mechanisms; CAS existence is not authorization; no ownerless blobs; verify before and after publication. |
| M045-PROOF-05 | P0 | `Boolean(data.job?.output_blob_sha256)` sets UI `m045ProofVerified` and client updates current revision from response alone. | Track `COMMAND_ACCEPTED`, `REVISION_COMMITTED`, `ARTIFACT_VALID`, `AUDIO_PLAYABLE`, `CREATIVE_APPROVED` independently. Proof badge only after server-side authorized, decoded and read-back verified evidence with exact revision/artifact. Reread authoritative current after ambiguous response. |
| M045-LOCK-06 | P0 | `sonicLockedTracks` lives only in browser; client toggles cannot enforce a canonical lock. | Store locks in canonical versioned project/operation data; reject lock-breaking edits on server at expected-revision compare-and-swap; UI is a reflection. |
| M045-WAVE-07 | P0 | `verify_physical_wav_bytes` sets `decoded_verified=True` using container metadata and `readframes`, without validating sample width/length, sample amplitude/sanity, all stems' exact length/channel alignment or independent readback. | Validate frame-byte count, PCM encoding and channel/rate constraints; for accepted audio compute digest of decoded PCM (with sample format metadata); compare stems to master timeline, independently reopen finalized CAS and fully decode; gate duration, peak, NaN if floating formats admitted. |
| M045-SEC-08 | P0 | `signing_secret` defaults to public `dev-local-loopback-secret`; grant lacks audience/capability scope and consumer verification/renewal/revocation contract. | Never issue trust grants from a default secret; provision/rotate key securely; include audience, scope, expiry, project/revision/artifact IDs; explicitly qualify the consuming PulseForge verifier. For local-only prototype, refuse external grants. |
| M045-TIME-09 | P1 | `deriveSampleWindowFromBars` uses JS Number floor/ceil, not zero-float rational arithmetic; `endBar` inclusive may disagree with half-open ProductionTimeline. | Bind to actual timeline ticks, tempo/meter map, sample-rate and revision; BigInt/Fraction rational conversion, explicit half-open range. Validate noninteger tempos, tempo changes, 30000/1001, edge boundaries and half-open identity. |
| M045-RUN-10 | P1 | Timeout and `CUDA_VISIBLE_DEVICES` do not enforce VRAM or sandboxing; worker may spawn children, create symlinks, output huge WAV, exfiltrate prompts, and spoof model capabilities or cost. | Constrained worker identity/network, process-group kill, output size limits, anti-symlink opens, effective GPU memory budget + OOM handling, checked model checkpoint/digest/license/weights, separate independent telemetry validation. |
| M045-CAST-11 | P1 | `supports_stems=True`, `supports_lyric_alignment=True` hardcoded; provider_id and license prefix derive provenance / tiers. | Capabilities and licensing are qualified against a model/checkpoint and actual output; origin is separately authenticated, never inferred from a license string. Generative stems are not inherently P0/P1. |
| M045-UI-12 | P1 | Standalone `export class` proposed for script-style `app-ui.js`; `app-cinema.js` is local 3D viewport, not canonical remote PulseForge consumer. Stale UI token is not server authority. | Use existing UI module format/events, test DOM/actual HTTP, preserve transport-generation race checks, and build an explicit cinema adapter contract owned by dj_rezrxtion before connecting projects. |
| M045-BENCH-13 | P1 | Flagship mock fixtures use non-hex "sha_r1_master"/"pcm_digest" and 8,823,830 frames for 72 bars @94 BPM/48kHz (exact count differs); they don't test real rights, auth, decode, or provider execution. | Derive musical windows from server timeline; test real valid 64-hex digests and decoded files; verify exact sample count. WER without independently aligned/reference audio cannot be a certification. |

## Quantitative discriminator: timebase
At constant 94 BPM, 4/4, 72 bars last `72*4*60/94 = 8640/47` seconds ≈ 183.829787234s; at 48,000 Hz exact endpoint is `414720000/47` samples ≈ 8,823,829.787, thus ceiling = **8,823,830**. The fixture's total count is plausible *if* a ceiling policy is adopted, but embedded section sample coordinates must be derived from the *same* reference timeline. Do not hard-code inferred ranges as authority. An earlier 88-bar case is 224.68s and outside the requested 2.5–3.5min benchmark.

## Mandatory RED tests before application wiring
1. **Header impersonation:** valid session principal A plus `X-Sara-Principal:B` must never read/grant/commit B's project. Missing session must deny.
2. **Forged CAS:** correct digest from another project, orphan CAS, and artifact after detached revision must all be denied. Historical R1/A1 remains lawful after R2/A2 current, only for authorized principal.
3. **Job uncertainty:** inject crash at (a) job identity durable, (b) decoded object validated, (c) CAS publication, (d) historical association, (e) current promotion, (f) after promotion before COMMITTED job marker, (g) HTTP response lost. Cold read must give exactly one lawful owner association and never duplicate generation/incorrectly mark failed.
4. **Locked edits:** browser-side unlock or forged JSON must not bypass canonical Sonic Lock; locked non-target event IDs and bytes remain immutable.
5. **Media:** truncate data chunk, mismatch declared length, bad sample widths, too-big output, stem timeline mismatch, digest mismatch, corrupted CAS and malformed WAV; no publication or proof PASS.
6. **Timing:** exact half-open boundaries including tempo/meter changes, negative ranges, zero length, 30000/1001 fps, section discontinuities, start-frame floor/end-frame ceil without overclaiming musical alignment.
7. **Provider:** unlicensed/missing checkpoint, unsupported stems or vocal capabilities, VRAM overrun, runaway child worker, external network attempt and spoofed telemetry fail closed.
8. **UI:** stale R1 result after R2 selection must never replace A/B transport or any proof badge. UI-reported job success cannot advance ProjectManifest.

## Implementation order, no parallel authority
**RED adversarial tests → existing schema/API map → durable GenerationAttempt adapter over R3 render/publish owner → actual media readback and provider qualification → legitimate principal-bound soundtrack grant → existing UI state adaptation → real device tests.** 
Use one uniquely named source branch, independent qualification, and merge only after tests and exact source/artifact readback. Distinguish SOURCE, TESTED, INTEGRATED, EXECUTED, PHYSICALLY_VERIFIED, CREATIVELY_APPROVED, RELEASE_READY. No blanket PASS.

## Responsible owners and wake
- **Music authority/durability, M045 generation job:** `SARA_studio` — executable gate pending authenticated adapter and fault injection.
- **Cinema grant consumer and shot use:** `dj_rezrxtion` — cannot claim full handoff until consumer verifies signed grant, audience and immutable audio association; preserve current/historical distinction.
- **Model licensing/weights and audio QA:** candidate checkpoint exact digest, license and real WAV/independent listening needed for promotion.
- **Artist:** no decision required for this security repair. Approval remains separate for sound and creative results.

## JUSTIN 101
**CHANGED:** reviewable source-specific blocker matrix and RED-test design, no shadow authority.
**FAILED:** provided code cannot safely mount as production routes.
**PROVEN:** checked-in source owner interfaces, incompatible manifest assumptions, unsafe user-supplied principal, fabricated client proof and ambiguous post-commit failure handling. Benchmark arithmetic verified analytically.
**UNPROVEN:** real GPU job, authorized soundtrack handoff, latency/cost, audio quality, mobile behavior and release.
**TEAM NEXT:** turn the first P0 into RED tests, implement narrow adapter over existing R3 owner, verify exact SHAs/physical readback.
**JUSTIN ACTION:** None for engineering safety gate; no need to choose model before native owner qualification.

# M044 / MANUS NASA-003 — G3 owner-reviewed revision-bound WAV bridge

**Date:** 2026-11-10  
**Disposition:** HARDENING_ADVANCE / G3 IMPLEMENTATION PROPOSAL — **NOT** real-audio bridge certification.  
**Target owner:** Sound Forge M044 for canonical audio/project contract; Manus studio owner for authenticated consumer adapter.  
**Mutation lease:** documentation only. No product engine, Manus runtime, PR #11, governance, or Forge mutation authorized by this document.

## Refresh pins and evidence boundary

- Sound Forge main observed at `14e2fb9cc55c8ce2909803a66d509915a18eb625`; PR #10 is merged; PR #11 remains open on `bobby/m044-scorecore-foundation`, head `cb80d4fe06cc1148651787872ad89216c20328f3`.
- Canonical backend read: `tools/studio_server.py` blob SHA `4b044628187a94ab2a80db818bccb84b9fd1518a`; session client: `tools/m044-session.cjs` blob SHA `d8fe314c43e04acf291427bbabc33e484571664d`.
- Mainline engine proof: `docs/audits/PF_MISSION_044_MAINLINE.md`, blob `32014f607375d6021e7016f547a59b6e07a7bdbf`; reported 46/46 Python, 8/8 Node, bounded integration WAV proof. Not an independently executed test in this round.
- DJ RezrXtion Forge main `cd8997c260f552d28c1230d16954a59203a78d57`; organization governance main `f45ae27df34c9b53507bff653b59258f05eac020`.
- User-provided Manus checkpoint: **local** `f9c2a98495ca7a4b5f995ed8adee4f87a6c6629b`, branch `manus/nasa003-auth-bridge`; authenticated ownership 13/13 reported PASS. **Not fetched** from managed Manus workspace or independently re-run. The paths `/home/ubuntu/sarastudio/evidence/manus-m044-nasa003/...` are Manus-local paths and are **not** GitHub evidence links.
- Live Manus dev server is reportedly stopped. A stopped preview does not establish loss of committed source but live preview is UNVERIFIED.

## Specific first G3 blocker: no authorized artifact read path

The existing canonical server **does** have:
- `POST /api/projects/commit` and `POST /api/projects/open`, via `project_operation`;
- `POST /api/write_production_file`, returning content-addressed `sha256`;
- `artifact_bytes(root,digest)`, which confirms object existence and SHA-256, internal to the authoritative store;
- `project_revision(...)`, which checks immutable `revisionId`, `songSpecDigest`, `productionTimelineDigest`, and referenced artifact bytes;
- `validate_render_audio(root,digest)`, which checks actual WAV/PCM16 structure before historical render admission;
- `tools/m044-session.cjs` orchestration that generates/renders/edits through existing owner code.

The existing `do_GET` route serves the Studio page and fixed static assets; it does **not** expose a revision-authorized, user-owned WAV download/stream endpoint. `project_result` exposes metadata and revision bindings, **not the WAV bytes**. The engine expects loopback-only local origin + private `X-Studio-Capability`, not public multi-user authentication.

**DO NOT** solve this by exposing `/workspace`, storage paths, CAS directories, the engine capability header, or a generic `GET /objects/{digest}`. A hash is not authorization; the browser must not call the local Sound Forge authority directly.

## Smallest lawful architecture

`Authenticated Manus user` → `Manus server-owned project binding` → `private trusted bridge` → `existing Sound Forge project/revision/audio owner` → `verified WAV bytes` → `authenticated browser transport`.

Sound Forge stays the source of truth for `ProjectManifest`, immutable `ProjectRevision`, `SongSpec`, `ProductionTimeline`, `outputArtifactIds` and historical output bindings. Manus owns only its authenticated tenant mapping and application view state. No shadow revision counter. Friendly `R1/R2` labels are UI projections over actual SHA-256 revision IDs.

**Recommended first slice:** implement a narrow, private **server-side** adapter at the Manus runtime boundary, consuming a pinned canonical Sound Forge checkout on the same trusted execution host. Keep the existing Sound Forge server loopback only. If the two apps do not share a trusted host, HOLD until an explicit secure service-to-service transport and owner-reviewed deployment architecture are chosen; do not open the engine's local port publicly.

**Minimal owner approval needed:** a read-only, explicitly scoped artifact accessor owned by Sound Forge, either:
1. A private in-process module that returns `artifact_bytes` *only after* validating the canonical project/revision/output association, or
2. A narrow loopback private authenticated endpoint with equivalent binding checks.

The returned identifier must be `{projectId, sourceRevisionId, artifactDigest, kind: current|historical, bytesSha256, mimeType: audio/wav, sampleRate, channels, frames}`. Caller identity is bound by Manus auth before requesting the adapter; the Sound Forge adapter must verify that requested artifact is actually attached to the requested qualified revision and user-bound project, not merely present in CAS. No browser-visible capability, secret, filesystem path, raw tenant ID or object directory.

**Existing source authority:** `project_revision(root,directory,pid,rid)` and `historical_result(...)` already mediate immutable revisions and historical render associations. Reuse them, including `reconcile_historical_renders`. A historical late-R1 WAV remains associated with R1 and never becomes R2 current audio. `ProjectManifest.currentRevisionId` alone selects current authority.

## Proposed Manus-facing contract (NOT an existing route)

An authenticated private app endpoint may be shaped as:

`GET /api/studio/projects/:appProjectId/revisions/:canonicalRevisionId/audio/:artifactDigest`

This is **PROPOSED**, not a verified current endpoint.

Request authorization sequence:
1. Check a live authenticated principal. Anonymous fails **401** before metadata disclosure.
2. Look up `appProjectId` under the server-derived principal; absent/foreign both **404** (same response shape and no metadata leakage).
3. Resolve the server-held mapping to canonical Sound Forge `projectId` (`[a-f0-9]{32}`). Reject any browser-controlled canonical project/store path.
4. Read the exact requested canonical revision (`[a-f0-9]{64}`) and prove it is in that project's committed ancestry. Validate latest vs historical output binding, including pending-recovery reconciliation under canonical owner rules.
5. Require `artifactDigest` (`[a-f0-9]{64}`) to be a lawful output attached to that exact revision or qualified historical output for that source revision; reject arbitrary digest and stale cross-revision substitution.
6. Verify stored bytes via canonical digest and actual WAV decoder/validator. Do not infer playable audio from file extension or hash.
7. Stream bytes via server with `Content-Type: audio/wav`, correct byte length, `Cache-Control: private, no-store` until an audited cache key exists. The response may expose canonical `X-Audio-SHA256` only if CORS and privacy controls allow; never expose engine capability.
8. Record bounded request metrics and an audit receipt without recording tokens, private raw audio content, or full personal identifiers.

For **render writes**, use existing `m044-session.cjs` `generate/render/edit` and canonical project APIs only through the private service. The adapter must carry `expectedCurrentRevisionId` and a stable server-generated `operationId` through faults and retries. A stale render cannot auto-rebase onto the new current revision.

For **historical reads**, no extra ProjectRevision is created and no manifest pointer is moved. If a historical artifact cannot be admitted or decoded, return an explicit unavailable state and disable playback; never synthesize substitute audio or present oscillator preview as real A/B.

## RED acceptance matrix (must visibly fail before GREEN implementation)

| ID | Fault / operation | Expected outcome |
|---|---|---|
| G3-01 | Anonymous calls proposed audio route | 401, no artifact bytes |
| G3-02 | User B requests User A's appProjectId | 404, no metadata, same outward shape as missing |
| G3-03 | User B guesses a real digest from User A | 404, no byte leak |
| G3-04 | Authenticated User A requests nonexistent revision | 404/409 bounded contract, no bytes |
| G3-05 | User A requests real digest bound to *another revision* | Fail closed; no cross-revision substitution |
| G3-06 | Digest exists in CAS but is not project-bound | Fail closed; no raw CAS read |
| G3-07 | .wav name with random/invalid RIFF bytes | Reject; zero playback evidence |
| G3-08 | Truncated WAV or bad RIFF length | Reject; no partial playback mislabeled valid |
| G3-09 | Wrong artifact checksum | Reject; no byte stream |
| G3-10 | Valid actual current R2 WAV | SHA+PCM decode PASS, source revision R2 |
| G3-11 | Valid late R1 historical WAV while R2 current | R1 retrieval PASS, R2 current unchanged |
| G3-12 | Crash between durable artifact and historical binding | cold restart reconciliation; no caller replay |
| G3-13 | Rapid R1/R2 A/B toggle | real distinct authorized files; no misleading metadata-only audio |
| G3-14 | Two simultaneous edits with stale expected revision | one lawful commit, one 409; no duplicate |
| G3-15 | Process restart, empty browser cache | exact latest spec/output and R1 history recovered |
| G3-16 | Malicious pathname, symlink, traversal, oversized request | fail closed; no storage escape |
| G3-17 | Engine capability accidentally included in browser HTML/JSON/log | security test FAIL; must never occur |
| G3-18 | Distinct User A/B projects concurrent | isolated reads, writes, artifacts and logs |
| G3-19 | Engine not started/restarted | honest retryable unavailable state; no false success |
| G3-20 | Same rendered operation replay, different payload | canonical conflict; never auto-rewrite retained history |

Do not mark this matrix PASS based on mock server, static types or screenshots. Record RED then GREEN test logs, real two-user requests, actual SHA-256 WAV bytes, physical decode data, browser network traces with secrets redacted, exact checked out SHA, cold process restart evidence, and performance budget/resource measurements.

## Serial execution, boundaries and promotion

**G1 source preservation** — save/verify Manus local `f9c2a98...` with a clean tree and exact file digests in a remote branch or export; **UNVERIFIED remotely now**. Never overwrite this with the earlier ZIP.

**G2 authenticated tenant owner** — Manus reports PASS 13/13; independent cross-user readback needed before promotion.

**G3 real media bridge** — Owner approval of narrow artifact accessor, then RED/GREEN for G3-01..20; no production release if auth or WAV fails.

**G4 actual user journey** — sign in → Generate → canonical R1 → render WAV A → listen → scoped bass edit → canonical R2 → WAV B → real A/B → close/restart/reopen.

**G5 product adversary** — mobile and desktop share same state, no silent fallback, stale UI states, failed audio, historical read during render, preserved unrelated section, rights state.

**G6 Forge follow-through** — only after G3/G4, assess MUS-004/006/008 and Sample Creator against canonical Forge. Research leads do not equal implemented features.

PR #11 is Work A's cone: do not rewrite/retarget it from this document. No changes to Bobby's merged audio/revision authority. Any new Sound Forge retrieval endpoint requires owner-specific review and independent security qualification before Manus consumes it.

## First actionable owner review question

**Can Sound Forge expose exactly one verified read-only artifact-by-(project,revision,digest) accessor on its existing local trusted boundary, reusing current `artifact_bytes` + `project_revision` + historical association checks, without broadening the public engine API?** If yes, implement that one seam test-first. If no, document the precise deployment/trust limitation and hold G3. Do not create another store or credential path.

## Findings

| Severity | Evidence | Owner | Impact | Blocker | Next action |
|---|---|---|---|---|---|
| P0 | Canonical HTTP GET allows fixed static assets; `project_result` returns metadata only | Sound Forge M044 owner | No safe revision-bound WAV retrieval for Manus | G3 | authorize and qualify narrow private artifact accessor |
| P0 | Existing engine origin/capability is for loopback-local use | Manus adapter + Sound Forge | Public forwarding would bypass tenant model | G3 | bind verified user to app project, keep engine capability server-only |
| P1 | Manus local `f9c2a98...` receipt not independently available | Manus executor | Potential lost/divergent auth changes if reimporting | remote continuity | push/export exact checkpoint before further mutation |
| P1 | PR #11 targets older Bobby base | Work A/B | Browser Generate integration not final on main | UI edge | owner-controlled retarget and QA |
| P1 | Historical output identity differs from current manifest pointer | Work C/D | Wrong A/B audio or current rollback | physical proof | test G3-10..15 against actual PCM |

## JUSTIN 101

**WHAT CHANGED:** exact source-backed G3 seam and negative-test contract recorded on a documentation-only branch.  
**WHAT FAILED/BLOCKED:** direct Manus filesystem/auth checkpoint access and owner approval of audio read seam.  
**WHAT IS PROVEN:** current canonical route inventory, digest/manifest owner path and mainline receipt existence; not G3 implementation.  
**WHAT IS NOT PROVEN:** actual authenticated multi-user download, real hosted browser playback, deployed app, product parity.  
**WHAT JUSTIN MUST DO:** no routine step at this point; the Sound Forge/Manus owners must agree the narrow artifact accessor and run the tests.

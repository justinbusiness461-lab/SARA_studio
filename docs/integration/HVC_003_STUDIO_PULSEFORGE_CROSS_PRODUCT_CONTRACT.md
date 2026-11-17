# HVC-003 — S.A.R.A. Studio ↔ PulseForge Joint Build Contract (Studio Owner)

**Disposition:** PROPOSED DESIGN / NOT IMPLEMENTED / NOT CERTIFIED
**Date:** 2026-11-17
**Studio canonical owner:** justinbusiness461-lab/SARA_studio (repo ID 1427534706)
**Cinema canonical owner:** justinbusiness461-lab/dj_rezrxtion
**Inspected Studio baseline:** main at d6aa889a0def72bb8e1c87009a98d6c29e47067e
**Companion:** PulseForge HVC-001/HVC-002 PR #72; Studio docs/M044_STUDIO_CALLABLE_MAP.md and docs/M044_BOBBY_R3_RENDER_DURABILITY_HANDOFF.md

## 1. Operator decision

**Build both applications hand in hand as one artist-facing workflow.** S.A.R.A. Studio creates, edits, preserves, authorizes, and proves music. PulseForge builds the film, scenes, seven visual modes, renders, and visual revisions. Both can display and control their respective parts of one connected operation. Neither owns the other's history/currentness. Avoid duplicating music authority or inventing shared database truth.

CHAT = COMMAND. CANVAS = CREATION. WORKSTREAM = EXECUTION. PROOF = TRUST.
TARGET → PRESERVE → IMPACT → REVISE → PROVE.
COMMAND ACCEPTED ≠ MUSIC REVISION COMMITTED ≠ AUDIO PLAYABLE ≠ VISUAL REVISION COMMITTED ≠ MOVIE VALID ≠ CREATIVE APPROVED.

Studio owns SongSpec, ProductionTimeline, ProjectRevision, ProjectManifest.currentRevisionId, LyricTimelineRevision, SampleAsset, music RenderAttempt, music RenderArtifact, accepted audio, and authorization to read it. PulseForge owns VisualAsset, VisualRevision, VisualOperation, VisualProof, VisualApproval, cinema render and current film selection.

## 2. As-built qualification limits

Inspected Studio main includes canonical project/open/commit, immutable lyric revisions, local session/principal/project authorization and validated revision-bound audio. These do NOT establish an externally callable inter-app service, hosted SSO, cross-origin export, signed cinema grant, qualified automatic DJ event extraction or full video support. The main callable map explicitly differentiates local draft playback and revision-bound audio. The following is an implementation proposal, not a claim of shipped APIs.

## 3. Studio-owned AcceptedSoundtrackDescriptorV1 (candidate schema)

```typescript
type AcceptedSoundtrackDescriptorV1 = Readonly<{
  schemaVersion: 1;
  owner: "SARA_studio";
  studioProjectId: string;
  sourceProjectRevisionId: string;
  acceptedAudioArtifactId: string;
  containerSha256: string;
  decodedPcmSha256: string;
  pcmEncoding: string;
  sampleRate: number;
  channels: number;
  pcmSampleFrames: number;
  productionTimelineRevisionId?: string;
  lyricTimelineRevisionId?: string;
  djEventGraphRevisionId?: string;
  soundRightsRef: string;
  descriptorDigest: string;
}>;
```

**Authoritative issuer:** Studio alone. This is a permission-checked immutable read descriptor, not a portable bearer authorization or film current pointer. Audio digest alone never authorizes another project. All fields are subject to implementation/schema review.

**Proposed issuer operations (NOT currently deployed):**
- issueAcceptedSoundtrackBinding(principal, studioProjectId, revisionId, audioArtifactId, cinemaProjectId, intendedUse): revalidate session/project/revision/artifact/rights; issue a scoped, expiring, audience-bound grant and descriptor.
- streamAuthorizedAudio(grant, exactSampleSpan): reauthorize before bytes; verify revision membership, digest and media validity.
- readQualifiedMusicObservations(grant): read existing approved lyric and ProductionTimeline evidence; include confidence and origin. Do not call heuristic beat/section recognition certified.
- requestStudioMusicOperation(principal, projectId, expectedRevisionId, operationId, target, preservationClass): Studio owner handles music edits; cinema may only PROPOSE a request.
- inspectStudioOperation(operationId): reconcile ambiguous completion without blind retry or ownerless CAS.
- emitAcceptedAudioRevisionEvent(revisionId, audioArtifactId, acceptanceState, correlationId): informational outbox; NEVER promotes cinema current.

**Trust order:** authenticated principal/session → Studio project authorization → revision membership → lawful revision-to-audio binding → immutable identity/digest → media validity → stream. Cross-product integration requires an independently reviewed service-to-service identity model, not reuse of local loopback session assumptions.

## 4. Music timeline contract

Global decoded PCM sample coordinate is truth. For audio rate SR and film rate FN/FD, frame f starts at floor(f*SR*FD/FN). A film's final sample boundary is clipped to exact decoded N. No approximate MP4 duration or scene-local timer can control musical phase.

Studio provides qualified source and timing evidence. PulseForge creates its **own read-only music observations** for visuals and one AudioFeatureBus whose indexed values are referenced by all blue trails, equalizers, lighting and particles. Studio does NOT own visualizer frame states; PulseForge cannot modify SongSpec or the original PCM in order to animate them.

Word-level lyric observations retain Studio LyricTimelineRevision identity and confidence. Real beat-locked DJ performance events are used only when present/qualified; no fake performer provenance.

## 5. Full interactive workflow — both products

| Artist request | Studio commits or exposes | PulseForge commits or exposes |
|---|---|---|
| Make a song | SongSpec, ProductionTimeline and audio candidate; only Studio selects/accepts music | none yet |
| Make a music video | accepted R1/A1 exact descriptor and lawful streaming | film V1 binds exact R1/A1; Hybrid Director, characters and modes |
| Show 15s preview | immutable 15s sample window from accepted source | derived 15s visual render without altering film authority |
| Animate every blue equalizer | audio samples/qualified cue evidence | bind ALL reactive entities to one global sample-addressed bus |
| Change the bass in verse two | create, render, verify and artist-accept Studio R2 | film still binds R1 until artist explicitly selects R2 |
| Update the film to accepted R2 | reauthorize and publish exact R2/A2 descriptor | derive V2 candidate, selectively invalidate dependent shots, require creative review |
| Change character clothing only | never mutate audio | scoped VisualOperation, impact proof; keep soundtrack bound |
| Publish | verify music authorization/rights | decode complete film, visual QA and separate artist approval |

Suno screenshots demonstrate user-facing tasks (song selection, 15s segment, characters, reference images, first/last frame, image/video/sequences and cover art); do not equate screenshot existence with verified render quality. Product goal is to exceed workflow editability/preservation, not copy proprietary layouts.

## 6. Inter-repository reliability protocol

A distributed saga, not one global ProjectRevision or pretend ACID transaction:
1. Studio commits and durably associates R1 audio A1. Artist accepts.
2. Studio issues scoped descriptor after authorization.
3. PulseForge creates film V1 bound to R1/A1, renders, physically verifies and requests artistic approval.
4. Studio may later create accepted R2/A2; PulseForge marks it AVAILABLE but DOES NOT promote it into current film.
5. If artist explicitly requests rebinding, PulseForge opens proposed V2, computes impacted dependency spans, selectively renders/proves, then promotes only via expected-visual-revision CAS.
6. Late R1/late V1 completions remain lawfully historical and cannot replace current R2/V2.

All handoffs carry correlationId, idempotencyKey, Studio sourceProjectRevisionId, exact audio artifact ID, expected VisualRevisionId when applicable, contract version, event receipt and authorization context. Under ambiguous failures, resolve authoritative state in BOTH domains before any retry.

## 7. Coordinated gates and independent proof

- JOINT-0: pin both exact main SHAs and current PR heads; owner and asset-rights inventory.
- JOINT-1: schema + Studio issuer + strict cinema consumer; reject cross-project same-digest authorization.
- JOINT-2: right-audio-right-sample-position; shared global AudioFeatureBus and cross-scene equalizers.
- JOINT-3: seven visual adapters and Hybrid Director consume exact music identities.
- JOINT-4: edit Studio R1→R2 without changing film V1 automatically; choose V2 through explicit operator decision.
- JOINT-5: cold restart, late historical rendering, CAS owner checks and network/transport fault injection.
- JOINT-6: unified chat/guided/pro creative UI commands with mobile parity and distinct proof stages.
- JOINT-7: independent full physical film decode, rights and artist creative approval before release.

Test fixtures must include two different Studio projects with identical PCM digests, revoked grants, forged browser artifact IDs, correct file at wrong musical position, an R1 render finishing after R2, and V1 completing after visual V2 selection. No top-level PASS overrides failed physical evidence.

## 8. Owner-disjoint implementation

**Studio owner / Cody/Bobby lanes:** version the descriptor, implement authorized issuer and audio read using existing Studio project/lyric/render authorities, write RED tests on exact Studio tree. No cinema VisualRevision or 3D engine code.

**PulseForge owner:** consume issuer through versioned adapter; implement seven visual engines, Hybrid Director, visual currentness, compositor, proof and film UI. No SongSpec/ProjectManifest duplication.

**Independent QA:** exact dual-SHA contract tests, fresh-process recovery, security attacks, timing and physical decoding.
**Artist:** approves actual creative/audio-master switch; no automatic film promotion.

**State:** SPECIFIED ONLY, no runtime mutation, audio rendering, dual-app UI, automated QA execution, release or merge is implied.

## JUSTIN 101

WHAT CHANGED: Studio-side shared development contract and coordinated gates specified; Studio music authority remains intact.
PROVEN: inspected source/contract boundaries and exact baseline, not end-to-end running integration.
UNPROVEN: issuer API, cinema consumer, 7-engine integration, deployed authorization, creative acceptance.
TEAM NEXT: Studio owner assess issuer against current source; cinema owner implement separate consumer after joint contract freeze.
JUSTIN ACTION: none for design review; approval required before accepting a new film soundtrack.

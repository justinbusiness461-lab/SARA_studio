# HVC-003A — JOINT-1/JOINT-2 Studio Issuer and Cinema Proof Boundary

**Disposition:** Studio-owned contract addendum / NOT AN IMPLEMENTED API OR CERTIFIED FILM  
**Date:** 2026-11-17  
**Studio owner:** justinbusiness461-lab/SARA_studio (repo ID 1427534706)  
**Cinema owner:** justinbusiness461-lab/dj_rezrxtion  
**Studio baseline inspected:** main d6aa889a0def72bb8e1c87009a98d6c29e47067e  
**Companions:** Studio PR #29, PulseForge PR #72; cinema's unmerged PF-CINEMA-021C independent six-RED source audit [PR #84](https://github.com/justinbusiness461-lab/dj_rezrxtion/pull/84).

## 1. Review disposition

**ACCEPT THE DIRECTION / HOLD RUNTIME QUALIFICATION.** Prioritize joint first light: one authenticated, Studio-accepted music revision plus its exact audio artifact, one immutable cinema-owned VisualRevision, one 15-second hybrid render using Resurrection Vinyl + Living Lyrics + Hypnotic Soundworld, and independently measured decoded-media proof.

The studio emitter must not certify the video; its scope is the authorized soundtrack issuer and qualified musical observations. PulseForge's verifier cannot manufacture "PHYSICALLY_VERIFIED" from supplied metadata. No automatic acceptance or replacement of selected film soundtrack when Studio advances R1→R2.

## 2. Studio issuer contract — mandatory acceptance properties

Studio-issued descriptor and scoped grant are valid only after:

1. Caller principal/session authentication and project ownership/authorization.
2. The requested sourceProjectRevisionId is in canonical Studio history and its exact acceptedAudioArtifactId is lawfully associated with that revision. Cross-project same-digest reuse is DENIED without independent authorization.
3. Source bytes and decoded PCM metadata/digest are checked against durable records; exact sample count, sample rate, encoding/channels and access restrictions are preserved.
4. Audience and intended cinema project, expiry/revocation, rights and operation ID are bound to issuance. Cinema cannot turn an untrusted browser-supplied ID or CAS digest into an authorization token.
5. Observed lyrics and DJ performance events include precise revision identity and qualification state. Instrument/beat/cue heuristics are labeled as evidence of their true tier, never promoted to verified performer data.
6. Every ambiguous timeout/retry resolves authoritative Studio revision, RenderAttempt and artifact association first. Idempotency and late historical R1 outcomes may never rewrite current R2.
7. Studio's artist-facing "Create Visuals" request supplies accepted R1/A1, exact global decoded PCM sample window and correlation receipt, not merely an MP3 upload or approximate timestamp.

The first Studio test should issue the binding and read the exact accepted 15-second sample window with independent byte identity and cross-project 403/deny negative cases. A service-to-service principal model needs explicit qualification; the current local loopback capability does not itself prove hosted interoperability.

## 3. Cinema independent proof required before Studio displays "verified"

The attached cinema QA [PR #84](https://github.com/justinbusiness461-lab/dj_rezrxtion/pull/84) reports six remaining source-level false-PASS routes: fabricated EQ measurements with real media, invented 17 seam measurements using a 19-second S15 clip, unmeasured legacy removal, forged final gates/artist approval, reuse of G-EQ from another media candidate, and self-selected HVC verifier/measurement JSON.

This source-level finding is an unmerged risk report, **not** proof that a commercial master was actually falsely certified.

Studio-facing cinema status must come from the cinema-owned independent verifier, which must:
- Resolve exact authorized cinema VisualRevision, candidate artifact, immutable accepted music binding, global sample span, render profile and media digest.
- Decode actual media and produce its own frame-by-frame target movement/timing, seam, absence/preservation and audio-position measurements.
- Use immutable 18-scene target inventory where required by existing VIDEO-001 film; distinguish pilot scope from full-film scope.
- Refuse caller-authored PASS flags, measurement JSON, self-selected verifier identities, unauthenticated approval, and evidence from a different candidate SHA.
- Return separately typed execution, physical validation, technical certification, artist creative approval and release readiness, with false/missing evidence never coerced to PASS.

The exact VIDEO-001 historical full-film gate cited in PR #84 requires 18 scenes, 17 transitions and 7,114 frames **of the same full candidate**, after G-EQ and G-REMOVE and post-removal G-EQ recheck. That is a film-specific required coverage claim to independently reconcile with current VIDEO-001 manifest; it is NOT the frame count for every DJ RezrXtion movie.

**Forbidden Studio UI:** Showing an unverified 15-second preview or arbitrary JSON "PASS" as a fully certified movie, or labeling a PulseForge film V2 current after only Studio music R2 changed.

## 4. Cross-product test matrix

| Test | Required behavior |
|---|---|
| ST-ISSUE-001 | Studio R1/A1 authorized project issues exact bounded descriptor |
| ST-ISSUE-002 | Unknown principal, stale grant, wrong project (even identical digest) denied |
| ST-ISSUE-003 | PCM sample-offset requests return right audio at right musical position |
| ST-ISSUE-004 | Studio R2 accepted → cinema V1 keeps R1 until explicit film-binding operation |
| ST-ISSUE-005 | late R1 RenderAttempt becomes lawfully historical but cannot select R1 as current R2 |
| ST-PROOF-001 | cinema returns authentic source-bound decoded measurements, not self-minted JSON |
| ST-PROOF-002 | 15s three-mode preview is visually and sample-linked measured; not called full-film proof |
| ST-PROOF-003 | reported VIDEO-001 full 18/17/7114 has independent same-candidate proof before release label |
| ST-PROOF-004 | explicit artist creative approval not inferred from technical PASS |
| ST-PROOF-005 | failed cross-product handoff/restart yields held/reconcilable states, not optimistic success |

## 5. First implementation order

Studio owner: issuer schema → principal/project/revision/artifact tests → scoped 15-second audio read → outbox/idempotency & status query. Cinema owner: strict consumer → global clock and 3-mode pilot → independent decoded verifier → VisualRevision V1/V2 selective rebind/recovery. Independent QA: wrong-audio-time, forged metrics, fabricated seam and approval, cross-revision authorization, restart and ownership attack matrix.

**Certification status:** DOCS ONLY / NO RUNTIME PASS. Studio must not copy cinema VisualRevision or own cinema certificate. Cinema must not write SongSpec or Studio ProjectManifest.

## JUSTIN 101

CHANGED: a verifiable Studio-side first-light issuer/physical-proof boundary and negative test contract.
PROVEN: repository docs and PR #84 source-level audit inspected; no new runtime tests run.
UNPROVEN: service issuance, real inter-app stream, physically verified 15s clip, full-film coverage and creative approval.
TEAM NEXT: Studio owner freeze issuance, cinema owner freeze consumer+verifier; independent tests bind both exact immutable identities.
JUSTIN ACTION: none for architecture; creative acceptance always belongs to artist.

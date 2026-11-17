# HVC-004 — Studio Music-Issuer Double-Time Execution Order
Date 2026-11-17. Status: DRAFT INTEGRATION ORDER; not a deployed issuer, accepted-media transfer, film verification or artist approval. Companion canonical cinema coordination: dj_rezrxtion PF-CINEMA-022 draft PR #87, with 12 worker roles including Work E and Codex.

## Owner contract — Studio is music authority
SARA_studio owns SongSpec, ProductionTimeline, ProjectRevision, ProjectManifest.currentRevisionId, accepted RenderArtifact association, lyric/DJ sample coordinates, project authorization and media rights. Cinema owns VisualRevision and visuals; it must not promote Studio currentness. Floot/Codex are non-authoritative executors. Old accepted R1 remains lawful history after R2 becomes current but can never automatically replace current R2. A cinema film V1 retains its selected accepted R1 until a separately authorized cinema V2 operation.

## Double-time parallel orders
STUDIO WORK A — Issuer: authenticate principal/session, project and revision membership; verify lawful source revision→accepted audio artifact association, decoded media identity and quality; issue bounded audience/cinema-project/expiry/revocation/rights grant for exact PCM sample window. Never authorize on path or SHA alone. Deny wrong-project requests even if digest matches.

STUDIO WORK B — Music structures: issue qualified timing of accepted lyrics, beat/section/DJ performance events and exact sample coordinates. Keep SongSpec/ProductionTimeline canonical in Studio. Use rational clock reference with cinema owner instead of floating-point re-rounding independently.

STUDIO WORK C — Independent Studio QA: challenge wrong PCM position even with correct digest; stale/expired grant, cross-project media reuse, stale-R1 race after R2 current, recovery after timeout, late artifact association, cold reopen and mobile responsive parity. Ensure Cinema status shown in Studio is accurately differentiated from film technical certification and artist approval.

CODEX EXECUTION ENVIRONMENT — when actually admitted by environment ID, bounded to exact Studio SHA and an isolated branch/worktree, may implement issuer TDD code and regression tests in Studio owner paths with explicit approval. Codex is NOT currently proven connected by this order, cannot decide music currentness, create shadow accepted artifacts or self-certify cinema physical video proof. Record exact base/head, test command/exits, source path deltas, Git readback and next wake.

WORK E — independent adversarial QA resides principally in cinema repo, challenges Studio issue/read contract at its lawful integration interface. It may submit disjoint attack fixtures/review, not copy musician-owned ProjectRevision authority into cinema.

## JOINT-1 / JOINT-2 first-light scope
Studio issues authorized R1/A1 accepted audio and exact 15-second sample interval. Cinema binds it into one visual V1 and physically renders three modes: Resurrection Vinyl, Living Lyrics, Hypnotic Soundworld. Contract timing reference at 48 kHz / 24 fps: [10992000,11712000) audio samples and [5496,5856) global source video frames. These are mathematical test vectors, not assertion that the artist's real PCM audio is available. Cinema independently decodes and measures all intended visual targets; Studio must not display a verified full film from a 15-second preview or caller-generated JSON. R2 opt-in to cinema V2 requires explicit revision selection, cold recovery and independent physical proof on V2. Other four HVC modes separately unqualified until rendered/measured.

## Stage/gate semantics
COMMAND_ACCEPTED ≠ PROJECT_REVISION_COMMITTED ≠ AUDIO_ARTIFACT_VALID ≠ PCM_PLAYABLE ≠ CINEMA_PHYSICALLY_VERIFIED ≠ ARTIST_CREATIVELY_APPROVED. Proof from cinema must resolve the exact authorized cinema revision/media binding, target inventory, verifier-held trust root, expected scope, actual decoded measurements and independently valid approval. Correct WAV bytes at wrong musical position = FAIL. No unscoped hash, browser supplied current or forged report grants rights.

## Source reference / acceptance
At order creation Studio main d6aa889a0def72bb8e1c87009a98d6c29e47067e; Studio HVC-003A draft #29 head 1a2a08f67ddb2651c62d8b63b284fc4cd81211e0; cinema main aaed100cb41cac9df32962a441fad4434e3f6071; cinema coordination draft PR #87 head 68d3973dd889562c29e12022bfd790bdbb1a390f. Read back current heads before integration. No direct main mutation, release, deploy, approved grant, media upload or spend was performed by this document. Local machine-checked 25-file NASA command ZIP is a separate handoff; production integration remains NOT EXECUTED.

## JUSTIN 101
CHANGED: Studio-side work orders for A/B/C plus CodeX execution and Work E independent challenges, aligned to cinema NASA command. PROVEN: doc source committed/reviewable only. UNPROVEN: service issuer, actual 15-second stream, real HVC render, cold recovery, film certificates. TEAM NEXT: owner implementation/QA on separate source branches; Foreman reconciles independent cinema gates. JUSTIN ACTION: none until creative review of actual film.

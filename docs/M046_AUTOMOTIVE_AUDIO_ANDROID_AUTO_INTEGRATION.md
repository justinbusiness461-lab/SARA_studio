# M046 — S.A.R.A. Studio Automotive Audio / Android Auto

**Date:** 2026-11-23. **Owner:** SARA_studio (repo ID 1427534706). **Source base:** main d6aa889a0def72bb8e1c87009a98d6c29e47067e. **Status:** isolated media contract candidate — NO native Android application, no Android Auto playback certification, no shipped car UI.

**Pilot:** Sara's 2020 GMC Terrain SLE with Android Auto phone projection. Android Auto is NOT Android Automotive OS (Google built-in). Treat model/trim as project context, not a VIN/head-unit hardware audit.

## Required unified experience

S.A.R.A. Studio must ultimately include authorized project masters, artist library, play/pause/seek/skip, voice search, artwork and Now Playing, 10/12/32-band graphic and parametric EQ, low/high shelves, bass/treble/presets, limiter and output metering, time-synchronized waveform, FFT/spectrum/oscilloscope, bouncing bars, waves and circular DJ-reactive visualizers, history and exact revision A/B, mobile-first phone UI, and maximum lawful car integration.

**Capability parity is not custom-screen parity.** In the vehicle, only expose controls actually supported by Google's host. Full-band editable sliders, waveform animation, and DJ editor may NOT be projected as arbitrary Android Auto driving screens. Do not use overlays, spoofed app categories, browser hacks or mirror bypass as a release strategy. A parked-only Android Automotive OS vehicle app is a distinct future product and needs vehicle/host/policy qualification.

## Capability routing

| Function | Studio phone/desktop | Standard Android Auto driving host | AAOS parked candidate |
|---|---|---|---|
| Browse authorized library/playlist/history | Full | Host media library | Host media library |
| Play/stop/seek/skip, artwork/position | Full | Media3 host controls | Media3 host controls |
| Voice media search | Yes | Voice/session integration | Voice/session integration |
| EQ bands, parametric filters, bass, presets | Full, safe DSP gate | Host-permitted preset action if supported; do NOT promise sliders | Custom parked settings only after host approval |
| Animated EQ bars / waves / circles | Authorized, PCM-time-based visualizer | No unrestricted custom animated UI | Parked custom-screen candidate only |
| Change ONLY This, timeline, stems, revision edit | Existing owner | Not on driving car screen | Not automatic, requires independent approval |
| Historical R1/R2 A/B | Lawful revision selection; exact musical position | Browse/play only if grant issued; do not promote history | Same |

## Existing Studio reuse — validated source inspection, not executed on head unit

- app-core.js: masterBus, lowShelf, highShelf, mixAnalyser, flux analysis already exist. Validate whether analyser captures pre/post master DSP before making visual or sound-fidelity claims.
- index.html: existing two master shelf sliders and browser playback controls.
- app-ui.js: project commit/open, revision-bound audio paths and historical playback selection, with release gates still outstanding.
- tools/studio_server.py: canonical ProjectManifest, immutable ProjectRevision and RenderArtifact ownership. Reuse; NEVER fork a car-specific project graph, CAS, media digest owner, or browser cache as truth.
- INSTALL.md: broker is loopback-only; current runtime does not establish a remotely authenticated, multi-device protected media API. **P0 BLOCKER:** phone in a Terrain cannot lawfully stream private Studio revision media until a principal-bound, secure delivery owner exists.
- No native Android Gradle app / Media3 service in inspected default branch. This branch is a first contract, NOT a vehicle player.

## Lawful architecture

1. Server owns principal/session, project access, current selected revision, committed historical ancestry, source-to-artifact associations and render validity.
2. Provide server-authenticated **browse** returning opaque playable media IDs, safe display metadata and no private file paths or CAS digests. A playlist/cached identifier is not authorization.
3. **Every play** request re-checks principal/session -> project permission -> explicit revision membership -> lawful revision/artifact association -> immutable digest and physical media validity; server emits short-lived HTTPS stream grant for that exact artifact. No grant = no playback. An invalid/expired grant cannot fall back to unverified browser synthesis pretending to be the certified master.
4. Native Android phone app owns only the car media projection adapter: Jetpack Media3 MediaLibraryService + MediaLibrarySession + ExoPlayer, host-rendered media browser, transport, voice, focus, interruptions and metadata. It does not own revisions. Declare automotive_app_desc.xml uses media; test via Android Auto Desktop Head Unit.
5. Future Car App Library media templates are capability-gated; currently Android Auto release track restrictions apply. Do NOT assume templates enable arbitrary EQ controls or animations.
6. On-car DSP presets are *playback presentation* only unless an explicit Studio change operation commits a new immutable revision. Never silently alter SongSpec, ProductionTimeline or accepted WAV. No claim that a Studio EQ processes Spotify or other apps.
7. Visualizers read verified, decoded, currently selected audio and preserve timeline/seek correspondence; silence must give silence, no microphone fakery. An earlier historical R1 response may load into history but cannot replace selected/current R2.
8. Connection alone must not start music. Respect driver distraction, car/phone focus, incoming calls, Bluetooth/wired disconnect, permissions, offline and token expiry. UI request-generation tokens suppress stale screens; they do not select current project truth.
9. Android Auto phone projection vs AAOS Google built-in require distinct app packaging, rules, eligibility tests, and hardware compatibility evidence.

## Execution order / exact owners

**M046-A (this PR, owner-disjoint):** tools/automotive_media_contract.cjs plus tests/automotive_media_contract.test.cjs. The helper shapes a safe catalog, requires fresh playback resolver callbacks, validates bounded stream grant shape, and restricts car visual/slider/editor surfaces. It CANNOT prove that the resolver is truthful; real protection must be enforced by the authenticated backend. Local Node RED (missing module) -> GREEN 5/5; not Android runtime testing.

**M046-B (Studio backend):** Principal-bound catalog and token issuance; exact historical membership and immutable artifact verification; range-read stream and revocation; isolated P0 tests for forged project ID, cross-project media, stolen grant, stale history, expired grant, invalid WAV and uncertain completion. Do not open a public CAS URL.

**M046-C (Android app owner):** Reproducible Gradle project; native Media3 library/session/player, voice actions, standard browse/Now Playing, custom preset actions only when host permits, storage/permissions, audio focus, reconnect/recovery; Android Auto DHU and 2020 Terrain physical exercise. No production publication until B passes.

**M046-D (Studio DSP owner):** Reuse low/high shelves; add true multiband graphic + parametric equalization, presets and bass boost with reproducible gain/phase/tail/clip tests and live-vs-offline parity; make render-affecting edits revision-controlled.

**M046-E (visual owner):** Reuse analyser; FFT bars, waveform, radial visualizer, DJ beat-reactivity and latency/seek tests on phone, responsive UI and safe parked-only AAOS experimentation. Don't accidentally change the accepted audio.

**M046-F (release/physical owners):** Full Python/Node/browser regressions, real WAV decoding/listening, Android Auto test head unit, USB car test, Play Store policy review, accessibility, audio focus, interruption, authorized A/B, mobile UX and creative approval.

## Mandatory RED vectors

- Unauthorized/cross-project opaque ID or bare path/digest cannot grant audio.
- Expired, mismatched, recycled, wrong-project, forged or disconnected stream grant denied.
- Historical R1 can play by lawful explicit selection but never becomes current R2; seek position stays correct.
- Car reconnect or browse never autoplays; permission revocation, phone switch, network loss and focus interruption fail safely.
- Exact decoded active audio drives visualizer; no visualizer/editor on driving Android Auto standard display.
- No release certificate from source-only tests or pretty graphics; physically decode/verify car output before signing a claim.

## Evidence

Local, isolated Node v22: original focused test failed (module absent); implementation then passed 5/5. Reproduce: node --test tests/automotive_media_contract.test.cjs. Full repo test suite, Android compilation, Google Play review, car compatibility and actual audio were NOT executed. No merge/promotion or release signoff.

References:
- https://developer.android.com/media/implement/surfaces/cars
- https://developer.android.com/training/cars/media/auto
- https://developer.android.com/training/cars/apps/media
- https://developer.android.com/docs/quality-guidelines/car-app-quality

## JUSTIN 101

**WHAT CHANGED:** automotive integration feature contract and first adversarial tests, owner-isolated.
**FAILED/BLOCKED:** principal-bound remote grant and Android native module absent; no car runtime.
**PROVEN:** pure contract behavior only, focused local Node 5/5.
**UNPROVEN:** a working Terrain Android Auto app, EQ DSP behavior, visualizer output, audio quality, mobile/Play certification.
**TEAM NEXT:** Backend owner B -> native Android owner C -> DSP/visual owner D/E -> independent release/physical gate F.
**JUSTIN ACTION:** None for review; later a physical USB test on Sara's Terrain once a signed build and authorized media are ready.

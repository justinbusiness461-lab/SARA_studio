# M046 — Competitor Parity Engineering Contract (Android Auto + Off-Car)

**Initiated:** 2026-11-23. **Status:** researched feature obligations, NOT implemented or certified. **Right owner:** SARA_studio (ID 1427534706).
**Upstream research:** existing \`dj_rezrxtion\` Forge V2 PR #67, additive admission \`forge/audits/2026-11-23_ANDROID_AUTO_EQ_VISUALIZER_DONOR_ADMISSION.md\`. No donor code imported into this repo. Do not create a new project graph, audio artifact owner, playlist owner or cross-repo runtime dependency.

## Operator request

Implement capability parity with all six researched programs **both on and off Android Auto**, to the greatest lawful host capability. Explicit vendor product identity:
1. Auto Equalizer (GG_Studio)
2. MCEqual Max (CoreLogicLabs)
3. allEQ (omixin)
4. CarWeb (fcaronte)
5. MCEqual AAOS (CoreLogicLabs, different Google built-in OS)
6. Poweramp Equalizer (Max MP)
Watch: MCEqual Ultra (preorder hardware, AAOS-only; NOT the 2020 Terrain).

### What "parity" means

Deliver equivalent **user outcomes**, not vendor implementation copies. For unsupported host/platform, the same operation appears in phone/desktop Studio or must be marked unavailable in-car. Never simulate supported results. No audio quality or DSP equivalence without matched actual decoded audio and listening.

## Product capability backlog (testable)

| ID | Category | Must-have target | Where it runs | Acceptance |
|---|---|---|---|---|
| A-01 | Native car transport | Play/pause/seek/next/previous, metadata, art, browse, playlist, history, voice, audio focus, interruption, reconnect | Android app + host | Media3 MediaLibraryService DHU then Terrain; no autoplay on browse |
| A-02 | Secure Studio library | Accepted source masters + lawful explicit historical versions | All surfaces | principal ACL → project → revision membership → artifact binding → digest + decode; R1 never supersedes R2 |
| A-03 | Graphic EQ | 5, 10, 12 and up to 32 configurable bands, adjustable frequency span, presets, visual curve | Phone/desktop and supported Android DSP | deterministic transfer coefficients, gain/phase test against fixture |
| A-04 | Parametric EQ | ≥12 bands; peak, low/high shelf, high/low pass, Q and gain/frequency, bypass | Phone/desktop; processing on car route when OS allows | exact frequency responses, gain/Q bounds, no non-finite coefficient |
| A-05 | Dynamics | 3-band compressor, preamp, limiter ceiling/release, makeup, balance, bass/treble, smart bass/auto gain | Phone/desktop/eligible device | matched impulse/sweep, clipped input, limiter no false true-peak claim |
| A-06 | Auto presets | Per-car, device, headphone, speaker, app, output + automatic route switching | Phone native + Android EQ if supported | deterministic selector, no cross-device EQ bleed, disabled where unsupported |
| A-07 | Correction | AutoEQ/headphone database import, loudness/highway profiles, personalized profile | Phone/desktop | provenance, matched-target compensation, user overrides stable |
| A-08 | Visuals | FFT bar spectrum, waveform, radial rings, circles, retro styles, theme/wallpaper/widgets/screensaver, configurable presets | Studio/phone, not unrestricted driving Android Auto | decoded selected audio time-aligned, silence=zero, seek parity, low-latency; 24+ initial reference, MCEqual listing count to verify |
| A-09 | Lyrics | Time-synced lyrics, manual offset, local words and LRCLIB lookup where licensed/authorized | Studio/phone; car host controls only | existing immutable LyricTimelineRevision; no fabricated words; metadata minimized |
| A-10 | Library extras | Local files, audio queue, search, shuffle, repeat, sleep, crossfade, bookmarks, radio, podcast/RSS, M3U where legal | Phone/desktop + host audio browser | source rights, network safety, seek and metadata, no offline DRM bypass |
| A-11 | Touch/theme | Thumb controls 48px+, A/B bypass/preview, haptics, phone/foldable/tablet responsive composition, configurable dark/light/OLED | Studio/phone | mobile UI/a11y test, no mobile feature demotion |
| A-12 | Device control | Widgets, notification, Bluetooth media buttons, Quick Settings, startup behavior, battery recovery | Native Android phone app | lifecycle/permissions, no hijack, no uncommanded playing |
| A-13 | Android Auto controls | Safe, large preset/favorites/enable toggles where host permits; voice/media browsing | 2020 Terrain Android Auto projection | Google-hosted UI, driving tests, no arbitrary sliders/animation/video while driving |
| A-14 | AAOS | AAOS separate distribution target; Google built-in car app, parked tune flows, permitted presets | Eligible AAOS car, NOT 2020 Terrain | independent device acceptance and Google Play rules; no cross-model assumption |
| A-15 | Extra CarWeb scope | Web/TV/IPTV/third-party app viewing, video, interactive browser, larger custom visual screens | Off-car optional separate modules only; vehicle parked category if ever permitted | rights, privacy, category eligibility, crash/security; NEVER unofficial in-motion mirroring |
| A-16 | Presentation-vs-production | Playback-only EQ does NOT alter SongSpec, ProductionTimeline, immutable master; committing mastered EQ requires explicit revision operation | All | source/master hash remains unchanged; committed revisions use existing expected-revision CAS |

## Implementation architecture / boundaries

\`\`\`
Studio SongSpec + ProductionTimeline + ProjectRevision (AUTHORITATIVE)
          │
          ├── RenderArtifact + immutable association + decode/QA (AUTHORITATIVE)
          │       └── Principal-bound Media Issuer -> expiring playable media grant
          │              └── Android Media3/ExoPlayer/MediaLibraryService
          │                      ├── Android Auto host browse / Now Playing / voice
          │                      └── AudioEffect DSP when device and session allow
          │
          └── Studio/phone full edit, DSP, visualizer, preset, lyric controls
                  ├── Playback presentation settings (non-authoritative)
                  └── Explicit commit through existing revision authority when render-affecting
\`\`\`

IMPORTANT: System-wide third-party audio equalization is a **separate OS-bound capability** from Studio media playback; it cannot be guaranteed for Spotify, Apple Music, games, protected players, hardware FM or car-resident AAOS apps. Android DynamicsProcessing is session-sensitive and attaching to session 0 is a deprecated/firmware-dependent path. Only claim coverage measured per actual Android/ROM/app.

### Reuse-first code map

- \`app-core.js\`: \`masterBus\`, \`lowShelf\`, \`highShelf\`, \`mixAnalyser\` and source DSP; preserve live/offline parity and source revision contract.
- \`index.html\`: master shelf controls plus media transport; do not claim current source implements more than low/high shelves.
- \`app-ui.js\`: existing project/revision/verified audio affordances; audio artifact authority belongs to server, not car app.
- \`tools/studio_server.py\`: extend guarded media browse/grants, do NOT publish CAS objects or accept caller-supplied current revision as permission.
- \`m044-session.cjs\`: revision-bound headless workflow; maintain recovery and historical A/B.
- \`tools/automotive_media_contract.cjs\` in PR #43: isolated shape adapter, not full backend grant validation or Android app.

### Independent tests — must fail first

SEC-01 stolen opaque ID / wrong project / forged revision / retired grant / orphan CAS / browser current spoof.  
SEC-02 authenticated physical WAV read must have lawful parent association and valid digest, decoded physical bytes.  
AUTH-03 R1/R2 out-of-order responses, cold reopen, seek to correct musical position, permission revocation.  
DSP-04 fixed fixture impulse and sine sweeps for 5/10/12/32-band responses, parametric Q, compressor envelope, limiter true peaks; honest CPU, latency and clipping.  
DSP-05 bypass/flat exact tolerance; original audio stays exact when presentation EQ toggles.  
DVC-06 routing Bluetooth/USB/wired/handset, session-only EQ vs protected third-party app; no double processing.  
VIS-07 FFT at exact selected time and 24+ effects, silence/seek handling, 30fps target with low-end fallback; visualizer NEVER fakes spectrum from microphone or unverified media.  
VIS-08 lyrics timeline remains immutable; external lyrics/source text must not forge observed words.  
AUTO-09 AA driving host renders permitted actions; no web, moving-video, arbitrary text sliders, moving visualizer/mirroring.  
AUTO-10 DHU cold starts, incoming call, steering wheel keys, interruptions, background and reconnect, app battery restrictions.  
RELEASE-11 Google Play policy review + required vehicle test + independent listening and creative approval.  
RIGHTS-12 donor license readback; GPL-3.0 allEQ source must not enter product without approved licensing; CarWeb MIT source needs attribution and provenance if copied.

## Release ordering (owner-specific)

**P0 / M046-B:** authenticated protected media catalog + streams. Block until principal ownership and private artifact law physically exercised.
**P0 / M046-C:** native Android app skeleton and Media3 service, host actions, DHU tests. Build can start on authorized fake fixture while backend is under review, but no production claims.
**P1 / M046-D:** scalable parametric/graphic EQ + dynamics with true DSP test fixtures, route/focus ownership, per-device profiles.
**P1 / M046-E:** full phone/Studio animated visualizer, time-synced lyrics, widget and UX surface; existing analyser and existing lyric authority.
**P2 / M046-F:** local media/radio/podcast optional feature expansions with rights/metadata gates.
**P2 / M046-G:** independent AAOS Google built-in product/parked controls; NOT necessary for Terrain projection.
**P3 / separate decision:** browser/TV/IPTV, external apps, EV-routing and adapter hardware, if ever product-admitted; do not silently convert S.A.R.A. Studio into an unsafe unrestricted car browser.

## Stage record

- Competitors: 6 official-source-reviewed, 2 published code trees inspected, 4 closed-source marketing/manual-only. No physical competitor comparison.
- Research is logged in existing Forge PR #67 and used as **requirements**, not transplanted owner code.
- Studio PR #43 includes media adapter and five test source files; their full checkout/Android runtime/actual audio proof needs a certified executor. Previously reported "5/5 local GREEN" does NOT by itself establish an independently recorded current-head test receipt. Treat as **FOCUSED_TEST_EXECUTION_UNVERIFIED pending direct reproduction** unless an exact independent raw log is attached.
- No merger, deployment, APK, synchronized visual stream, car stereo proof, listener review or Google Play approval asserted.

## JUSTIN 101

WHAT CHANGED: official parity targets, owner mapping, adversarial acceptance criteria bound to six verified competitor identities.
BLOCKED: authorized remote media grants, native Android module, DSP extension, actual audio/listening and vehicle test.
PROVEN: source/market feature discovery and repository-owned requirements only.
TEAM NEXT: execute owner-disjoint P0 and P1 gates; pin exact source/commit, reproduce tests, physical audio, car quality and proof. No "all features PASS" on documentation.
JUSTIN ACTION: none for research; eventual USB test on Sara's Terrain and creative review of visuals.

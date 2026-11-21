# S.A.R.A. Studio™ — UI/UX/Graphics Master Plan
**ID:** SARA-UX-PLAN-001 · **Date:** 2026-11-21 · **Disposition:** DESIGN / PLANNING CANDIDATE ONLY
**Canonical owner:** `justinbusiness461-lab/SARA_studio` · **Source pinned for discovery:** `d6aa889a0def72bb8e1c87009a98d6c29e47067e`
**Product authority:** existing SongSpec, ProductionTimeline, ProjectRevision, ProjectManifest, RenderAttempt, RenderArtifact, LyricTimelineRevision and SampleAsset owners; this document creates none.
**Purpose:** Source-grounded master interaction/graphic contract for generative audio, editing, mixing, DJ performance, preservation, history and responsive iOS/Android/web experiences. It does not certify implementation, deployment or creative quality.

## 0. Current evidence, source, and overlaps
- Current main `index.html` includes a `.app{max-width:560px}` ceiling and viewport `maximum-scale=1,user-scalable=no`; existing project is one long card stack with a fixed transport dock. These are observed source concerns, not a measured phone failure.
- Current theme tokens: background `#0a0c12`, surface `#12161f`, elevated surface `#1a2030`, outline `#2a3348`, foreground `#e6ebf5`, muted `#8892a8`, violet `#7c6cf0`, teal `#00d2c6`, verified green `#00c853`, warning `#ffc107`, danger `#ff6b7a`. Prefer reuse and contrast verification, not wholesale rebranding.
- Existing Work A / Grimoire RS-001 candidate (historical handoff) specifies Project Bar, Chat, Canvas, Inspector, Workstream and Proof plus responsive shell contract and six golden journeys; it was SOURCE-QUALIFIED/HOLD in supplied evidence, not current-main certified. Do not independently duplicate or overwrite its source patch.
- Main's historical merged golden-journey report records 66/66 Python, 11/11 Node and 10/10 desktop Chromium tests at an older exact SHA; this is **historical reported execution**, NOT six-viewport certification at current main.
- `app-ui.js` uses `#prompt`, `#btnCompile`, `#sections`, `#mixer`, `#matrix`, `#btnOpenProject`, `#btnOctaveEdit`, `#abControls` and other existing DOM IDs. Preserve them and their authority boundaries during RS-001 composition. `scorecore.js` compiles MusicIntent to existing SongSpec; don't mint a second music schema.
- Studio PRs #35–37 and other open platform/native generation initiatives may overlap. Recompute exact heads and current main before source mutation; this proposal is not a merge order.
- Modal is **candidate generative-audio compute for Studio only**. Studio owns generation request, source-revision binding, publication, playback, cost admission and Proof; Modal is an external GPU provider, not a project authority. No specific model is certified.

## 1. Product experience contract
Artist says what to create/change; S.A.R.A. identifies **target → preserve → impact → revise → prove**. User can freely generate music but must never lose accepted work or mistake a provisional model output for a verified/playable artifact.
`CHAT = COMMAND · CANVAS = CREATION · WORKSTREAM = EXECUTION · PROOF = TRUST`.
Four core destinations: **Chat, Canvas, DJ Grid, Proof**. Project Bar is universal; Inspector and Workstream are context projections reachable from every mode; they are not separate persisted project/mission authorities.
All clients resolve the same project ID, selected revision ID, exact artifact ID, playhead/timeline position and pending operation. Navigation changes presentation only; a late response must not promote a historical revision, shift the current selection or resume stale playback.

## 2. Information architecture and screen contracts
| Surface | Principal content | Required live action / state |
|---|---|---|
| Library / Project Open | Recent projects, Create, Open by ID, current vs historical metadata | Exact server reopen; offline/unknown unmistakable |
| Universal Project Bar | Project title, save/current indicator, selected R#, history entry, export, settings | Never infer current from browser cache |
| Chat | Prompt, lyrics brief, interpretation, target/lock summary, clarification when needed | Same canonical operation as Canvas/Pro controls |
| Canvas — Arrange | Sections, bar/beat ruler, track lanes, waveform/MIDI, selection, automation, real playhead | Pinch/drag/zoom/scroll with accessible alternatives |
| Canvas — Lyrics | Per-section text, vocal role, linked observations/word timeline | Differentiate authored lyrics from observed/aligned evidence |
| Canvas — Mixer | Gain, pan, mute/solo, bus/effect, headphone audition, A/B | Controls show committed vs draft state |
| Generate composer | Style/lyrics/structure/seed where qualified; instrumental/vocal; Take 1–4 | Model constraints, input limits, credits, rights and render authority before invoke |
| Workstream strip/sheet | Queue, provider, stage, error, cancel when lawful, cost if known | Submitted ≠ running ≠ validated ≠ published |
| Change ONLY This™ inspector | Explicit target, preserve locks, dependency/tail impact, P0–P3 grade | Confirm scope before mutation; no blanket exactness claims |
| Version Vault™ / A-B | Current and historical revisions, artifacts, difference and beat-aligned playhead | Historical access does not promote current |
| DJ Grid | Transport, pads, cue points, loops, crossfader, scratch/FX actions | Beat-locked editable events where qualified, not decorative animation |
| Proof | Exact revision/artifact, validity, audio decoding, scope diff, audition/approval, errors | Truthful unknown and failed states with evidence links |
| Export | WAV/stems/other *qualified* formats, metadata, usage/rights disclosure | Export only actual validated bytes |
| Account / Usage | Auth/session, connected provider status, budget, local/cloud disclosures | Payment does not grant project or execution authorization |

The first-run experience should permit a musician to: **create → describe → generate → hear → change one section → audition R1/R2 at the same musical position → verify → reopen** without reading technical details or switching to desktop.

## 3. Responsive composition
**Phone compact 320–430 CSS px:** project bar → context/selection strip → primary Canvas/Chat/DJ/Proof content → Workstream status inline or sheet → fixed, safe-area-aware **two-row thumb dock**. Upper row has Play/Stop, Generate, Change ONLY This™ (three large, spaced controls); lower row has four labeled mode tabs (Chat, Canvas, DJ Grid, Proof). This solves the physical width conflict of seven independent 48px controls in one row. Dock must not cover lyrics, arrangement, focused inputs or save feedback. Inspector opens as an accessible modal bottom sheet, with persistent explicit close/confirm.
**Tablet / split 640–1024:** Canvas remains primary; optional Chat or Inspector side panel; Workstream/Proof remain accessible without navigation loss. Resizable and landscape configurations must not demote capabilities.
**Desktop 1440+:** project bar; Chat left, Canvas center, Inspector right; Workstream and Proof as resizable/supporting regions, persistent transport. Mode tabs are same logical actions, not separate data.
**Foldable, orientation changes, and keyboard:** recomposition must preserve project/revision selection, scroll/track selection, transport/playhead, prompt draft, lock state and pending operation; an unfolded device can expose more panels without changing available capabilities.
**Baseline six RS-001 viewports:** `1440×900, 1024×768, 768×900, 640×900, 430×932, 390×844`. Additional 320px compact, foldable split, text scaling, keyboard display and portrait/landscape cases are necessary extensions.
**Interaction:** 48×48 CSS-px minimum interactive target with 8px separation target for finger actions, and native-equivalent minimum 48dp on Android; visually narrow step cells must have usable accessible hit areas or horizontal scrolling, not 16×18px touch targets. No hover-only controls. VoiceOver/TalkBack names and alternatives for drag/gesture. Restore pinch zoom. Respect `env(safe-area-inset-*)`, keyboard overlap and platform dynamic text/contrast behavior.

## 4. Visual system / graphics
**Design direction:** Studio's existing obsidian-violet-teal identity, evolved into a precise professional DAW; not a fresh brand.
- **Violet**: principal creation/selection action; **teal**: audio timeline/active signal and focus; **green**: only actual qualified success; **amber**: risk/warning/uncertainty; **red**: confirmed error. Use text/icons in addition to color, especially for P0–P3 preservation.
- **Track colors:** semantic and accessible; do not rely on track color alone. Lyrics, drums, bass, guitar, vocal, sample and FX have stable icons + labels and optional hues.
- **Real musical visuals:** waveform drawn only from actual decoded audio samples/authorized peak summaries; spectrum/equalizer animated from genuine current audio, never decorative "fake playback". In-progress output uses neutral processing motion, not counterfeit spectral content.
- **Hierarchy:** 8px rhythm / tokenized spacing, compact but readable typography, 48px interactive areas, high contrast, predictable corners/elevation, dense controls appear in an advanced inspector not first-run canvas. Native system font stack acceptable (do not ship fonts merely for a cosmetic redesign).
- **Animation:** 60fps aspirational for playback visuals with adaptive reduced-motion and power-save behavior; never let animation frame rate affect sample timing, transport, committed state or Proof.
- **Assets:** app icon, splash/loading, empty projects, artwork cards, render-progress, lock glyphs, waveform/stem layers, DJ pads, revision timeline and evidence glyphs should be original, vector-first where feasible and included in one versioned asset manifest; no unlicensed artist likeness/visual donor copying.

## 5. Generative audio UI: Modal provider as candidate
**Artist-facing generation:** concise creative brief, musical constraints, lyric input, desired length/takes (when a selected model supports them), generation mode (song/instrumental or qualified edit), Generate action. Advanced exposes exact model/version/seed/sampling settings and supported limits. If a model does not support a requested control, the UI refuses or explains rather than silently pretending compliance.
**Preflight sheet:** sourceProjectRevisionId, generation intent, rights/consent, provider capability, explicit cost ceiling and authorization; warn when limited credits/model availability are uncertain. A payment method never acts as execution approval.
**Truthful stage vocabulary:** DRAFT → REQUEST ADMITTED → RENDER ATTEMPT DURABLE → RUNNING → CANDIDATE BYTES RECEIVED → AUDIO DECODED/VALIDATED → ARTIFACT DURABLY ASSOCIATED → PLAYABLE → AUDITIONED → CREATIVE APPROVED. Map only to states the actual Studio backend proves; never manufacture new authority transitions in UI.
**Takes 1–4:** each candidate keeps provenance/seed/artifact and is auditionable only if validated, with explicit chosen take. UI handles partial, failed, canceled, disconnected, unknown-effect/reconcile-before-retry states.
**Long render:** close/reopen hydrates from canonical operation/artifact IDs. Late R1 may surface under history but must never replace current selected R2.
**Model-specific note:** ACE-Step or other open-weight music models are **benchmark candidates**, not declared production-ready. Generative region edits default to P3 preservation until independent proof supports a narrower class.

## 6. Change ONLY This™ / preservation UX
Workflow: select track/section/beat or lyric target → issue instruction → show exact target and locks → disclose affected neighboring tail/bleed → identify grade **P0 Exact Event / P1 Exact Audio Region / P2 Best-Effort Isolation / P3 Generative Reconstruction** → confirm → render → listen A/B → inspect Proof → approve/reject.
- P0/P1 cannot be labeled exact absent supported event/audio comparison and correct dependency regions.
- P2 requires audition with bleed/artifact warning.
- P3 cannot promise unrelated waveform identity; user can lock *intent*, not fabricated exactness.
- Lock controls have visible state, accessible name, independent per-target identities and undo/revision path.
- Wrong artifact or wrong musical position is a failed A/B even if audio itself is valid.

## 7. Native store / platform readiness
Treat the present PWA/HTML as a prototype of app interactions, **not** proven iOS/Android store packages. Choose native host adapters only after analyzing existing packaging and lawful project owners. Preserve the same musical project model across web/iOS/Android. Validate hardware audio routing, latency, microphone/recording disclosures, background audio policy, interruptions/headphones/Bluetooth, file import/export, keyboard, safe area, offline visibility, data minimization and accessibility.
Apple review: demonstrate meaningful app functionality beyond a minimal website wrapper, required demo/AI-service disclosures, privacy policy, permissions and compliant in-app purchase behavior if applicable.
Google Play: check active target SDK requirement at submission, adapt to tablets/foldables and resizability, disclose data use and permission purpose. Official policy pages can change; do not freeze a target API based on an older handoff.
Store assets must be real screenshots of the actual qualified app and original logos/artwork; UI artwork candidate ≠ published listing.
Do not make store release claims before signed device builds, store policy review, physical playback tests, authentication and recovery validation.

## 8. Component inventory / code ownership
Reuse existing UI IDs/events and server operations. Suggested presentation components: ProjectBar, RevisionPill, RealPlaybackTransport, DualRowThumbDock, ModeTab, WorkstreamStrip, GenerationComposer, TakeSwitcher, ArrangementCanvas, SectionRuler, TrackHeader, Waveform, PianoRoll/StepGrid, LyricLane, MixerStrip, DJPad, DJDeck, TargetSelector, SonicLockToggle, PreservationImpactSheet, HistoryDrawer, ABTransport, ProofLedger, ErrorRecoverySheet, ExportSheet, EmptyState.
Initial code cone **after owner approval**: `index.html`, RS-001 `studio-shell.css` if lawfully admitted, `app-ui.js`, responsive tests; no speculative backend/music authority mutation. New audio-generation provider contracts belong to separately qualified Studio backend/RenderAttempt work, not to UI CSS or BOB.
Presentational state has no right to originate current revision, valid artifact, cost authority or Proof.

## 9. Acceptance and adverse-case validation
**RS-001 first:** exact-main integration candidate; audit product-byte diff and existing IDs; run current Python/Node tests and full six-viewport Chromium golden journey, using real server and audio (not mock waveform). Journey at each size: New → Prompt → Generate R1 → authenticated R1 Play → select Verse 2 Bass → -12 semitones → commit/render R2 → Play → same-position A/B → Proof → Save → Cold Reopen → R2 current and R1 historical/playable.
**Faults:** late R1; stale render completion; wrong artifact digest; lost network; 403/409; delayed proof; model failure; partial/corrupt WAV; insufficient cost allowance; browser/device background; portrait/landscape switch; resize while rendering; keyboard open; panel switch; audio route interruption; failure during publication/unknown-effect retry; historical access permission. Independent device and browser readback required. No test framework success alone certifies audio quality, design usability, or store release.
**Accessibility:** WCAG/OS contrast; VoiceOver/TalkBack screen reader; focus order, keyboard and switch control; visible focus; captions/text labels for audio states; no flashing or motion dependency; zoom support; 200% text/resize behavior; 48px touch targets and ≥8px interaction separation.
**Graphics:** real waveform identities and audio-time binding; no arbitrary phase reset on responsive view changes; reduced-motion support; screenshot comparison across 6 sizes + portrait/landscape + dark/light platform settings.
**Audio generation qualification:** actual model output physically decoded; inspect loudness/clipping/duration and artifact hashes; actual listening rubric; repeat/reopen; documented cost. Audio quality remains UNVERIFIED without rendered + listened evidence.

## 10. Delivery ordering, handoff and status
1. **UI owner / Work A:** inspect current RS-001 candidate exact head and current main; produce one lawful integration path preserving all IDs and behavior.
2. **Independent UX/graphics specialist:** audit first-run comprehension, mobile reach, touch, accessibility, tonal branding and failure truth on that actual candidate; return defects, not a competing shell.
3. **Work B / test executor:** exact candidate, six viewport journeys, phone + split-screen, A/B, cold reopen, concurrency/race and accessibility; allow merge only when earned.
4. **Studio generation owner:** separately qualify Modal GPU/ACE-Step/alternatives through durable RenderAttempt and exact-artifact readback; UI consumes the admitted provider result only.
5. **Store release owner:** native host/deployment packaging, platform QA, screenshots, policy readback and store listing. No premature publish.
No unapproved product, provider or release mutations are performed by this planning document.

## JUSTIN 101
**WHAT CHANGED:** source-grounded Studio screen map, visual language, mobile composition, generative-audio UI, preservation/proof interaction, native-store and test gates specified.
**FAILED:** no design/runtime/product mutation; RS-001 not certified on inspected main; `user-scalable=no` and 560px ceiling remain visible in current source.
**PROVEN:** exact source inspected, historical handoff reconciled to inspected tree; not physical UI/device testing.
**UNPROVEN:** RS-001 browser parity, Modal generation, actual music, creative acceptance, native release.
**TEAM NEXT:** Work A RS-001 source integration; UX independent adversarial review; Work B six viewports; Studio audio generator separate owner.
**JUSTIN ACTION:** none needed for planning review; future visual direction approval, store account policy and paid GPU execution are separate decisions.

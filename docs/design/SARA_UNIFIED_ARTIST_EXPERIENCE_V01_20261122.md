# S.A.R.A. Studio™ — Unified Artist Experience Design Contract v0.1

**Date:** 2026-11-22 · **Status:** DESIGN PROPOSAL / NOT PRODUCT-IMPLEMENTED · **Owner:** `justinbusiness461-lab/SARA_studio` · **Delivery branch:** `design/unified-experience-contract-20261122`.

## Evidence and branch separation

The user's ten supplied chronological handoffs `00024.txt` through `00033.txt` were inspected locally on November 22. The handoffs describe an existing mobile-first responsive shell, a newer three-column desktop workspace, verified PCM meter, eight-stage generation UI, native bridge scaffolding, artist identity/catalog and the protected-chat operator workstream. These are **handoff-reported/historically source-qualified**, not a fresh full repo/physical-device test. A late Round 22 report says PR #37 CI workflow now triggers but fails before retrievable job steps, while full live three-song Studio playback and store certification remain HOLD. Avoid citing older 288/42 or 568 totals as current release proof.

`main` at planning intake: `d6aa889a0def72bb8e1c87009a98d6c29e47067e`. Active implementation authorities include draft PR #36 / PR #37 and `feat/platform-identity-and-catalog`; this document does **not** modify those implementations. Engineering owner must reconcile their exact heads before merging visual changes.

## North Star: artistic intent becomes verifiable change

> Artist: “Change only the middle verse; preserve the hook, voice and DJ cuts.”  
> S.A.R.A.: interpret → show exact target → show locks/dependencies → propose → get approval → render candidate → listen A/B at same musical position → prove preservation/limitations → commit new revision or reject → cold reopen.

**Success metric:** `TIME_TO_VERIFIED_CREATIVE_CHANGE` including user effort, avoidable navigation, regeneration, retries and preservation risk. A visually polished status display is false if it shows `Ready` when only a request was accepted.

## One project / one selection / six workspaces

**Global shell:** project name, canonical current/selected revision, rights and source-audio verification indicator, transport, accessible project switcher, workstream/operation progress, never a second client-owned revision object.

| Workspace | User job | UI modules | Truth source |
|---|---|---|---|
| Chat | ask plain-language multi-clause changes | transcript; scoped proposal cards; preview; approval challenge; latest operation receipt | typed operation, Studio server |
| Canvas | edit exact music | multitrack waveform; region/ruler; lyric-linked sections; piano roll; track locks; mixer; FX | SongSpec, ProductionTimeline, ProjectRevision |
| DJ Grid | live editable DJ craft | dual decks; 16-step grid, 2×8 phone pad layout; faders; scratches; beat grid; loop points | authorized DJ musical events |
| Sample Lab / Beat Forge | capture / split / slice / sequence | source preview; wave slices; chromatic/beat zones; stem lanes; modular routing | SampleAsset/rights + ProjectRevision |
| Library / Release | find, organize, approve, share, distribute | versions, takes, samples, artists, source rights, release readiness | canonical catalog + release receipts |
| Proof / Workstream | decide whether a change really worked | R1/R2 exact-position A/B, verified media, preserved diff region, tier, conflicts, rights, audit | independent readback/evidence, not badge inference |

**Cinema entry:** route to PulseForge via an accepted Studio grant; do not duplicate film project truth or film visual editor in this repository. Cinema workspace link goes to PulseForge's rightful visual operation.

### Unified operation sheet (must render consistently everywhere)

`operationId`, `projectId`, `sourceRevisionId`, `selectedRevisionId`, `targetScope`, `protectedScopes`, `preservationTier` (P0/P1/P2/P3), `approvalChallenge` (when required), `attemptId`, `artifactId`, `actualMediaValidation`, `state`, `userVisibleMessage`, `evidenceUri`. This is a view contract, not a new server authority.

Use distinct stages:
`DRAFT → INTERPRETED → TARGET_RESOLVED → APPROVAL_REQUIRED → REQUEST_ACCEPTED → ATTEMPT_RUNNING → CANDIDATE_RENDERED → MEDIA_VERIFIED → A/B_READY → PRESERVATION_REVIEWED → REVISION_COMMITTED → CREATIVE_APPROVED → RELEASE_ELIGIBLE`.
Failure states `BLOCKED_LOCK`, `STALE_SOURCE`, `RIGHTS_UNVERIFIED`, `RENDER_FAILED`, `MEDIA_INVALID`, `PARTIAL_ISOLATION`, `SUBMISSION_UNCERTAIN` are visibly different. Never auto-advance on client timing alone.

## Responsive composition contract

**360–599 CSS px:** one primary workspace at a time; horizontally scrollable editor surfaces INSIDE bounded panels, not document overflow. Persistent safe-area-aware bottom dock with Play/Stop, Generate, Change ONLY This™, current mode; additional modes available from bottom accessible More/sheet without sacrificing operation availability. Context drawers/bottom sheets for selected region, lock, mastering, A/B takes. On-screen keyboard cannot obscure authoring controls. Use `100dvh`, `env(safe-area-inset-bottom)`; minimum touch area **48×48 CSS px**; **≥8px between independent active touch bounds**; safe gesture exclusion and `touch-action:none` only where musically necessary (pad/platter).
**600–1023:** split waveform/Chat or Canvas/Proof, resizable panes; DJ grid responsive; maintains source strip.
**≥1024:** three-column studio composition: persistent project/library rail, central waveform/editor, context-aware right inspector/Chat/Proof; resize/collapse without losing selection. Keyboard tooltips and shortcuts; no special desktop authority.
**Foldables/tablets/desktop window resizing:** preserve selected region and current project by server ID; don't reload operations by rotating the device; migrate focus safely and retain tool state without client-owned truth.

**Transport:** one verified selected source and playhead across modes; audio must stop or show unavailable on lost source, route changes, background interruptions, denied permissions. `CORRECT FILE + WRONG MUSICAL POSITION = FAILED A/B`.

## Visual/graphic system proposal (NOT approved brand tokens)

- **Visual universe:** professional dark music-production workspace, precise and warm rather than generic neon; distinguish the product's artist identity from illustrative cinematic mood.
- **Tokens:** base surfaces `#101923`, `#192733`, elevated `#223445`; high-contrast text `#F4F6F7`; cyan `#52CFDB` for verified audio and selected waveform; amber `#FFAE55` for target edit/candidate; muted mint `#65D7A0` for independently verified evidence; coral `#F18883` for blocked/error. **Color is never the only status signifier**; include readable text, shape and icon. Test WCAG contrast.
- **Waveforms and musical geometry:** selected edit range visually bounded and labeled; preserved regions can be dimmed/locked; source R1 and candidate R2 waveform aligned by the same actual ruler; no decorative fake spectral activity when no verified PCM.
- **Icon language:** consistent outlined transport/musical controls with text accessible names. Custom DJ pictograms only if tested at 48 CSS px and screen reader. Avoid lookalike competitor branding.
- **Typography:** readable, large numbers for BPM, key, time, source verification and take selection. Minimum readable body size, responsive scaling at 200% zoom and OS text enlargement.
- **Motion:** real transport meter follows actually decoded verified audio; 120–180ms functional transitions; reduce-motion preference; no animated badges that falsely imply an active render.
- **Accessibility:** keyboard support, focus order, touch target separation, spoken play status, waveform alternative representation, contrast, captions, no keyboard trap; DJ gestures must have an accessible non-gesture equivalent.
- **Microcopy:** `Proposal only` / `Rendering candidate` / `Audio playable` / `Source unchanged outside verified regions` / `Preservation not exact; audition required` / `Revision committed` / `Historical candidate — not selected`.

## Three mandatory UX journeys

**J1 First song:** open/create → import/generate → show rights/source provenance → hear verified playback → save → close/reopen same revision. No false “Ready”.
**J2 Change ONLY This™:** R1 source → select region and lock other scopes → natural-language instruction → inspect plan and effect of changes → approve → render R2 → exact-position A/B → view P0–P3 proof → commit or discard → reopen R2. Stale R1 job may enter history, never replace R2.
**J3 Studio-to-film:** select approved song revision/artifact → preview granted soundtrack/rights → request film grant → open cinema workspace → character source lock and approved shot storyboard → film renders only after rightful PulseForge authority; Studio never holds a second current film selection.

## Candidate component library: reuse before creation

GlobalBar, SourceTruthStrip, PersistentTransport, ThumbDock, WorkspaceTabs, PromptComposer, ScopedEditSummary, SonicLockToggle, RevisionRail, TakeABSwitcher, WaveformRegionSelector, LyricTimeline, DrumPadGrid, DJPlatter, StemLane, EffectsGraph, PermissionExplainer, RenderProgressTimeline, PreservationProofCard, ArtistApprovalSheet, RightsSheet, ReleaseGatePanel, RecoveryToast, MediaPlayerWithSourceIdentity, HistoricalArtifactLabel.

For each component, define typed input, controlled state derived from canonical server source, event contract, native adaptation and physical accessibility check. Never create a separate operation authority in UI state/localStorage.

## Exact engineering acceptance matrix

| Test ID | User-visible gate | Required validation |
|---|---|---|
| UX-001 | six viewports no overflow | `documentElement.scrollWidth <= window.innerWidth`; incl keyboard/zoom |
| UX-002 | persistent thumb ergonomics | all dock, lock, A/B, scratching controls ≥48px; ≥8px active gap |
| UX-003 | no mobile capability demotion | same operation list and same server command for Chat/Canvas/DJ Grid/Proof |
| UX-004 | slow/failed/out-of-order requests | generation token + selected `projectId/revisionId`, stale UI suppression |
| UX-005 | musical position A/B | exact same source timeline offset, decoded audio correct |
| UX-006 | source truth status | proposed != committed != artifact valid != playable != creatively approved |
| UX-007 | recovery | cold reopen R1/R2, failed upload, offline transition, resumed render |
| UX-008 | actual-device DJ input | multi-touch faders/pads, audible response latency, pointer capture, no scroll |
| UX-009 | Apple/Google native lifecycle | app install/auth, file picker/share, background audio, focus and routes |
| UX-010 | inclusive interaction | keyboard, TalkBack/VoiceOver, high zoom, reduced motion, contrast |
| UX-011 | render/release rights | no upload/share/export claim without verified lawful artifact and approval |
| UX-012 | human usability | novice completes J1/J2 unassisted; pro completes every advanced task on phone |

**Testing sequence:** static contract → red browser regression → implementation → exact Chromium suite → physical Android/iOS → source/digest readback → listening and operator approval. A screenshot or CSS pass is not real creative quality.

## Program execution and coordination

1. **Audit latest source:** reconcile PR #36 + #37 and exact source/CI evidence. PRs and older test counts are not current release authority. Do not edit app code from this design-only branch.
2. **Design tokens and view state:** create the smallest authorized shared component/token contract; one component with responsive composition, no parallel UI implementations.
3. **P0 workflow visualization:** final proposal→approval→render→A/B→Proof status interaction on phone first, then desktop and screen reader.
4. **Native device polish:** qualify multi-touch DJ and route interruptions on physical hardware; Capacitor is a candidate, not a proof of native parity.
5. **Graphics and commercial finish:** refine consistent icons, animated real audio, waveform/numeric readability and dark/light theme; use actual artist assets only with rights and approved branding.
6. **Release gating:** App Store/Play Store screenshots and app icon reflect *actual* qualified UI only; no claims of generated audio/video capability from a mockup.

## Ownership / handoff

`SARA_studio` owns this Studio UX behavior and shared artist shell. `dj_rezrxtion` owns cinematic graphics/shot UI, source character locks and global audio-reactive film visualization. Shared appearance may reuse approved tokens/interaction contract; sound-generation and film authority must remain separate. All producer workers can use this doc as a planning contract after merge; this design PR does not certify any product operation.

### JUSTIN 101

**CHANGED:** established a detailed design-side parity contract grounded in current uploaded Round 5–22 reports; named navigation, components, state semantics, accessibility, UI fault tests and next design slices.

**FAILED/HELD:** store/device/creative gates and CI physical execution are not proven; no mockups should imply otherwise.

**PROVEN:** design requirements written to this branch for review; execution pending independent repo readback.

**TEAM NEXT:** UI owner compares existing shell/PR #37 against this contract and creates RED visual/interaction tests before changing functionality.

**JUSTIN ACTION:** none for this design planning.

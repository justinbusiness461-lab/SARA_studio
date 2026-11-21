# S.A.R.A. Studio™ — SuTunes Native Capability Parity / Donor Forge

**Owner:** canonical `SARA_studio` (music), Mission 044–045 research handoff, 2026-11-21.  
**Competitor identity:** [Sutunes: AI Music & Song Maker — iOS](https://apps.apple.com/us/app/sutunes-ai-music-song-maker/id6785399105) / [Android](https://play.google.com/store/apps/details?id=com.ai.music.generator.songmaker). Apple listing: developer Mobile Smart Growth, seller ZERO TO ONE CONSULTING COMPANY LIMITED; official store product listing primary evidence.  
**Evidence:** public descriptions and App Store v2.5.2/2.5.1/2.5.0/2.4.0 changelog; **no independent binary execution, generated tracks, vocal quality listening, SDK/API, model/source inspection, app purchase or full feature conformance**.  
**Engineering principle:** VALIDATE → REUSE → EXTEND → REFACTOR → CREATE ONLY IF REQUIRED. Source-feature observation ≠ implemented/certified parity.

## Primary evidence snapshot (November 21, 2026)

Apple App Store states:
- **v2.5.2 (approximately Nov 19)**: more music styles, *Remix*, *Beat Maker*, *Audio Separator* (vocal/instrumental split).
- **v2.5.1 (Nov 13)**: in-app earned credits/task and invitations.
- **v2.5.0 (Nov 3)**: Music Remix and public songs/playlists/community.
- **v2.4.0 (Oct 24)**: player redesign; TXT/MP3/MP4 exports, instrumental/remix versions, commercial license offers, Live Activities.
- **v2.0.0 (Aug 30)**: AI music video and voice cover.
- Base listing: text/prompt/lyrics/story/mood→complete AI track, lyric assistant, personalized AI singing with supplied voice, AI song cover, AI MV.

Official sources: https://apps.apple.com/us/app/sutunes-ai-music-song-maker/id6785399105 and https://play.google.com/store/apps/details?id=com.ai.music.generator.songmaker. Developer privacy/terms links on listings should be read before using supplied voice or rights claims; store marketing alone is not sufficient to assert actual exclusive voice/song ownership. App Store reviews contain complaints about paywalls, weak prompt following and limited genre control; **anecdotes, not benchmark proof**.

## 20 capability-to-owner parity contracts

| ID | Observable SuTunes feature | SJ³ native owner | Proposed improvement + independent proof | Priority |
|---|---|---|---|---|
| SU-01 | Create music from short idea/story/mood | MusicIntent → SongSpec/ScoreCore | inspectable editable music event graph; source and render provenance | P0 |
| SU-02 | Full song generation incl. vocals/instruments | canonical Studio generator+render owner | exact revision/artifact identity, batch/take recovery, measured audio | P0 |
| SU-03 | Artist-authored lyrics → song | LyricTimeline / SongSpec | obey actual line/section boundaries, no lyrics drift, section-specific redo | P0 |
| SU-04 | AI-generated lyrics | guided intent + lyric candidate | artist approval and uniqueness; do not make up biography | P1 |
| SU-05 | Voice upload / AI singing in your voice | VoxLock / consented VoiceAsset | consent/revocation; speaker similarity, natural phrasing and privacy proof | P0 |
| SU-06 | AI song covers using voice | licensed cover/remix adapter | original-work rights, source license and non-impersonation; never auto-clear | P0 |
| SU-07 | Music Remix | ProjectRevision / Change ONLY This™ | bounded edit/locked sections; A/B matched time; same source revision | P0 |
| SU-08 | Beat Maker (v2.5.2) | Beat Forge™ / ScoreCore rhythm | notes, microtiming, groove, editable Scratch Surgeon DJ events | P0 |
| SU-09 | Audio Separator (v2.5.2) | StemForge™ | decoded stems aligned; source identity; reconstruction claim only when measured | P0 |
| SU-10 | AI song music video | PulseForge™ consumer only | hand off accepted sourceRevision+artifactId, never cinema-owned master | ROUTE-CINEMA |
| SU-11 | Instrumental version | Music revision/render owner | instrumental as versioned edit/alternate export, not deletion of vocals | P1 |
| SU-12 | TXT, MP3, MP4 export | Studio artifact export / cinema MP4 | immutable hashes, codec and frame decode, rights/readback receipts | P1 |
| SU-13 | Public songs/playlists | artist catalog/release owner | preview, private/public grants, access scopes, revocable share links | P2 |
| SU-14 | Genre/style palette expansion | MusicIntent + Style DNA | individual song identity, measurable groove/rock/DJ identity, no genericization | P1 |
| SU-15 | New player and comparison | transport/A/B / Version Vault™ | actual verified WAV, selected R1/R2 and same musical position | P0 |
| SU-16 | Credits-earned tasks/invites | user account billing/UX owner | transparent CPU/cloud cost, zero hidden paywalls and no data-tracking surprise | P2 |
| SU-17 | Commercial licenses on exports | SampleAsset/rights owner | inspect actual generated/output rights agreement per job, not fake blanket rights | P0 |
| SU-18 | Live Activities and mobile creation | mobile app shell/release | Android/iOS parity; 48px targets; persistent recoverable jobs, no mobile demotion | P1 |
| SU-19 | Multi-language/localized UI | product UI layer | preserve musical/lyric language identity; WCAG/a11y and locale tests | P2 |
| SU-20 | Share/discover created music | release manager / allowed integrations | durable release receipts, safe API scope and provenance | P2 |

**No competing DB.** User Intent is nonauthoritative; SongSpec musical truth; ProductionTimeline timebase; ProjectRevision immutable version; ProjectManifest.currentRevisionId current; RenderArtifact immutable subordinate output; SampleAsset lawful media rights; LyricTimelineRevision observed evidence. Store app-created audio may be imported only after independent source+rights verification.

## Competitive failure tests we should beat

1. **PROMPT_FIDELITY**: "Keep hook exactly the same, slow middle verse, darken bass, add a metallic hit" → typed target plan, blocked ambiguous/locked operations, no full-song automatic regen. Measure edits versus actual accepted source; P3 bleed disclosed.
2. **VOCAL_CONSENT**: real voice samples require recorded permission, voice user controls, revocation and restricted access; a singing voice candidate must not impersonate a person without authorization.
3. **SINGING_QUALITY**: genuine physical listening; lyric clarity, prosody, singing intonation, consonants, voice consistency, half-time rapper pace. Never claim AUDIO_PASS from prompt alone.
4. **COVER_RIGHTS**: rights on original composition, sound recording and reference voice independently established; if unresolved, external publish/distribution blocked.
5. **STEMS**: selected source and N stereo stems must share sample rate/timeline; dry-stem vs post-master mix reconstruction separately qualified; no exact reconstruction from a mere aligned WAV count.
6. **REMIX_VERSION_VAULT**: original R1 protected, scoped R2 editable, late R1 result historical-only, actual A/B playback from corresponding source position, crash restore.
7. **BEAT_DJ**: actual beat-locked scratch/fader events, subdivisions and audio; not decorative DJ FX, and exact source identity.
8. **EXPORTS**: file lengths, hashes, codecs, metadata, lyrics, artwork and rights receipts; 60s vs 210s not silently equal.
9. **MOBILE**: six viewports and actual Android/iOS device gesture endurance; same project/current authority across Chat/Canvas/DJ Grid/Proof.
10. **COST**: free/paid credit claims tested by actual bounded account experiments only if authorized; user never charged without a declared budget, no unnecessary repeated regenerations.
11. **PRIVACY**: explicit notice of microphone/photo use, third-party model providers, retention/deletion, age rules and whether training occurs.
12. **MUSIC_BRAIN**: every song its own sonic identity; controlled groove and voice prompts measurable by real rendered audio; no arbitrary exactness from prompt descriptions.
13. **MULTI-LANGUAGE**: deterministic Unicode codepoint counts, multilingual pronunciation/prosody audition, source lyric identity preserved.
14. **SOCIAL_RELEASE**: publishing never implied by making a preview; rights + creative acceptance gate explicit.

## M044/M045 qualified reuse versus actual gaps

**Reuse (already investigated in project source, revalidate exact HEAD):** ScoreCore prompt→editable specification, local/staged audio render, lyric timeline/guided speech, Sonic Lock, Version Vault, scoped section proposals, Scratch Surgeon, Beat Forge rhythms, local FM preview, source-bound audio-to-MIDI candidate, MIDI/MusicXML interchange, multi-take A/B and candidate mastering. Passing local tests do **not** equal real model vocals or listening.

**Material gaps still to qualify:** natural singing personal voice models; consented voice asset authority and revoke; actual third-party/owned music model output; high-quality separation and stem rebuilding; AI cover licensing; 3½-minute mastering; formal meter conformance; fair credit/monetization and native mobile release; verified export distribution and whole-song production listening.

**Priority order by TIME_TO_VERIFIED_CREATIVE_CHANGE:**
- W6-A: exact compound Change ONLY This™ execution with candidate render and preservation receipts;
- W6-B: consented VoiceAsset + voice cover risk controls + independent singer quality evaluation;
- W6-C: dry/mixed stem source graph, separating and recombining proof;
- W6-D: mobile-native exports, commercial rights and transparent budget;
- W6-E: film integration as a consumer via accepted Studio audio grant only.

## Licensing/security admission

SuTunes is a proprietary app; no public license/SDK/model weights were verified from store descriptions. **RESEARCH_ADMITTED / CODE_AND_MODEL_REUSE_NOT_AUTHORIZED / PERFORMANCE_UNVERIFIED.** Implement original algorithms or independently licensed public components, cite provenance, obey mobile store requirements. No app binary copying, reverse engineering past contractual/legal limits, unauthorized artist voice training, or background scraping of other users' songs. Paid credits/listed commerce rights do not constitute a guaranteed general commercial copyright grant.

## Worker handoff / exact acceptance

- All workers read this doc in the canonical Studio repo, inspect current branch/SHA, then run owner-controlled source, physical audio and independent permission checks before feature promotion.
- Cross-repo cinema features go in `dj_rezrxtion`, **not** a duplicated Sound Forge video editor.
- Source → Tested → Integrated → Executed → Physically Verified → Technically Certified → Creatively Approved → Release Ready are separate statuses.

## JUSTIN 101

**CHANGED:** source-backed 20-feature SuTunes donor contract mapped to rightful Studio owners and 14 measurable acceptance gates, with contemporary v2.5.2/2.5.1/2.5.0 research.

**PROVEN:** official descriptions and public changelog observed; capabilities are advertised by the vendor.

**UNPROVEN:** actual SuTunes outputs, proprietary internals, functional parity, production reliability, source reuse licenses, vocal likeness or audio creative approval.

**TEAM NEXT:** ScoreCore/Studio owner extends scoped edits, SampleAsset owner secures voice/rights/embeddable stems, QA conducts real music listening, product tests mobile costs and export flows.

**JUSTIN ACTION:** none to admit research.

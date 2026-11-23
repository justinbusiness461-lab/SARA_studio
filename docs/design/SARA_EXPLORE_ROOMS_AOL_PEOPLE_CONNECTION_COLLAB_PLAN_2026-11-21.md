# S.A.R.A. Studio™ — Explore Rooms / AOL People Connection Collaboration Plan
**Plan ID:** SARA-EXPLORE-ROOMS-001 · **Date:** 2026-11-21 · **Status:** DRAFT / PLANNING ONLY
**Owning repository:** `justinbusiness461-lab/SARA_studio` (ID 1427534706)
**Design integration:** supplement of draft PR #38 `SARA-UX-PLAN-001`; **platform candidate:** draft PR #37 `feat/platform-identity-and-catalog`; no product or schema changes.
**Prior research provenance:** Personal Library `BOB_competitive_capability_audit_2026-10-01.md`, addendum `AOL PEOPLE CONNECTION CHAT, PROFILES AND BOTS`, October 1, 2026. Product research donor, not imported BOB implementation or AIM.

## 1. Product concept / differentiator
Turn **Explore → Rooms** into a browsable network of *places* where musicians meet through shared genres, skills, projects and events, and can graduate from chatting to real rights-bound Studio collaboration. Use the emotional grammar of **AOL People Connection chatrooms**, expressly **NOT AIM buddy-list messaging**: member-curated directory, recognizable room name/topic, visible occupants, profile card, hosted events, public/member-created/private rooms, room guide and linked overflow/breakouts.
Never clone AOL's trademarks, imagery or proprietary client; reinterpret the interaction model in S.A.R.A. Studio's existing obsidian/violet/teal design. A familiar room should be welcoming and legible on a phone.
**North Star:** `Meet → Talk → Listen → Invite → Propose → Create → Verify → Share (optional)`.
**Hard boundary:** Room message / AI suggestion ≠ Studio ProjectRevision commit ≠ verified WAV ≠ authorized public SongPublication ≠ creative approval.

## 2. Research-derived vs new Studio proposal
**Historical evidence from Oct 1 audit:** mid/late-1990s AOL People Connection provided subject-category directories, public/member-created/private rooms, occupant lists, chosen screen-name profiles, private IM and ignore, hosted/scheduled programming, and numbered overflow rooms. One historical report described a 23-person cap; treat it as a period-specific observation, not Studio's target. Difficulties were durable file collaboration, spam/flood, spoofing, identity trust, harassment and poorly accountable moderation. The audit classified room discovery/occupant/profile/command mechanics ADAPT, cozy size/event/teaching bots BENCHMARK, and fake identity/invisible bots/unrestricted child DMs/spammy greeters/unaccountable volunteer powers REJECT.
**New Studio design proposal:** genre-based Explore rooms, verified-identity-backed artist handles, pinned lawful audio, optional read-only project collaboration, room-triggered invitation/proposal workflow, explicit S.A.R.A. helper identity, durable transcript, responsible moderation and mobile professional DAW integration. No prior source claimed Studio had implemented these rooms.

## 3. Navigation / discovery
Within existing authenticated **Explore** view: `Discover | Rooms | Sessions | Creators` (tabs are presentation scopes, not independent source systems).
- Discover: public approved music and featured artist/room events, personalized only where consent/eligibility supports.
- Rooms: category chips and searchable room list; public and eligible membership-scoped room listings; titles, descriptions, declared language/genre, participant count (observed), activity freshness, explicit access badge and hosted event when scheduled. No fictional current counts or fake "online now" claims.
- Sessions: scheduled listening parties, songwriting circles, feedback clinics and co-creation events; calendar is derived from current approved event records, not client guesses.
- Creators: searchable approved public artist profiles, instruments/genre, work preferences, opt-in contact; never assume profile correctness or expose unconsented personal details.
Suggested **category templates, not existing rooms**: The Southern Sound (outlaw-country-hop/rock), Beat Lab (hip-hop/sampling), Songwriters Circle (lyrics/hooks), DJ Scratch Lounge (turntablism), Mix & Master Clinic (feedback), Open Collaboration (session opportunities), Experimental Sounds (cross-genre). Artist may create and name rooms under policy.
Room visibility: PUBLIC_DISCOVERABLE, UNLISTED_INVITE, PRIVATE_WORKSPACE. An unlisted/private room is never returned in public directory/search or exposed by numeric enumeration. `roomId` is stable and separate from display name.

## 4. Room UI (mobile-first)
**Header:** room title + purpose, access badge, presence count (fresh or unknown), host/moderation link, invite action only when authorized; pinned rules and "now playing" context.
**Main:** ordered conversation timeline with distinct artist/verified bot/room-system message styles, compact identity/profile card, timestamps, replies, attachments, session notices, report/block; no false AI roleplay as human participants.
**People panel:** who is currently participating (fresh presence only), chosen artist handle, optional skill tags, availability and authorized actions. Does not enumerate private members to nonmembers.
**Music rail:** lawful `SongPublication` preview/player for public rooms; private owner-scoped `project/revision/artifact` links only after explicit project/workspace authorization, never raw CAS path/digest-as-permission. Show accepted/unaccepted/playable statuses accurately.
**Composer:** prominent text input, 48px touch controls, attach/share by verified artifact reference not arbitrary file link. Optional S.A.R.A. helper mention (later gate) visibly labeled; no model spend or mutation from generic room messages.
**Phone:** one-room focus; collapsed participant sheet; pinned now-playing mini-player above keyboard/transport; unread counts and scroll-back without lost drafts; bottom navigation preserves existing six-tab platform model and Studio 4 modes without new duplicated navigation state.
**Tablet:** conversation + participant or music rail; **desktop:** directory + room transcript + participant/project card triple pane. All capabilities remain available through sheets on compact devices.
**Visual direction:** modern, subtly nostalgic window/tab framing (purpose, participants, scrolling chat) in existing Studio tokens; no literal vintage AOL blue copy. Accessible contrast, 48px targets, screen reader announcements, text scaling, motion reduction, keyboard navigation and quiet notifications.

## 5. Room types and permissions
| Type | Discoverability | Intended membership | Music collaboration |
|---|---|---|---|
| Public genre lounge | Explore directory | Authenticated eligible artists | Public rights-cleared SongPublication playback; invite by consent |
| Hosted event / listening party | Listed while scheduled/active | Registered eligible attendees/host | Shared published-track playlist; no undeclared broadcast |
| Private collaboration room | Invitation only | Explicit workspace membership + effective room admission | Lawful read-only private project/revision/audio; edits proposal-only until Studio delegated-write gate qualifies |
| Creator community / workshop | Public or unlisted policy | Topic collaborators/moderators | Critique notes, opt-in project workspace invitation |
| Breakout/overflow | Linked parent directory | Reauthorized subset | Parent workspace pointers; no untracked file fork |
**V1 recommended:** adult-account private two-human pilot + public directory/read-only lounge, no minors, no stranger DMs, no live mic streaming, no editor writes. Future minors path is separately consent/age/safety qualified; it is NOT implied by the historic AOL analogy.
Roles: owner, moderator, member, listener; effective permissions server-derived from authenticated principal, current room membership, blocking relationships and linked workspace role. Profile's displayed role is a projection, never authority.

## 6. Studio integration and provenance contract
**Already visible in draft PR #37:** `tools/platform_identity.py` local accounts/handles/session pilot; `tools/platform_social.py` playlists/follow/comments/block; `tools/platform_workspaces.py` owner/editor/viewer membership and owner-bound project reads, with delegated writes HELD; `tools/platform_chat.py` authenticated bounded **command compiler**, NOT a general durable multi-human chat transcript; `platform-ui.js` Explore and platform shell; `studio-shell.css` responsive shell. These are draft branch source, **not current main or production certification**.
**Required owner-preserving extensions, after code preflight:** room directory and scoped room admission under existing platform social/workspace owners; a single durably ordered human message stream under the rightful Studio platform conversation/message owner (discover current owner before schema); ephemeral presence with expiry; report/moderation policy plus appeal/revocation; published-song pointer reuse; room→workspace invitation only with host authorization; private workspace resource handles resolved through existing Studio ProjectRevision/RenderArtifact authorization. Avoid second artist identity, secondary song store, alternate render pipeline, shadow revision history or BOB conversation authority.
Critical edges: principal/session → room admission → message read/write → artifact/workspace authorization (if invoked) → exact project/revision/artifact association → digest/media validity → stream. No path/digest/public room membership alone grants private WAV.
Room conversation is social testimony. Collaborator suggestion is a **proposed operation**, not a Studio write. The actual scoped edit must route through existing target/preserve/impact/revision/Proof gate and expected-current-revision fence. Platform Room chat and artist-to-S.A.R.A. Studio Command Chat are different intents but may use the same authenticated platform identity and shared project pointers. Do not conflate existing `platform_chat.py` commands with multi-human message persistence.

## 7. Exact user journey
1. Sign in → Explore → Rooms → choose "Songwriters Circle" → view purpose, rules and fresh occupants → join if admitted.
2. Chat with an authenticated artist; inspect optional artist profile card and shared lawful released track.
3. Artist shares an authorized `SongPublication` or requests feedback; users can listen only after real verified rights/public WAV lookup.
4. Artist requests private collaboration; host explicitly creates/chooses a workspace, invites the consenting principal and links the original Studio project after owner readback.
5. Collaborator may read/listen only to authorized project revisions; submit timestamped proposal ("Verse 2 guitar texture") with selected section and impact notes, **not direct commit**.
6. Owner opens Studio Canvas from room's scoped project reference, reviews proposed edit/locks, performs authorized operation, commits new immutable revision, renders and proves valid audio.
7. Return to room with newly authorized revision/artifact *reference*; A/B binds correct musical position; no new public publication unless creator/rights owner approves.
8. Leave/revoke → private room and project playback immediately denied; reconnect must revalidate every capability.

## 8. Events, bots, moderation
**V1:** human-only messaging and explicit host/room rules. V1.1 opt-in deterministic `/help`, `/rules`, `/listening`, `/report` commands using declared bot identity and bounded replies; no artificial occupancy or greeting spam.
**Later:** opt-in visibly named S.A.R.A. room assistant for arranging a collaboration brief, translating room requests into *proposal* objects and summarizing with cited message IDs. It may not auto-spend Modal credits, render audio, publish, impersonate artists or modify project revisions. Cost approval belongs to existing Studio credit/render authority.
Moderation needs rate limits, flood control, authenticated server sender identity, impersonation controls, content/report queue, block, transparent mutes/removals, bounded host powers, audit/appeal/review. Child-safe chat is out-of-scope for the adult V1; no public child profile or unrestricted direct stranger message.
Retention/notification/recording privacy disclosed per room; explicit rights for recording/summarizing voice in later phase. No hidden AI participation.

## 9. Engineering phases and hard acceptance gates
**Stage A — Social UX spec & authentic source audit:** resolve current PR #37/platform UI, PR #38 design branch, room/source overlap; approve responsive mockups and account privacy. No mutation of PR #37 source.
**Stage B — Room discovery & two-adult private pilot:** one authenticated owner, invited second adult, denied third adult; room list, invite/revoke, ordered transcript, refresh and reconnect; visible participants; public/private search separation.
**Stage C — Published music conversation:** existing lawful public `SongPublication` preview in room; unpublish/rights revocation invalidates playback immediately; private project read remains role-bound.
**Stage D — Project collaboration proposals:** room→existing workspace owner invite, reviewer proposal, owner Studio action, immutable revision and playback/Proof. No delegated editor writes without current M045 preservation/rights/race graduation.
**Stage E — Hosted sessions & bounded helper:** events, room host, named breakouts, opt-in deterministic assistant; no always-on spending.
**Stage F — Real-time co-production (future research):** synchronized transport, remote session cues, mixed network latencies, instrument performance capture, conflict resolution, clock/sample alignment. Real-time shared audio is NOT claimed from human chat; it needs separate device/audio-engine qualification.
**Required negative tests:** unauthorized third-party private room listing; wrong-project room link; forged principal/role; stale/revoked workspace member; unpublish while playing; replay/double send; ordered messages across reconnect; messages after mute/block; spam/flood; model-helper injection; chat→render request without current paid authorization; late R1 audio attempting R2 promotion; two editors proposing conflicting changes; mobile keyboard and 320/360/390 widths; account logoff/online count; privacy export/deletion; system clock out of order. Require server-side, real HTTP, browser + at least two device sessions and DB/RLS independent readback. Source-level PASS ≠ hosted certification.

## 10. Metrics / release
Primary: **room join → first meaningful conversation → accepted collaboration invitation → lawful audition → verified creative change**. Record abandonment, invitations accepted, productive sessions, first render/approval, moderation incidents and retention; avoid optimizing raw message count/flooding. No unbounded costs or auto-GPU chat.
Release guards: current platform draft #37 is not merged/deployed; production auth/OIDC, rights, public moderation and store policy remain independently held. App Store/Play account deletion, community reporting, blocking, content moderation, privacy, consent and anti-harassment controls must be policy reviewed before broad public rooms. No fictional "community live" data in production UI.

## JUSTIN 101
**WHAT CHANGED:** historical AOL People Connection research translated into Studio Explore Rooms and collaboration design, without AIM confusion; proposed owner map, screens, role/safety contract, artist journey, phases and tests.
**FAILED:** no functionality attempted; no real room transcript, access or model output executed.
**PROVEN:** original Oct 1 research retrieved; Studio PR #37 module/source and existing PR #38 design scope inspected.
**UNPROVEN:** room runtime, public moderation, hosted identity/rights, collaborative edits, live audio sync, production release and creative approval.
**TEAM NEXT:** Studio platform/social owner reconciles exact PR #37 and source; UI specialist composes from PR #38; Work B independent two-user/denied-user and rights/revision QA; Studio Audio owns audio and revision authority.
**JUSTIN ACTION:** review the conceptual direction; no keys, spend, merge or deploy needed for this documentation.

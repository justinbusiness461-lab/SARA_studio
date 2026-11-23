# S.A.R.A. Studio™ v0.2 Experience Addendum — Explore, AOL Rooms, Band Manager and Apps & Connections

**November 22, 2026 · owner: `SARA_studio` · design-only addendum to `docs/design/SARA_UNIFIED_ARTIST_EXPERIENCE_V01_20261122.md`.**

## Source lineage and verification status

- This addendum is grounded in the operator-provided 44-entry, 17,720,605-uncompressed-byte archive `0101 (1).zip`, ZIP CRC PASS. It contains overlapping chronological Studio/Cinema reports and workstream histories, not 44 independent production test receipts.
- `00033.txt` explicitly restores October 1 AOL **People Connection** research (not AIM), defines `Explore → Rooms`, and outlines six staged releases: private room → directory → lawful music sharing → collaboration → hosted events → qualified live co-production.
- The upload says `SARA-EXPLORE-ROOMS-001` was previously committed to Studio UI design PR #38 (`a0534b9262d04126c103178031b886a03bab3e8a`) and later Stage 13 feature work reported on PR #37. Don't create a competing room, identity or collaboration database. Exact current PR #37/#38 branch and CI receipts must be refreshed before any feature work.
- `00033.txt` later records Round 22 source commit `2cf4511ed70dee2cd07f01d9c1db28cc2fb86048` on Studio PR #37 with GitHub Actions triggered but job showing no test execution steps, plus `main` unchanged in the handoff. Historical reported green test counts do not certify live hosted Studio, full rooms, stores or actual devices.
- Cinema is `dj_rezrxtion` owner; never bring cinema currentness, actor identity, frames or VisualRevision into Studio. Studio grants source-revision-bound accepted soundtrack to it.

## Corrected primary navigation (no Explore omission)

**Create/Studio** | **Explore** | **Band Manager™** | **Library/Projects** | **S.A.R.A. Chat**.

On phone, maintain a safe-area-aware bottom action dock and a responsive workspace switcher; don't try to cram all top-level routes into tiny dock buttons. Every route can open contextual S.A.R.A. Chat with same authorized project/session context and identical operation semantics.

### Explore (full creator discovery and social home)

- **Discover:** published tracks, artist profiles, genres, curated listening, new work, public playlists, selected source-safe recommendations. No fake play counts or hidden use of unpublished projects.
- **Rooms:** authentic AOL People Connection-inspired themed directory; public/private artist-created rooms, who-is-chatting presence, chosen handles, host and moderator roles, overflow rooms and invited collaborators; rooms for genre, producers, DJs, songwriting, education and feedback. Room state is platform/social authority, NOT SongSpec or audio-artifact authority.
- **Sessions:** scheduled listening parties, workshops, hosted remix reviews, producer challenges and room events. Authorized pinned song station, linked to actual released project revision/artifact and permission; no direct arbitrary file/digest authorization.
- **Creators & Collabs:** browse opt-in artist/instrument roles; permissioned invitations to existing canonical collaborative Studio workspaces, proposals, revision-linked timestamped comments, scoped role grants (owner/editor/viewer) with revocation. Room conversation alone cannot edit a song or grant source rights.

**AOL soul, not AOL UI copying:** warm, intimate interest-based conversation, recognizable room names, active visible participant lists, compact artist identity and community rituals. Upgrade privacy, moderation, mobile usability and creative collaboration. Text-first qualified rooms before live microphone/streaming co-production.

**Protect users:** adult-focused initial public rooms; private-room membership/authorization; rate limits, block/mute/report, spam moderation, escalation, visible named AI helper disclosure, consented identity and rights, audit logging. Account/report privacy, safe links, account deletion, no private/public room leakage. A user cannot become editor by being in the room.

### Band Manager™ (creative business partner, not music-authority replacement)

One artist-operating workspace with:
- **Overview:** current projects, approved release readiness, deadlines, bookings, opportunities, costs and true operation status.
- **Releases:** rights/metadata/splits/artwork/ISRC/UPC if lawfully obtained, royalty/report reconciliation and external distributor submission receipts. Never assume a SoundCloud API can programmatically do every dashboard operation.
- **Growth & SEO Center™:** artist website and search content, video discoverability, social/content campaigns, audience segments, fan engagement, email outreach, growth experiments and true platform metrics. No promises of rankings or fabricated conversions.
- **Fans & Community:** consented fans, room events, newsletters, public posts and invitations, with unsubscribe/suppression and lawful messaging.
- **Bookings & Relationships:** contacts, email threads, venue/promoter campaigns, EPKs, gig calendar, contracts, collaboration invitations and approval before outreach.
- **Finances & Rights:** expenses, royalty splits, licensing, budget controls, payment reconciliation and referrals to qualified legal/accounting experts for regulated work.
- **Tasks & Workstreams:** S.A.R.A. can prepare, investigate, compare and execute only specific authorized steps. No invisible sends/posts/payments/contract acceptance.

### Apps & Connections (plugin-style app marketplace)

An explicit **Connections Hub** that shows available and linked services with provider icons, capability cards, authorized scopes, last successful sync, revocation and audit history. This is account/permission infrastructure shared with Band Manager and contextual Studio chat—not a second plugin engine or a vendor-owned artist database.

**P0 initial connector candidates:**
- **Gmail/Google:** OAuth for authorized reading/searching gig inquiries and contracts, preparing drafts, explicit permission before sending; calendar events only where separately authorized. Prefer scoped read/draft actions; no default mass emailing.
- **Facebook Pages / Instagram professional accounts:** Meta platform access subject to approval and actual app capabilities; page-owned posts, scheduled content and aggregate insights only for authorized pages/accounts and permitted scopes. **Personal-profile posting, generic Facebook inbox scraping and unrestricted platform analytics must not be promised.**
- **Artist website & analytics:** ownership-verified site, Google Search Console/Analytics where user connects, bounded SEO reports; no unsupported third-party metrics.
- **Later music ecosystem:** SoundCloud (OAuth and limited official API), streaming/distribution and DAW tools only after rights, API Terms, external account credentials and legal scopes qualification.

**Connection state machine:** `NOT_CONNECTED → OAUTH_PENDING → AUTHORIZED_SCOPES_VERIFIED → SYNCING → READBACK_VERIFIED`; `SCOPE_DENIED`, `TOKEN_EXPIRED`, `PROVIDER_REVOKED`, `SYNC_PARTIAL`, `RATE_LIMITED`, `SUBMISSION_UNCERTAIN` are distinct. Token stays on secure server vault (encrypted/limited), never browser truth; refresh/revoke safely; segregate accounts/teams/tenants.

**Every external action must separate:** `S.A.R.A. UNDERSTOOD` ≠ `PROPOSED` ≠ `USER_AUTHORIZED` ≠ `PROVIDER_ACCEPTED` ≠ `READBACK_VERIFIED` ≠ `CAMPAIGN_APPROVED`. User-visible confirmation for sends/posts/spend and account writes, independent provider readback, idempotency/reconciliation after uncertain network effects, privacy export/deletion.

## Always-connected Chat semantics

Persistent S.A.R.A. Chat is an **assistant interaction plane**, not a parallel project, rights or marketing authority. She can:
1. Interpret a music/visual/business query using session-authorized resources.
2. Present an exact proposed operation, affected owner, source version, scope, cost/rights and approvals.
3. Execute via the rightful Studio, PulseForge, social, campaign, release or external-provider adapter only after user authorization.
4. Display real receipts/proof and offer adjusted next steps. Prior to verified readback, never say an email was sent, a video was published, a record was modified or a master was approved.

**Unified career journey:** Create → Change & Mix → Prove/Approve → Cinema handoff → Rights/Release → Discover/Explore → Rooms & Collaborate → SEO/Promotion → Fans → Booking & Career → Analyze & Improve. This loop is iterative, not a one-way funnel.

## UI graphics and interactivity

- **Explore:** mood of classic themed rooms and modern music community; actual verified album artwork/waveforms; live people only when real presence data exists. "Who's here", room/listening station/host/pinned track must be compact and thumb-operable.
- **Room:** song-linked player source strip, chat transcript, people pane, moderation affordances and Collaborate invitation sheet; 360px becomes a room conversation with collapsible people/listening drawers; tablet/desktop panels appear without duplicated authority.
- **Band Manager:** campaign board, connected account status, scheduling calendar, fan metrics with source-time labels, gig inbox, rights checklist, expenses and workstream proof. Distinguish live platform values from hypothetical ideas.
- **Connections Hub:** each provider card includes permission scope, data destinations, failure/sync status, disconnect control and human-readable purpose. Show drafts vs sent and scheduled vs published accurately. Accessible focus, ≥48px target and 8px spacing.
- **S.A.R.A. Chat:** contextual action chips identify "Ask", "Preview", "Approve", "Execute", "Prove" and carry source identity. Always offer easy rollback where the underlying provider supports it, otherwise disclose irreversibility.

## Owner-directed test gates

**EXP-01** private room member-only access and 3rd-party denial; **EXP-02** room live ordered message and cold reopen; **EXP-03** immediate permission revocation; **EXP-04** no leaked private room in public discovery; **EXP-05** track unpublish revokes all room listening-station URLs; **EXP-06** invited collaborator cannot commit/approve without owner role.  
**BAND-01** exact SongSpec/rights → campaign provenance association; **BAND-02** no unapproved email/social post; **BAND-03** consented fan-list and unsubscribe enforcement; **BAND-04** source-backed engagement/report metrics.  
**CONN-01** OAuth scope-minimization + PKCE where supported; **CONN-02** cross-tenant/token leakage attack; **CONN-03** provider-token expiry and deauthorization; **CONN-04** idempotent network error/readback; **CONN-05** real Meta/Gmail provider-scope compatibility validated before UI says available.  
**UX-01** exact mobile 360/390/412/768/1024/1440 viewport controls; **UX-02** TalkBack/VoiceOver, contrast, reduced motion, keyboard; **UX-03** no UI click can send/publish/pay without specific approval.

## Current engineering status and next integration

**Design contract: proposed, not a new deployed product.** Upload includes historical claims of platform Rooms implementation, account/social features and extensive green source suites. This addendum does not certify current runtime. Route to **existing Studio PR #37 platform/social owner** and **existing Studio PR #38 UI/UX master-plan owner**; review current exact heads and implemented APIs first. Merge/reconcile into their work only after source review and tests. Keep PR #36 soundtrack-issuer dependency and cinema-owner constraints intact. Protected `main` unchanged by design document.

## JUSTIN 101

**WHAT CHANGED:** Corrected complete information architecture: Explore, AOL Rooms, Collabs, Band Manager, SEO/Growth and scoped external Connections all alongside professional music, AI creation, verified cinema handoff and continuous Chat.

**PROVEN:** The uploaded 44-file source archive was read, ZIP CRC PASS; prior Explore design and platform/social implementation reported in archive. This is a new owner-scoped planning contract, not verified runtime execution.

**UNPROVEN:** actual live room moderation, published public social app, Google/Meta OAuth implementation, live marketing sending, real fan engagement and store release.

**TEAM NEXT:** Platform owner validates PR #37 social/room source; UX owner consolidates into PR #38/PR #40; integrations/security owner qualifies Gmail and Meta provider scopes; Band Manager design/product defines minimum verifiable workflows. No duplicate authority.

**JUSTIN ACTION:** None required for this design correction.

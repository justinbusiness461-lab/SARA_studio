# SUNO FULL PLATFORM PARITY + S.A.R.A. SUPERIORITY PROGRAM
## Executable Product / Engineering Plan — 20 Nov 2026

**Scope:** ALL Suno user-visible product surfaces, not only Create and Studio: signup/auth, profiles, Home, Explore, search, player, Library, playlists, releases, social, Hooks, Workspaces, notifications, plans/credits/payments, settings, safety, mobile apps, Chat/MCP, Studio 2.0, Visuals, and operator/admin infrastructure.
**Canonical music owner:** `justinbusiness461-lab/SARA_studio` / ID `1427534706`. **Canonical visual owner:** `justinbusiness461-lab/dj_rezrxtion`; music-to-cinema connection consumes accepted music, never owns original SongSpec or ProjectRevision.
**Audit baseline observed:** M045 feature HEAD `15b6d3f15fe2a122933133f34d43c7dc7aaba28c`, main `d6aa889a0def72bb8e1c87009a98d6c29e47067e`. Research branch is not production authority. No repo code or live app mutated for this audit.
**Companion files:** `SUNO_COMPLETE_PLATFORM_PARITY_MATRIX_2026-11-20.csv` = 370 atomic targets / 21 areas. 132 Suno *category-reference candidates* requiring per-feature evidence checks; 238 native S.A.R.A. extension targets, not falsely attributed to Suno. Existing `SUNO_FULL_ABSORPTION_MATRIX_2026-11-20.csv` holds prior 57 music/cinema parity targets; these inventories OVERLAP and are **not** an additive unique feature count.
**Current source discovery limit:** inspected M045 `index.html`, `app-ui.js`, `studio-shell.css`, `tools/studio_server.py`, `package.json`, plus default-branch GitHub searches for auth/profile/Explore/credit/playlist/workspace symbols. Found the canonical Studio music project and revision architecture; did NOT establish complete app-account, Explore, social, and billing implementations in those surfaces. `NOT VERIFIED` ≠ `DOES NOT EXIST`.

## FIRST: What Suno actually documents, and what we should not assume

| Product | Vendor-documented facts | Reference |
|---|---|---|
| Welcome / login | Phone OTP and Apple, Google, Microsoft, Discord SSO | https://help.suno.com/en/articles/3134401 |
| Explore | Personalized playlists, trending songs, genres, contest entries and curated playlists | https://help.suno.com/en/articles/3134721 |
| Library | All Songs, Likes, Uploads, Stems, Workspaces, Studio Projects | https://help.suno.com/en/articles/13670849 |
| Accounts/profile | Avatar, display identity, public music, featured songs/playlists, profile customization | https://suno.com/release-notes |
| Albums | LP/EP, artwork, songs, ordering, publishing; **publishing album can turn its unpublished component songs public** | https://help.suno.com/en/articles/14227329 |
| Collaborative Workspaces | Handle-based invitation, notifications, owner controls, shared create/remix/extend, member limit and plan gate | https://help.suno.com/en/articles/14616961 |
| Social | Like, comment, share, block and report public material; creator can disable comments | https://help.suno.com/en/articles/4524353 ; https://help.suno.com/en/articles/4524417 |
| Hooks | User song + video feed, lyric overlays, share/like/comment/remix | https://help.suno.com/en/articles/8049409 |
| App player | iOS/Android listening, AirPlay, CarPlay, Android Auto and in-app offline playlists | https://help.suno.com/en/articles/14467265 ; https://help.suno.com/en/articles/14467137 |
| Studio | Studio 2.0 tracks, Chat, takes, recording, MIDI, synth, effects, automation, plugin authoring and export | https://help.suno.com/en/articles/13670529 |
| Conversational platform | Suno MCP interacts with libraries, playlists, Workspaces, plan, credits, settings, song creation, Visuals | https://help.suno.com/en/articles/14551361 |
| Billing | Free/Pro/Premier plans, dynamic plan/credit tiers and add-ons. Current pricing surface may also display Platinum; HELP pages and dynamic pricing can diverge, verify target checkout before implementing parity | https://suno.com/pricing ; https://help.suno.com/en/articles/14617153 |
| Settings / support | Personalization, visibility, remix permissions, comment controls, account deletion, report/block and help | https://help.suno.com/en/articles/3480577 ; https://help.suno.com/en/articles/4523713 |

Suno documents **Studio Chat** and **external MCP**. Thus "chat exists" is not differentiation. S.A.R.A. must give one authenticated conversational command authority across every *real*, not simulated, feature.

## The artist's unified application map

**Public without login:** Welcome, Explore, search, public creator, published song, published playlist, published album, safe player, pricing, help.
**Authenticated shell:** Home, Explore, Search, Create, Studio, Library, Artist Profile, Workspaces, notifications, credits, settings, support.
**Mobile composition:** Bottom dock (Home, Explore, Create, Library, Chat/More), persistent mini-player above or within safe-area-respecting dock, contextual Studio full-screen controls, 48×48 px targets and 8px gaps. No tool or mode gets removed on 360px mobile—reorganize, don't demote.
**Desktop composition:** Side navigation + full Studio workspace + optional Chat/Proof panels + right library dock.
**Creator detail:** A song can have an audio master, original source project, lyrics, image, album placement, multiple releases, catalog listing, optional Hook/film, and social metrics; these are references to truthful immutable identities, not duplicate song objects.

## System-of-record design; no wrong owner

### Platform identity and roles (new platform subsystems in the SARA owner, after repository scan)
- `PrincipalAccount` internal ID, `ExternalIdentityBinding`, `AuthenticatedSession`, `ArtistProfile`, `ArtistMembership` and identity verification. Public handle is never primary project authority.
- Use a standard reviewed OIDC/OAuth2 provider adapter with PKCE + state/nonce where applicable; verify issuer/audience/signature and revoke securely. Phone OTP provider requires rate limits and replay defense. Browser JS cannot originate principal authority. Prefer HttpOnly/Secure/SameSite cookies with CSRF protections where session-cookies are used.
- `Workspace` and `WorkspaceGrant` define artist/project authorization; per-operation owner/read/editor policy. Deleting invitation or membership revokes all read/stream/render rights, including old signed preview endpoints.
- A **server-side identity and authorization** check precedes every account, project, audio, search and collaboration operation.

### Catalog, social, commerce (projections of music truth, not replacements)
- `SongPublication` = artistId + authorized projectId + **immutable sourceProjectRevisionId** + **acceptedAudioArtifactId** + verified rights clearance + visibility + release metadata. No publication from arbitrary digest, browser current pointer, draft or unapproved model result.
- `CatalogListing` is a public projection derived only from active `SongPublication`; index/feeds/album entries/playlist public endpoints resolve visibility. Unpublish / rights revoke invalidates public search, CDN and cached listing; physical lawful stream auth remains enforced at the owner.
- `Playlist`, `PlaylistEntry`, `AlbumRelease`, `FollowerEdge`, `Reaction`, `Comment`, `NotificationEvent`, `ModerationReport` operate on catalog/publication identities. A playlist of private material doesn't grant strangers audio access.
- `SubscriptionEntitlement`, `CreditLedgerEntry`, `GenerationCostQuote`, `CreditReservation`, `ChargeSettlement` are transactional app operations; do not confuse model credits with audio revision proof. Payment webhook events are signature-checked, deduplicated and independently reconciled.
- `PersonalizationProfile` tracks consented listening/create preferences; opt-out immediately prevents future use. Public feed must never reveal private projects through recommendation embeddings.

### Music-to-Cinema boundary
- SARA owns SongSpec, Song DNA, SampleAsset, ProductionTimeline, ProjectRevision, accepted master, rights and release approval.
- `dj_rezrxtion` owns cinema operations, shot selection, frames, film VisualRevision, VisualProof. Its soundtrack reference requires an authorized accepted-audio grant, not CAS digest alone.
- Late historical R1 music or video cannot overwrite currently selected approved R2; selective invalidation only.

## Delivery roadmap — upgrade while auditing, without fake completion

| Wave | Deliverable / exact first vertical slice | Minimum tests / launch gate | Primary owner |
|---|---|---|---|
| PLATFORM-00: Inventory + ownership | Verify existing platform/auth sources and branch SHAs, document current account sessions, all audit indexes, contracts, decision on identity provider, no shadow catalog. | Source map + threat matrix + exact active HEAD + no authority duplication | Team Lead / Work B |
| PLATFORM-01: Identity, permissions, privacy | Working Sign Up / Sign In / OAuth, session restore, logout/revoke, principal ID, private default, access-aware app navigation, account profile skeleton and settings. Connect Chat identity. | 2 independent real principals, stolen/expired token denies, role and session revocation, 360px/mobile login, cross-session cold reopen; no unauthorized CAS reads | Platform/auth owner |
| PLATFORM-02: Artist Profiles, Home, Library and publication | Editable profile/handle/avatar/banner, persistent catalog, **private→approved publication** pipeline, public profile and safe song page, Home "resume project", Library with versions and playback. | Published R2 only becomes public after explicit rights/artist approval; R1 remains historical; private/unpublished track absent from public search; browser 6 viewports | Catalog / Studio owner |
| PLATFORM-03: Explore, Search and Player | Trending, For You, genre/mood, creator shelves, curated playlists, query/fuzzy search, player queue, safe media read, library filter, listen feedback, popularity abuse defense. | Paginated search/feeds on fixtures with private+public mixed, deindex after unpublish, stale feed cache denies actual stream, no cross-tenant leak, 360px operator tests | Discovery / Player |
| PLATFORM-04: Social, playlists, albums, Hooks, notifications | Follow/like/comment/report/block; playlist create/reorder/share, album draft/release, followers alert, notifications; Hooks listings from cinema grants only. | Double-like idempotency, blocked commenter 403, no surprise album-publication of drafts, comment moderation, stable event identities and cold restart | Social / catalog + cinema owner |
| PLATFORM-05: Billing, collaboration, moderation, support | Free/Paid entitlement checks, credits, cost quote→reserve→job→settle/refund, signed billing webhooks; Workspaces invites/roles; admin, tickets and appeals. | No duplicate charges; concurrent credit spends cannot overspend; revoked member immediately loses stream; stale write rejects; provider outage safe; finance reconciles exactly | Platform/Commerce/Auth |
| PLATFORM-06: Full Studio + mobile + external agent + cinema | Finish prior 57-row creative map: 8-min generation, actual multitrack DAW, 48k export, models, custom voice/consent, advanced stems, effects, SourceAsset rights; MCP; full phone parity; accepted cinema grant. | Blind quality rubric and physical media, exact R1/R2 A/B, 360px full actions, real DAW export, adversarial MCP and negative authorization, full movie EQ synchronized | Studio + independent cinema |
| PLATFORM-07: Hardening and release qualification | Production data migration, operability, incident/recovery, accessibility, app store/SDK policies, rate limiting, compliance reviews, security review, cost analytics, load/performance | Independent physical devices, crash injection across durability boundary, multi-user privacy audit, end-to-end payments sandbox, complete rights clearance and rollback drill | QA/Security/Release |

**Parallelism:** Auth and publisher/copyright models can be designed concurrently. Never launch public Explore until correct publish/authorization exists. No paid generation unless credit ledger and failure refunds work. No collaborative song work until principal and per-project grants exist. No public cinema video unless approved soundtrack and VisualApproval exist.

## Concrete first sprint tickets, not just feature labels

1. `PLAT-001` Repository source map: search identity, sessions, billing, social, libraries in canonical repo, deployments and manifests; record exact SHA, evidence status and owner, avoid duplicate platform authority.
2. `PLAT-002` Auth threat model: external OIDC/OTP identity, principal ID mapping, session policy, rate limiting, anti-CSRF and principal-scoped service operation. Write 403 RED tests before feature.
3. `PLAT-003` Authenticated route contract: `GET /api/me`, `GET /api/me/sessions`, `POST /api/me/sessions/revoke`, `GET/PUT /api/me/profile`. Proposed endpoints—not existing API. Contract and permission tests first.
4. `PLAT-004` Artist profile data: `ArtistProfile`, handle reservation, bio sanitization, profile artwork permission and visibility. Establish 2-account test fixtures and prevent impersonation.
5. `PLAT-005` Publication gate: `POST /api/publications` with expected source revision/artifact + rights proof + explicit artist approval; `POST /api/publications/{id}/unpublish`; prohibit digest-only publication and orphan CAS.
6. `PLAT-006` Public catalog: `GET /api/explore`, `GET /api/search`, `GET /api/artists/{handle}`, `GET /api/songs/{publicId}` with pagination and access projection. Test unpublish and private data isolation.
7. `PLAT-007` Real app-shell navigation: Welcome, Home, Explore, Create/Studio, Library, Artist Profile, Playlists, Notifications, Settings; same routes and availability from Chat; 360 px safe-area UI, no fake tabs.
8. `PLAT-008` Global player: accepted artifact media path, queue, saved position, public access, private artist preview, offline validity. Real decoder/readback and device test.
9. `PLAT-009` Social roles/events: followers, likes, playlist, album and notifications, delayed delivery idempotency, moderation, block.
10. `PLAT-010` Commerce ledger: provider-independent entitlement and spend reservation; fail-closed webhook, no double charge on retry, refund after final generation failure.
11. `PLAT-011` Chat contract parity: create playlist, find artist, play song, edit own profile, publish song, generate in Studio all use the **same authorized API** as native UI.
12. `PLAT-012` Accessibility and mobile certification: six viewport visual checks, tap 48x48, full screen reader, OS keyboard, Android/iOS login/recovery and playback.

**First six deliverables should go in a bounded platform branch/PR, not directly into `main` or a hot M045 music file.** No new backend framework solely because Suno has one—first qualify existing Studio server and deployer/runtime capability.

## 18 adversarial acceptance scenarios

| ID | Required result |
|---|---|
| ACC-01 | Malformed OAuth token, wrong audience and expired session fail closed |
| ACC-02 | Principal A may never see Principal B's private project, stream or proof |
| ACC-03 | Two concurrent signups cannot reserve the same handle |
| ACC-04 | Revoked member cannot read audio even when retaining an old digest or URL |
| PUB-01 | Draft, historical and unapproved master are absent from public Explore |
| PUB-02 | Album with private tracks triggers an explicit disclosure review, not surprise publication |
| PUB-03 | Unpublish immediately denies public play and eventually removes index/cache |
| PUB-04 | CAS object existence without lawful association never authorizes release |
| DIS-01 | Explore trending excludes deleted, rights-held and spam-farmed items |
| DIS-02 | Search pagination and high concurrent load show no private metadata |
| DIS-03 | Personalization opt-out truly stops using listening history for recommendations |
| SOC-01 | Follow/unfollow, like/unlike, notifications and retries remain idempotent |
| SOC-02 | Blocked commenter cannot post on the owner's public material |
| FIN-01 | Two concurrent paid generations cannot overdraft credits |
| FIN-02 | Duplicate payment webhook cannot double-grant credits |
| FIN-03 | Ambiguous job outcome requires authoritative readback before a paid retry |
| MOB-01 | Login, Explore, playlist, music player, create, Chat and Studio all work at 360px |
| CHAT-01 | Chat and UI actions produce same owner-authorized operation/receipt |

## Navigation and interaction specification

Desktop: left sidebar (Home, Explore, Search, Create, Studio, Library, Playlists, Workspaces, Artist, Notifications, Credits, Settings); center active content; right-side detail/library; optionally docked Chat and Proof. Phone: bottom thumb-zone dock with primary Home/Explore/Create/Library plus Chat/More, persistent player and context-specific Studio dock. Account settings reachable through avatar; no 30-tab horizontal row. Everything is resilient to deep-link and cold-restart.

Every page has four testable states: `LOADING`, `READY`, `EMPTY`, `ERROR / ACCESS_DENIED`. Public song, album and artist pages must never depend on another user's authenticated project browser state.

For social and billing: no optimistic "success" badges for payments or publications until authoritative readback; submit result and server commitment are distinct.

## Critical product distinctions

**Suno parity:** Verify each candidate feature from its own dated public documentation or live authorized browser session; a category-level help link is not a physical feature test.

**S.A.R.A. superiority:** natural-language workflows in Chat for *everything*: sign in guidance, profile changes, Explore, playlist construction, notifications, collaboration, rights, billing questions, song editing, mastering, music-to-video; sensitive actions (purchase, public publishing, invite/revoke, delete) require explicit informed operator approval.

**Not yet done:** this audit does not add real auth screens, public social API, a payment processor, a real Explore database, or release candidate. No claims of deployment, production user sessions, full song generation parity or credit charges.

## JUSTIN 101

**WHAT CHANGED:** Platform roadmap added for 21 areas and 370 atomic acceptance targets, extending the earlier 57-row *creative-capability* matrix. No wrong repo mutated.

**FAILED:** The prior research narrowed to music creation and omitted the account/discovery/social/commerce business platform. Fixed in specification, not yet in code.

**PROVEN:** Suno documentation supports account login, Explore, public catalog/profile, libraries, albums, shared Workspaces, Hooks, social, tiered credits, Studio and external AI-agent workflows.

**UNPROVEN:** Every per-row vendor feature in live authenticated use; S.A.R.A. platform implementation parity outside inspected source; app store/deployed/device; production billing or security certification.

**TEAM NEXT:** Qualify exact live source tree and reuse existing server authorization; execute PLAT-001 through PLAT-006 on owner branch with RED→GREEN and per-owner proof, then expand UI/discovery/social/billing incrementally.

**JUSTIN ACTION:** None for research/plan. Decisions on identity and billing vendors belong to the future integration gate; avoid purchasing services before approved scope/cost.

**STATUS:** RESEARCHED / PLANNED / OWNER-ASSIGNED, **NOT SHIPPED**.

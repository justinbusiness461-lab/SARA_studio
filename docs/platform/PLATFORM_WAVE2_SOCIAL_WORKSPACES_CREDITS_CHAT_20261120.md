# PLAT-009–011 · Native Platform Wave 2 execution & architecture — Nov 20 2026

**Canonical owner:** `justinbusiness461-lab/SARA_studio` repo ID `1427534706`. Wave 2 extends draft PR #37 `feat/platform-identity-and-catalog` based on exact M045 branch SHA `862a7ed11f12835b92c4f0b5673241ae4362b8c2`. No product mutations in `main`, `dj_rezrxtion`, or historical `song_forge`.

## Native source modules (no shadow music authority)

- `tools/platform_social.py`: Same platform SQLite database, owner-scoped public/private playlists, add/remove/reorder, draft albums with explicit confirmation; creator follower edges, idempotent likes, comments/block, idempotent notifications. Playlist/album song IDs are **SongPublication** IDs, never a CAS digest, private project ID, or user-supplied current revision. Each public song is checked by the Studio project's lawful artifact/read/host rights gate on every read.
- `tools/platform_workspaces.py`: Owner-invited roles `viewer` / `editor`; owner is immutable. Project association validates the original Studio project owner first. Collaborator project/audio reads recheck active membership before and after Studio read and pass the exact selected revision/artifact back through the Studio owner. Revocation blocks subsequent reads immediately. **Editor writes remain disabled pending change-isolation authority and multi-party race certification**; roles alone do not confer an unsafe write path.
- `tools/platform_billing.py`: Account-specific SQLite `BEGIN IMMEDIATE` grants/reservations/finalization; atomic no-overdraft spend; idempotent provider-event grants; quote→reserve→settle/refund. A `FAILED_PRE_COMMIT` result explicitly refunds; ambiguous/in-progress outcome remains reserved until authoritative reconciliation. The HTTP reserve/finalize routes fail **503** without a host-installed job authority. There is deliberately no browser mint-credits endpoint or integrated payment provider yet.
- `tools/platform_chat.py`: Bounded authenticated command compiler executing existing owner services: check balance, public catalog search, create private playlist, search/queue/create private playlist and **proposal-only** publish. Unrecognized prose rejects; publishing cannot bypass the ordinary exact revision/artifact/rights/approval path.
- `tools/studio_server.py`: Authenticated routes for platform-owned collections and operations, with principal derived from the existing PlatformStore's verified session. No changes to canonical `SongSpec`, `ProductionTimeline`, `ProjectRevision`, `ProjectManifest` or `RenderArtifact` authority.
- `tools/platform_identity.py`: Safest local SQLite initialization repaired: initializes WAL under in-process schema lock and **does not re-execute journal_mode=WAL for every new HTTP request**. Prior concurrent signups could throw `sqlite3.OperationalError: database is locked`, closing connections; reproduced then repaired.
- `index.html`, `platform-ui.js`, `studio-shell.css`: Extends existing single shell with private playlists, album drafts, workspace invitation/revocation, credits, follow/block, notifications, bounded authenticated platform Chat. Kept 6 bottom nav tabs with a 360px width; new controls live inside Profile and Chat views with >=48px touch targets and no overflow. Music editing still lives in existing Studio, not a new music backend.

## Evidence, as of Wave 2 source execution

| Gate | Observed |
|---|---|
| Domain RED-first | 15 tests errored on missing native modules |
| Domain GREEN | 15/15 PASS |
| Real HTTP RED-first | 5 API tests failed against original PR #37 routes |
| Concurrency regression RED | Existing identity concurrent-signup test crashed with SQLite `database is locked` |
| Concurrency/HTTP GREEN | 35 Wave2/HTTP tests PASS; 253 complete Python tests PASS in 74.730 seconds (includes original Studio regression) |
| Node | 39/39 PASS, zero failures/skips |
| Focused browser | 5/5 platform tests PASS (including Wave2 360px artist journey) |
| Existing full Chromium | **IN EXECUTION AT THIS RECEIPT'S DRAFT CREATION**. Must replace with final exact result; no success claim until terminal result. |

## Security invariants and unproven boundaries

1. Private playlists are unavailable to other accounts; public playlists themselves are shareable anonymously but qualified songs disappear after unpublishing or rights revocation.
2. Every album release requires the artist's explicit disclosure approval and existing qualified public tracks. An album never silently publishes a draft, historical R1, or unapproved master.
3. Follow/like actions are idempotent; blocked people cannot follow/like/comment; disabled comments are blocked; notification events are deduplicated.
4. Workspace invitation is NOT a CAS-owner bypass: binding requires the existing Studio owner to prove ownership, member audio requires exact authorized project/revision/artifact and active grant. Revocation rechecks.
5. No host configured payment verifier = NO webhook grants. No host configured generation-job outcome verifier = NO credit reservation/settlement API. Atomic local accounting is not a production payment integration.
6. Platform Chat supports a **bounded subset** of commands, not generalized natural-language execution across Suno's every feature. Publish returns `AWAITING_CONFIRMATION`; no audio revision, rights grant, or release committed from prose.
7. No final release claim while the exact A/B position + RS-002 full Chromium endurance, production auth, rights registry, per-user sessions, payments and deployed security remain held.
8. The SQLite schema is single-host pilot infrastructure. Horizontal scale, provider webhooks, rate-limiting, hostile account recovery, legal clearance, durable delivery, recovery fault injection, accessibility and phone hardware still need independent qualification.

## Minimum next repair

**P0 Studio A/B + Mobile QA:** Browser preservation failures observed on both original M045 and platform branch; instrument `__M044_AB_SWITCH__`, `__M044_AB_PROOF__`, media seek/play promises, and per-operation source revision fences. Do not increase assertion timeouts or skip tests to manufacture PASS. Repeat full `tests/*.browser.cjs` on exact branch with 0 failures and 0 skips.

**P0 Payment/security:** Host-signed provider webhook identity, owner-attested generation jobs and durable independent reconciliation; no speculative credits, invoices or provider charges.

**P0 Collaboration writes:** Exact studio Change ONLY This™ multi-actor principal and owner scoped permissions; no read-only viewer upgrade by changing UI.

**P1 Product completion:** Playlist removal/reorder mobile controls, full album editor, rich social feed, genuine notifications delivery, unrestricted conversational understanding and production data migrations remain future scoped implementation.

## JUSTIN 101

**WHAT CHANGED:** Real owner-bound social/album/workspace/credit/chat modules + mobile controls + concurrency repair.  
**FAILED/REPAIRED:** Concurrent SQLite WAL registration, public playlist anonymous read gating; both reproduced before repair.  
**PROVEN:** Local HTTP, real public WAV/revocation, no-overdraft credit races, rights-bound playlists, 360px owner-backed UI, full Python/Node and focused browser.  
**UNPROVEN:** Full Chromium regressions, external identity, provider payment/rights, multi-actor writes, product-wide Chat and deployment.  
**TEAM NEXT:** Browser A/B preservation repair owner, platform auth/payments/rights specialists, collaboration editor-write authority.  
**JUSTIN ACTION:** None for draft PR review. No expense, live billing or release approved.

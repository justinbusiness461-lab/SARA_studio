# PLAT-001 / PLAT-002 — Canonical Source Map and Multi-User Threat Matrix

**Scope:** First platform vertical slice, isolated from music/cinema main, pinned to the native Studio M045 source `862a7ed11f12835b92c4f0b5673241ae4362b8c2`.  
**Owner:** `SARA_studio` (repo ID `1427534706`). No writes to `dj_rezrxtion` or legacy `song_forge`.  
**Source authority:** `tools/studio_server.py` still exclusively owns `ProjectManifest`, `ProjectRevision`, source/artifact membership, `project_audio_bytes`, immutable media validation and CAS.  
**Platform additions:** `tools/platform_identity.py` stores authenticated principals, profiles, session token hashes and publication listings in SQLite with WAL + full synchronization. `tools/platform_catalog.py` is a derived publication/Explore/search projection. Neither is authoritative for SongSpec, revisions, audio digests, rights grants or cinema.  
**Mode:** `SARA_PLATFORM_AUTH_MODE=1` is an **opt-in local pilot**. Legacy local Studio behavior remains default; existing `local-studio-user` bootstrap is prohibited in platform mode.

## Authenticated source findings and repairs

| Severity | Before | Safest native change / denial | Proof |
|---|---|---|---|
| P0 | Anonymous GET / automatically issued a `local-studio-user` Studio session | Platform-mode GET / injects same-origin capability only, **no principal/session**; login issues hashed durable account session | ACC-01 |
| P0 | Older POST routes used local ambient principal or capability-only authorization | Platform mode allows only scoped projects and qualified M045 project-bound operations; all older local-only mutation routes explicitly return 403 pending owner adapter | ACC-05 regression RED→GREEN |
| P0 | CAS exists but does not authorize a public song or a cross-user stream | Public listing binds principal + current revision + explicit accepted output artifact + **host-only rights policy** + explicit artist confirmation; stream re-verifies lawful historical media | ACC-02/04; PUB-01/02/03 |
| P0 | Local project and session identities were unsuitable as multi-user identity | Account principal is stable `acct-...`; random session bearer only appears in HttpOnly SameSite=Strict local cookie; SHA-256 of token stored server-side | ACC-02, cold reopen |
| P0 | Public listing could expose drafts if built from arbitrary CAS scans | Explore and search are views solely over explicit active SongPublication; unpublish immediately denies public song audio, even before cache/search invalidation | PUB-01/03/04 |
| P1 | Two accounts might claim the same handle | SQLite case-insensitive unique handle constraint with transaction; one concurrent signup wins, other 409 | ACC-03 |
| P1 | Old offline cache may serve local session-injected HTML | Platform bootstrap is no-store; service worker no longer caches HTML; opt-in platform disables/unregisters SW | Chromium mobile login + static source review |
| P1 | Browser project/current pointer might be assumed authoritative | UI sends selected identity but server performs owner authorization, revision membership and physical audio validation | ACC-04 + PUB-02/04 |

## Narrow pilot test coverage

- `tests/test_platform_identity_and_catalog.py`: 10 local HTTP tests covering ACC-01 through ACC-05; PUB-01 through PUB-04; account/profile/session cold open.
- `tests/platform-identity-catalog.browser.cjs`: 360x800 + 390x844 create-account/login → Explore EMPTY → Library EMPTY → profile edit → logout → /api/me 403; enforces >=48px navigation, no horizontal overflow, no page errors.
- No external OAuth login, real user records, payment provider, email/SMS OTP, public-host deployment, offline authentication or live creative approval performed.
- All rights checks default to **BLOCKED 503** unless host explicitly configures an independently validated rights decision for the exact owner/project/revision/artifact. A client-supplied `rightsStatus` is rejected.
- The pilot **blocks unqualified legacy generation and write endpoints in authenticated mode**. This is an intentional fail-closed feature gap, **not full Studio parity**; owner adapters must be rebuilt without ambient local principals before release.

## Operating and release HOLDs (exact owner + wake condition)

1. **P0 External identity & production deployment** — Current password accounts are localhost-only prototypes using scrypt, not OIDC/Apple/Google/Microsoft/Discord or deployed HTTPS with secure cookies, CSRF/security headers, account-recovery/OTP and rate limiting. **Owner:** Studio platform/security. **Wake:** verified OIDC provider trust, real multi-device login/logout, hostile token replay and security audit, TLS/reverse-proxy configuration.
2. **P0 Owner-adapter capability parity** — M045 generation attempt take audio, scratch rendering, neural/write helper endpoints are locally authorized only or use incompatible header/session contracts; platform mode denies them. **Owner:** rightful music runtime/Work B. **Wake:** principal-bound authorization contracts, suite of per-account RED tests, no local fallback.
3. **P0 Publication rights** — The public release gate has no user-supplied rights shortcut, and is unusable without host-owned grant policy backed by true SampleAsset/model/voice/derivative evidence. **Owner:** SARA SampleAsset + legal. **Wake:** rights/consent registry and independent issuance/readback tests.
4. **P1 Profile media** — Avatar/banner CAS binding is **not implemented**, neither are verified handles or multiple artists per principal. **Owner:** platform/profile. **Wake:** authorized image upload + ownership/format validation + immutable profile asset references.
5. **P1 Catalog/product scale** — Explore is a bounded authorized list, not yet trending ranking, recommendations, feeds, moderation, pagination beyond initial limit or production index invalidation. **Owner:** catalog/discovery. **Wake:** catalog storage/index and multi-user privacy/abuse tests.
6. **P1 Durable multi-user production scale** — SQLite WAL full synchronization is appropriate for a local pilot, not independently certified for remote horizontal deployments, backups, PITR and service uptime. **Owner:** platform/infrastructure. **Wake:** deployed DB/backup/readback/failover and load testing.
7. **P1 Unified mobile shell** — 360px/390px browser pass on basic account/Explore/Library/profile. Actual Android/iOS device/assistive technology and full Studio+platform parity remain unproven. **Owner:** mobile QA. **Wake:** physical device evidence and full command parity.
8. **P1 Accounts, billing and support** — Subscription/credit ledger, payment processor, support, deletion and abuse workflows remain future slices, not claims from these green tests. **Owner:** platform/finance/security. **Wake:** authorized vendor contracts and transaction/recovery audit.

## No fabricated closure

This is a bounded local implementation milestone, **not a public sign-in launch**. `SOURCE → TESTED → REPOSITORY COMMITTED` are distinct from `DEPLOYED → PHYSICALLY VERIFIED → TECHNICALLY CERTIFIED → CREATIVE APPROVED → RELEASE READY`. No private CAS authorization from digest alone, browser selected revision, account handle or public listing.

**JUSTIN 101:** CHANGED — secure-mode gate, accounts, profiles, sessions, explicit release and mobile navigation. FAILED — legacy endpoint bypass reproduced RED and blocked GREEN. PROVEN — targeted functional and adversarial local tests. UNPROVEN — third-party SSO, true release rights, provider spend, multi-user production hosting. TEAM NEXT — owner-adapter/rights and OIDC provider qualification, then wider public product. JUSTIN ACTION — none for branch review.

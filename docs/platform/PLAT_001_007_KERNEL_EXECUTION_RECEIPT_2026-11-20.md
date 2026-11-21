# PLATFORM-01/02 · PLAT-001–007 · KERNEL Execution and Certification Receipt

**Timestamp:** November 20, 2026.  
**Canonical music/platform owner:** `justinbusiness461-lab/SARA_studio`, repo ID `1427534706`.  
**Exact source base:** `862a7ed11f12835b92c4f0b5673241ae4362b8c2` (M045).  
**Platform branch implementation head at receipt:** `f81a0854cb431ba584fe9111ecddb35932454fd0`; `main` `d6aa889a0def72bb8e1c87009a98d6c29e47067e` unchanged.  
**Delivery stage:** SOURCE + REAL LOCAL HTTP + KERNEL CHROMIUM TARGETED + GITHUB BLOB READBACK. **NOT deployed, not production authentication certified, not release-ready.**

## What actually changed

1. `tools/platform_identity.py`: opt-in local SQLite WAL/durable platform identity store, hashed sessions, salted scrypt passwords, unique public artist handles, profile edits, revocation; no duplicate SongSpec/project authority.
2. `tools/platform_catalog.py`: host-cleared, artist-approved SongPublication and public Explore/search/song pages, with each media read rechecked against Studio's owner, lawful revision→artifact binding, digest and current host rights policy.
3. `tools/studio_server.py`: `SARA_PLATFORM_AUTH_MODE=1` platform mode; anonymous GET / never mints the local principal; platform endpoints under verified cookie + same-origin capability; old ambient-local endpoints fail closed while native adapters are not qualified.
4. `index.html` + `platform-ui.js` + `studio-shell.css`: real account/Home/Explore/search/Library/Profile/mobile tab/player/Studio/Chat navigation and explicit release action. 360 and 390 pixel account journeys physically executed in Chromium.
5. `app-ui.js`: share-device account isolation: in platform mode ignore old `sf_project_ref` and `m045_attempt_pointer` localStorage and do not write new account-owned IDs into cross-account cache.
6. `service-worker.js`: offline local Studio ScoreCore shell restored **after stripping all session/capability bootstrap** before caching. Platform HTML remains network-authenticated; platform mode unregisters SW. This preserves local non-authoritative compile capability without caching authentication tokens.
7. `tests/test_platform_identity_and_catalog.py`, `tests/platform-identity-catalog.browser.cjs`, `tests/platform-account-switch.browser.cjs`, `tests/platform-offline-safety.browser.cjs`, `tests/platform-release.browser.cjs`, `tests/platform_release_fixture.py`: actual tests and deterministic fixtures; no mock public-song listing or invented rights grant.

## Evidence and exact status

| Gate | Result | Meaning |
|---|---|---|
| First HTTP tests RED | 9/9 error before feature implementation | Missing platform symbols, real red |
| Legacy unauthorized mutation RED | 1 failing assertion | Old local-only writer returned 400 rather than security 403 |
| HTTP/security GREEN | **10/10 PASS** | Session principal, profile, unique handle, CAS privacy, publication, unpublish, restart |
| Shared-device stale project RED | 1 FAIL | Artist B's Studio accessed Artist A's stored project reference, receiving an authorization failure but exposing prior ID path |
| Shared-device stale project GREEN | **1/1 PASS** | Platform mode ignores foreign localStorage project/attempt pointers |
| Existing PWA offline original full-suite | 1 FAIL | Local ScoreCore offline navigation stopped when HTML cache disabled |
| Original offline ScoreCore target repair | **1/1 PASS** | Local offline Studio compiles from cached ScoreCore |
| Offline cached-secrets browser | **1/1 PASS** | Cache/loaded page contains no original Studio session or capability bearer token |
| Real browser publish + SHA WAV + unpublish | **1/1 PASS** | Authorized R2 → approved public listing → exact media SHA → streaming revoked |
| Platform browser complete focused test glob | **4/4 PASS** | Signup/profile/Explore/Library/logout; account switch; offline; release |
| Full Python after core change, sequential | **218/218 PASS** | No Python errors; long-master prior concurrent timeout passed independently |
| Full Node units after privacy fix | **39/39 PASS** | No failures/skips |
| Existing complete Chromium suite BEFORE privacy/offline repair | **20 PASS, 2 FAIL, 1 CANCELLED (23 total)** | Not green. Failures: offline ScoreCore (repaired in focused test), R1/R2 A/B 15s wait; cancelled RS002 endurance on 150s deadline |
| Independent R1/R2 A/B on platform implementation | **3/4 PASS** | One exact-musical-position UI wait timed out |
| Independent R1/R2 A/B on unmodified M045 source | **3/4 PASS** | Different A/B test timed out under same browser/executor; does not alone establish a root cause |

## Cryptographic provenance of logs

These are SHA-256 of actual KERNEL test log bytes, computed at the executor boundary. All 12 raw text logs are durably committed under `docs/platform/evidence/kernel_20261120/` with exact GitHub readback. The log digests provide evidence identity, **not** independent cross-executor replay or release certification.

```
backend-green.log           17b40ba41616bc4dc82f1f8e0dfadca3a6e270b64683d36606b352fb32415c08
python-sequential.log       b23ff01abe76fe4b513a52966022bb9c9ee526310cd3ec3d35f887e500b76f8c
node-unit-final.log         0bc094361fb431c6d2faea70e5d936d82736ce7c1b4a60970fe756fe4013b52e
platform-browser-final.log  a01f69869e799f566409cb12cc57116a68717c69ba5171be0e8ec75a29f7a101
account-switch-red.log      3b90aca8ac90f01461fac9e61b280048c5b5bd82e666163be4d6719320d31380
account-switch-green.log    7ab9a9d1a6c2c752921f5f1d5028cc5ddf3a3975d42fc2875be5d92210a7265b
offline-green.log           027667778da1e7ddc40bddbc9c27bee802382c9aed2268850dd00c9d15d7197c
offline-security.log        abc9d1d979fce8eb3b2ef6b982e4e6e919251fcd50e1cf6b4e33d6335d8fc71a
publish-ui.log              4915ca0c8eb34a930f2249a1612b2edc698b2ee0248df0a9c0223f8e85a7bde6
node-browser-sequential.log cda3bb55b530741599692a242bde26b9ba03753efd72f167b75a0ed8f4ecda60
ab-isolated.log             9db2aaa3f1bced467bcd174c32ff81aaeb65f1ac16df242af4258384c4f4307f
ab-original-source.log      77fd39a70036cfbf5808d539252fa37d992b20be08cbd00e9c880d85ef526ef7
```

## Unclosed owner gates

- **P0 AUTH/INFRA:** Local pilot credentials and cookie handling are not a production OIDC/OTP flow, nor TLS-terminated Secure cookie and independent CSRF/rate-limit/abuse hardening. Owner: platform/security. Wake: approved provider, real account recovery, multi-device/OIDC/CSRF attack tests, deployed security receipt.
- **P0 MUSIC RIGHTS:** Host rights policy is injectable for local tests and always missing in normal startup. Publication returns 503 rather than self-declaring clearance. Owner: SampleAsset + release approval. Wake: verified rights and explicit accepted current revision/artifact with independent approval.
- **P0 STUDIO PRINCIPAL PARITY:** Existing generated-take/M045 attempts and local-only neural writer endpoints deny in multi-user mode, deliberately. Owner: music runtime/ScoreCore. Wake: authorized adapters with principal-bound source/revision operation receipts, no ambient principal.
- **P0 PHYSICAL A/B:** One true musical-position A/B Chromium case does not reliably meet completion timing; unmodified baseline also exhibits a different A/B wait timeout. Owner: Studio A/B + independent browser/performance QA. Wake: capture browser logs/transport state around wait, reproduce deterministically, RED test then smallest preservation-first repair; 0 fails on new exact source.
- **P1 RS-002 ENDURANCE:** Original integrated 390px test hit a 150s deadline and was cancelled in full browser suite. Owner: mobile/runtime QA. Wake: isolate with CPU/memory traces, prove correct R1→R2→A/B→Proof→Restore on a stable executor (not a weakened test).
- **P1 PRODUCT COMPLETENESS:** No provider SSO, avatar/banner CAS, social graph, subscriptions/credits, trending rank, video Hooks or Chat command coverage. Owner: respective future platform waves. Wake: scoped RED→GREEN, production deployment and authorization proofs.
- **P1 REGRESSION:** Full Chromium suite has NOT been rerun to completion since shared-device/offline fix. Only targeted passes plus original not-green suite exist. Owner: Browser QA/Work C. Wake: full 0-fail / 0-skip replay at exact final branch head and independent readback.

## JUSTIN 101

**WHAT CHANGED:** Native platform pilot, verified release/public playback, mobile account flow, cross-account browser storage isolation, safe offline local ScoreCore.

**FAILED:** R1/R2 musical-position wait, RS-002 bounded endurance, original offline ScoreCore. **REPAIRED:** original offline ScoreCore via credential-free shell; shared-device project leak; local legacy endpoint bypass.

**PROVEN:** 218/218 Python, 39/39 Node unit, 10/10 HTTP security, 4/4 platform Chromium targeted, exact WAV public read+revoke, GitHub blob verification.

**UNPROVEN:** production sign-in/recovery, rights issuance, full authenticated Studio parity, full Chromium suite, device security/release.

**TEAM NEXT:** Auth/release rights team + Studio A/B owner + mobile QA; keep draft until above holds close.

**JUSTIN ACTION:** None for branch review. No deployment/merge/purchases or artist approval required by this execution.

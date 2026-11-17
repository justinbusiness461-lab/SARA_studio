# M044 Manus Studio donor hardening — 2026-11-06

**Disposition:** HARDENING_ADVANCE — local donor only; NOT canonical product authority.
**Source:** user-supplied `code.zip` SHA-256 `a515e0d34f325e3aa6098b7d1ca96481e47abc77527ac4df0d9e86ce793919ac`.
**Reported Manus checkpoint:** `c4d758a62b516dcc2e18f5b2d0e5989927654972` — direct match to source ZIP UNVERIFIED.
**Canonical engine main inspected:** `14e2fb9cc55c8ce2909803a66d509915a18eb625`.
**Engine PR #10:** MERGED; **UI PR #11:** OPEN, still based on `bobby/m044-scorecore-foundation`.
**Execution:** local patch only; Manus managed workspace unavailable. No canonical source code modified by this donor build.

## Executed local proof
- New `server/studioGuard.ts` tests: **6/6 PASS**, Node 22 type stripping.
- Actual `server/studioStore.ts` with a deliberately unavailable DB in a dependency-isolated harness: **5/5 PASS**.
- Guard standalone `tsc --noEmit`: PASS.
- Changed TS/TSX syntax parsing: 0 diagnostics across five files.
- Complete `pnpm check/test/build`, managed browser, persistent DB, cross-process CAS, physical WAV decode/A-B: **UNVERIFIED** (dependencies/workspace unavailable).

Local donor patch adds expected-revision fencing, invalid section/track rejection, per-process per-project operation serialization, copy-on-write history, true DB-write status messaging, random browser Preview IDs, and honest oscillator-only preview labels. The source and full report were delivered as downloadable chat artifacts, not pushed to public main.

## Material findings — severity / evidence / owner / impact / blocker / next action

1. **P0 — NO PRODUCTION AUTH/TENANCY.** Evidence: `server/routers.ts` calls public procedures for song/project mutations and read. Owner: Manus backend/security. Impact: no authenticated ownership of private artist projects. Blocker: user/project identity integration. Next: authenticated, tenant-bound server project IDs; cross-tenant negative tests.
2. **P0 — NO REAL WAV AUDIO IN MANUS.** Evidence: `server/studioStore.ts` hashes preview metadata, `client/src/pages/Home.tsx` plays a generic oscillator. Owner: canonical Sound Forge engine + Manus adapter. Impact: preview cannot prove actual editable/rendered sound, R1/R2 audio comparison or physical locality. Blocker: rightful engine adapter. Next: reuse existing ScoreCore/ForgeRuntime/ProjectRevision/audio artifact owners; independently verify PCM digest, source revision, restart and playability.
3. **P1 — STALE/INVALID EDIT AND IN-PROCESS RACE.** Evidence: original prototype allowed any section/track, used mutable state, accepted calls without expected revision. Owner: Manus donor. Impact: silent wrong-history/conflicting edits. Action: repaired in local package; 11 focused offline checks PASS. Next: run complete Manus app and browser tests before accepting.
4. **P1 — PERSISTENCE MESSAGE TOO STRONG.** Evidence: original `getProject` called `getDb()` and inferred persisted=true from availability. Owner: Manus donor. Impact: false save confidence. Action: local donor now tracks actual DB-write success. Next: test database error and cold restart in managed runtime.
5. **P1 — CROSS-PROCESS RACE STILL OPEN.** Evidence: added project queue is in-memory and process-local. Owner: Manus backend / canonical revision owner. Impact: multiple workers can still race. Blocker: transactional CAS. Next: integrate canonical authority, avoid duplicating revision store.
6. **P2 — MISLEADING AUDIO UX.** Evidence: A/B panel auditions same oscillator, Export button was inert. Owner: Manus UI. Impact: inaccurate user expectations. Action: local donor labels metadata-only comparison and disables unsupported export. Next: real revision-bound audio playback.

## Next Manus execution contract
1. Read live checkpoint and diff against isolated donor ZIP before applying; never overwrite newer source.
2. Install frozen dependencies and run `pnpm test:preview-admission`, `pnpm check`, `pnpm test`, `pnpm build`.
3. Browser-test R0→R1→R2, stale edits, invalid target, two racing requests, refresh/reopen; prove DB durability separately.
4. Implement authenticated multi-user ownership before live launch.
5. Integrate canonical Sound Forge engine after PR #11's Work A/B gate, including actual audio identity and crash recovery.
6. Then build staged Remix Plan / selective editing with web/mobile parity; no duplicate music backend.

**SOURCE ≠ RUNTIME; PROMPT ≠ AUDIO PROOF; PREVIEW ≠ PRODUCTION.**
**JUSTIN 101:** Changed local Manus donor files and tests; blocked hosted Manus access/full build; proven 11/11 scoped offline tests; not proven managed app, physical WAV, release or merge; Justin action only required to attach the ZIP to the authenticated Manus workspace if hosted continuation is desired.

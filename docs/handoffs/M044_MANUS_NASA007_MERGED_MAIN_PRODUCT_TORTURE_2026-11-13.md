# M044 MANUS NASA-007 — exact-merged-main stress dispatch (2026-11-13)

**Category:** independent executable QA, not product code, not release certification. **Owner:** Manus independent product torture. **Status:** PREPARED / physical Studio execution remains BLOCKED in this executor.

## Live verified anchors
- Canonical music production owner: `justinbusiness461-lab/SARA_studio`, repo ID `1427534706`.
- PR #22 **MERGED**. Candidate `91ed45f67f8c0bd432a7f4afb5de7a9ebe1dbdf5`, merge commit `1ea3909a25a2365862bd6a1106cfb386d933a504`.
- Current `main` observed `749127ce0ce2cd08cdc5a6354626a078064f4704`. Compare merge → main: **one documentation file added**, `docs/audits/PF_MISSION_044_PR22_WORK_B.md`. App/backend product code unchanged.
- Work B's committed independent report records 66 Python, 11 Node, 3 R1 browser, 2 Generate/PWA browser, 4 R2/A-B browser and 1 R2 cold-reopen passing. Those are source-reported verified results, **not** locally rerun in this contribution.
- Exact current source Git blobs: `app-ui.js` = `a2185db2044074518658cfb8f62bf97ac7c14cb5`; `tools/studio_server.py` = `55a2b3b54fbc162faaa1b2c401ca979f3a210cea`.

## New independent executable contribution
Built local (not yet copied as executable files into GitHub):
- `nasa007_browser.cjs`: actual Playwright user-flow tester, 60 real A/B UI selections, exact audio bytes+PCM decode/SHA, same-position + Proof alignment, delayed late-R1 response, wrong-revision WAV request, aborted R1 stream, backend/browser restart with byte-identity check, Linux resource snapshots.
- `nasa007_contract.cjs`: strict no-contradiction validator for A/B COMPLETE, target revision/artifact, target Proof, transport and <=50ms position. PCM16 WAV parser. Product gate refuses synthetic evidence, missing two-principal denial or absent runtime metrics.
- `test_nasa007_contract.cjs`: 21 local Node tests with executable RED→GREEN evidence; includes full fail-closed entrypoint test with no repository checkout.
- One 45-case machine-readable NASA-007 product/security/performance execution matrix, all **UNEXECUTED** until actual Manus/Codex run.

**Physical execution this round:**
- Focused validator self-tests: **21/21 PASS** (local Node v22.16.0).
- Node source syntax: **PASS**.
- Missing-repo preflight: exit 2 / `BLOCKED_SOURCE`, `proofOrigin=NOT_EXECUTED`, 0 switches (PASS fail-closed).
- **Real Studio browser run:** 0/60; no exact checkout or Playwright available to this isolated executor. Actual WAVs and product security unverified.

**Single-upload artifact:**
`SARA_STUDIO_MANUS_NASA007_SINGLE_UPLOAD_2026-11-13.zip`.
SHA-256 `59f13384424469f152e9d111e5e1498d6885f67ef7d3fc0dca67f74524720304`; **11 ZIP members**, per-file manifest and archive test PASS, 45 test case definitions.

## First material source-backed limitation
At current `tools/studio_server.py`, `StudioHandler.do_GET` mints every local HTML session with `issue_studio_session(LOCAL_PRINCIPAL_ID)`, even when distinct browser contexts receive separate tokens. Thus **two tabs do not prove two different authenticated tenants**. Current loopback-local project session tests are bounded single-principal evidence. A genuine hosted multi-user isolation PASS requires server-side distinct authenticated principals and independently exercised cross-user denial with actual audio bytes. This is a hosted authorization **HOLD**, not a claim that the bounded local musical editor is broken.

Current PCM access is **POST /api/projects/audio** requiring session+capability and exact project/revision/artifact. Earlier PR #18 GET probe is **not** a drop-in match for the current POST route; adapt method/contract under rightful owner without exposing capability or raw CAS.

## Decisions and limitations
- No R3 redesign; PR #10/11/22 historic work not reopened.
- No Bobby/Work B/Work A source mutation, no direct main write, no product duplicate authority.
- RUNNABLE proves clean reproduction. Manus now tests product endurance and adversarial reality.
- Client request generation remains ephemeral presentation fence.
- Historical R1 is lawful/available but must not become current R2.
- Three verdicts separate: AUDIO VALIDITY vs MUSICAL EDIT CORRECTNESS vs PLAYBACK TRUTH. Human listening/GRAVEYARD FREQUENCY not done.
- A successful synthetic receipt never becomes a product PASS. Local one-principal endurance PASS never becomes hosted two-user PASS.

## Findings (severity — owner — evidence — failed boundary — smallest repair)
| Severity | Finding | Evidence | Owner | Next |
|---|---|---|---|---|
| P0 hosted | Distinct browser session tokens map to same `LOCAL_PRINCIPAL_ID`; no real two-user proof | `studio_server.py` 53-59, 945-951, 981-993 | Hosted authentication owner / Manus+Work B verification | approved multi-principal identity binding + real 2-user negative tests |
| P1 product | PR22 proves bounded local A/B, not 60 uninterrupted switches/faults | Work B audit + existing browser test inventory | Manus | run pinned NASA007 stress and retain real traces |
| P1 experience | Chat/Canvas/Workstream/Proof full artist journey and mobile parity not yet independently qualified | Work B audit explicitly limits claims | Work A/Pixel/Manus | actual 390px/desktop end-to-end with artifact Proof |
| P1 telemetry | RSS/FD/CAS-orphan growth unmeasured for sustained product flow | missing actual runtime vantage | Manus | collect real start/end/trend and exceptions |

## JUSTIN 101
**WHAT CHANGED:** first true merged-main NASA-007 test package, runnable source and 21/21 local tests, exact SHA evidence and 45-case matrix. **WHAT FAILED/BLOCKED:** actual browser endurance absent in this ChatGPT executor; hosted two-principal auth not established by current local server. **WHAT IS PROVEN:** PR22 merge/main relation, local strict-checker and fail-closed preflight, ZIP integrity. **WHAT IS NOT PROVEN:** any physical NASA-007 product PASS, deployed tenant security, creative music quality or mobile parity. **WHAT JUSTIN MUST DO:** no routine action; use one ZIP with existing Manus when executing the product torture gate.

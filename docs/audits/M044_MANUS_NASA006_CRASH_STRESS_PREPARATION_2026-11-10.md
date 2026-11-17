# M044 NASA-006 — executable crash-stress preparation and source-access audit

**2026-11-10 · Internal Manus QA lane · HARDENING_ADVANCE (preparation, not product PASS).**

## Refresh receipts
- Sound Forge main `14e2fb9cc55c8ce2909803a66d509915a18eb625`; PR #10 merged; PR #11 open/stale; PR #16 G3 contract-only; PR #17 independently reports pre-pending crash orphan; PR #18 existing QA branch.
- Forge research owner `dj_rezrxtion/main`: `cd8997c260f552d28c1230d16954a59203a78d57`; governance main: `f45ae27df34c9b53507bff653b59258f05eac020`.
- Project Files listed **50 records**, **18 Project source uploads**, 10 locally SHA-verified raw originals, 8 not mounted. Three attempted materializations returned 'no authorized uploaded backing file'. This is **EXECUTOR_VANTAGE_MISSING**, not a user re-upload request.
- Source reviewed: `tools/studio_server.py` blob `4b044628187a94ab2a80db818bccb84b9fd1518a`; Work B `independent_pre_pending.py` blob `885e80667c00ffafdd5f143f0b68dd01dbc25dec`; Work C report blob `3f46fbb905dfe94b671eae4dd1d072ae08b1da89`.

## New runnable artifact
`SARA_STUDIO_MANUS_NASA006_ONE_UPLOAD_2026-11-10.zip`
SHA-256 `d22d248fe6c62d70d4c4e9919ca821c082de19d1bc2140247b9a533a88b2988a`; **8 entries, ZIP+member SHA integrity PASS**.

Contains an owner-disjoint `crash_stress.py` with deterministic 60-case plan (20 each after artifact fence / after pending receipt / after historical receipt), new subprocess every case, twice-cold-reopen, SHA+WAV check, R1 single association, R2 authority, no duplicate revision and no pending orphan; includes `START_HERE_MANUS_NASA006.md`, 19 self-tests, fail-closed receipt and project source inventory.

**Executed locally:** 19/19 harness self-tests PASS; missing checkout invocation returns **BLOCKED exit 2**. **Actual repaired R3 executions: 0/60** because no successor SHA had been published on refreshed GitHub. Injection hooks must be checked against actual R3 diff; a missing hook is BLOCKED, never PASS. No product source or Manus workspace changed.

## Findings (severity / evidence / owner / impact / blocker / action)
| Severity | Evidence | Owner | Impact | Blocker | Next action |
|---|---|---|---|---|---|
| P0 | PR #17 + NASA-005 late R1 survives CAS but loses historical association | Bobby R3 / Work B | Lost history | R3 SHA unavailable | Publish and independently test successor with exact early kill |
| P0 | Main HTTP GET lacks tenant/revision/artifact-bound WAV stream | Bobby / Work A | No real app playback | G3 accessor missing | Narrow authenticated read; two-user live HTTP proof |
| P1 | PR #11 still stacked on old branch | Work A | Generate unqualified | retarget pending | Browser test ScoreCore script and actual Generate |
| P1 | Manus local `c307cb5e...` only user-reported | Manus executor | Remote continuity not proven | managed workspace inaccessible | preserve/export/push exact checkpoint |
| P1 | Eight Project source entries not locally mounted | source-vantage router | Partial archive inspection | authorized raw backing absent | use other accessible sources; do not demand reupload |

## JUSTIN 101
**WHAT CHANGED:** executable NASA006 QA packet + indexed-source access classification.  
**WHAT FAILED/BLOCKED:** R3 SHA and G3 WAV accessor still absent.  
**WHAT IS PROVEN:** 19/19 local harness tests, ZIP and file digests, preflight fail-closed.  
**WHAT IS NOT PROVEN:** 60 real crash trials, live two-user audio, hosted app, deployment.  
**WHAT JUSTIN MUST DO:** no routine step; existing Manus can consume the single ZIP after its executor resumes.

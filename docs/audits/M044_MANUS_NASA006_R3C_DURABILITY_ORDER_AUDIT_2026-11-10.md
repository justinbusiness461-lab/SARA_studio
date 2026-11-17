# M044 — Manus NASA-006 R3-C, independent durability ordering audit
**Date:** 2026-11-10. **QA lane:** Internal Manus. **Result:** HARDENING_ADVANCE — checker only, R3 physically UNVERIFIED.

## Refresh
Canonical `justinbusiness461-lab/SARA_studio` repo ID `1427534706`, `main` `14e2fb9cc55c8ce2909803a66d509915a18eb625`. PR #10 merged. PR #11 new head `1c857ba5463a908049f78c0888f7ba0a6b52cd46` remains on old Bobby base. PR #16 G3 DOC-only. PR #17 current head `3addd96ca3e3cd3324930a9eb2273ab21a909d14` contains early-crash negative. PR #19 Runnable checker HOLD based on Team Lead's contradictory PASS discovery. **Bobby R3 successor SHA absent** from live branch/PR refresh.

Source refresh: 28 locally accessible file-like source/delivery artifacts hashed, including `tlspec3.zip` (9 entries, integrity PASS) and previous NASA-006 ZIP (10 entries, integrity PASS). An executor's missing Manus private checkout is not evidence that the user's Project files are absent.

## First material QA defect (P1)
The prior NASA-006 `crash_stress.py` demanded R1 history count exactly 1 at **every** kill point. That is false at corrected `VALIDATED_NOT_PUBLISHED`: the exact digest, intended CAS identity and ownership must be durable, but CAS has **not** been published and R1 history must not claim a playable historical artifact.

**New explicit phase contract:**
- **Crash A**, `VALIDATED_NOT_PUBLISHED`: known valid staged attempt, digest and intended CAS durable, CAS absent, history counts `[0,0]`, never fabricate R1 playback.
- **Crash B**, `ARTIFACT_DURABLE`: exact CAS object published, orphan GET denied before reconciliation; two fresh-process opens recover exactly one R1 association `[1,1]`.
- **Crash C**, `HISTORICALLY_BOUND`: two fresh opens retain exactly one R1 association `[1,1]`, no duplicate or current R2 change.
- Each trial must retain observed SIGKILL-equivalent process exit, exact SHA/operation identity, proven fsync/event order, correct artifact hash/WAV decode, R2 unchanged, no phantom revision, no CAS orphan or manual replay.

## Executed local independent verifier evidence
New standalone `r3_contract.py` + `test_r3_contract.py`: **30/30 PASS**. Legacy runner self-tests **19/19 PASS**, total **49/49**. A synthetically valid 60-trial receipt passes a consistency check **without** claiming physical proof. A contradictory top-level PASS with Crash B historical count zero returns `FAIL_HISTORICAL_RECONCILIATION`, **exit 2**. The legacy crash runner must NOT judge R3 until its hook mapping and phase expectations are repaired.

Single-upload `SARA_STUDIO_MANUS_NASA006_R3C_DURABILITY_2026-11-10.zip`: **7 entries**, ZIP and per-member SHA integrity PASS. Archive SHA-256 `96cdd5e6970fc94088b273c2c0682c79171192e676c202da2b3a20c9d687ded1`. Verifier source SHA-256 `e54f683e8f2830e7be0599cf5ed7b4391d58ebce2df61e7c9d65c263421d4777`. Test source SHA-256 `de33162260feda89265896a6f8c0b30c5d8446f48df94aa980d05c551c0a717a`. Downloadable full audit SHA-256 `c7dfbc08c01d6634443e536cf399207ea555e588d560079dfa41988274d1ac3e`.

## Findings / owner / impact / blocker / action
| Severity | Evidence | Owner | Impact | Blocker | Next action |
|---|---|---|---|---|---|
| P0 | PR #17 + NASA-005 early-prepending orphan | Bobby / Work B | R1 valid WAV lost from history | R3 exact SHA absent | Durable digest/identity before CAS; R3 20/20/20 physical faults |
| P0 | Main has no tenant/revision-bound WAV accessor | Bobby/Work A | Real browser playback blocked | G3 endpoint absent | Owner-approved association-first authenticated WAV read |
| P1 | Legacy NASA-006 assessor expects R1 history even before CAS publication | Manus QA | False certification failure | Old phase model | New R3-C contract + physical new-hook mapping |
| P1 | Runnable PR #19 accepts contradictory PASS per independent Work B finding | Runnable | False-positive readiness | Checker repair unverified | RED contradictory receipt, enforce fields independently |
| P1 | Manus local branch not read back here | Manus executor | Auth continuity not proven remotely | Managed runtime not accessible | Snapshot exact branch/HEAD and tests before mutation |

## Certification / JUSTIN 101
**WHAT CHANGED:** Added executable R3-C verifier and 30 new negative tests in single verified ZIP; recorded audit here. **WHAT FAILED/BLOCKED:** No R3 SHA or G3 WAV access, 0/60 real R3 physical tests. **WHAT IS PROVEN:** 49/49 local harness self-tests, contradiction rejection, ZIP identity. **WHAT IS NOT PROVEN:** Real durability, playback, hosted app or release. **WHAT JUSTIN MUST DO:** No routine step; Manus may upload one ZIP and execute when exact Bobby R3 SHA is published.

**IMPORTANT:** This GitHub report records SHA-verified local code and evidence, not the executable bytes themselves. It is not an upstream product code change or a passed real R3 run.

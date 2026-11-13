# M044 Manus NASA-005 — one-upload dispatch and scope receipt

**Date:** 2026-11-10 · **Classification:** MISSION PREPARATION, not runtime/product certification.

The complete single-upload mission was created and validated in ChatGPT as `M044_MANUS_NASA005_ONE_FILE_EXECUTION_SPEC_2026-11-10.md` (406 lines, 38,269 bytes, SHA-256 `6db47f548f831a5ced632b1ac546029acda0272c86331dc301234ea59a4ded53`). This dispatch record is a **summary**, not the complete uploaded artifact or a new canonical product owner.

## Current actual frontier

- Sound Forge `main`: `14e2fb9cc55c8ce2909803a66d509915a18eb625`; PR #10 **merged** `27f954a2a3ce423717721d30e26c6a2cab485bba`.
- PR #11 remains on old Bobby base; its exact UI integration is not merged.
- PR #16 is **documentation-only** G3 proposed WAV accessor, not an implemented endpoint.
- PR #18 contains independent runnable QA; its 31/31 Python and 10/10 Node **local harness** tests have passed; **no live app certification**.
- **New P0:** Work C PR #17 `aac01bae054e8fc9cc51aea4621111ce5fe107aa` independently reports that killing the process after CAS audio durability but before durable pending ownership strands a valid R1 WAV on Sound Forge `main`. The earlier unit/normal probe PASS does not prove this earlier crash window. Treat full early-crash recovery as **HOLD** until independent reproduction, Bobby repair, and Work B qualification.
- Manus local app at `manus/nasa003-auth-bridge` evidence `f6001a15b314a2c90b1b2737d92117b41a360a1f` is **reported, unpushed/unverified remotely**; preservation-first, no overwrite.

## NASA-005 run gates

`G0` checkpoint exact existing Manus branch; `G1` clone/test PR #17 pre-pending kill without upstream edits; `G2` two-user authenticated tenancy; `G3` owner-approved revision-bound real WAV accessor and live HTTP; `G4` canonical prompt→R1 WAV→-12 scoped bass→R2 WAV→real A/B→cold reopen; `G5` synchronized CHAT / CANVAS / PROOF; `G6` 60 rapid A/B, late responses, multi-project/endurance/mobile; `G7` truthful real-client+real-backend deploy qualification.

Manus may continue its own branch's safe work while G1 engine repair is held. **Do not modify Sound Forge main, PR #11, Forge, governance, or invent a fake engine endpoint.** No direct browser access to `__STUDIO_CAPABILITY__`, raw CAS, or user-unbound audio. Use GitHub PR #18 tests and current owner APIs; report actual WAV/revision SHA values, two real auth users and separate audio-validity/music-correctness/playback verdicts.

## Source references

- PR #17 Work C negative evidence: https://github.com/justinbusiness461-lab/pulseforge-songforge/pull/17
- PR #16 G3 proposal: https://github.com/justinbusiness461-lab/pulseforge-songforge/pull/16
- PR #18 current executable QA: https://github.com/justinbusiness461-lab/pulseforge-songforge/pull/18

## JUSTIN 101

**WHAT CHANGED:** Created verified self-contained NASA-005 executable mission; GitHub dispatch record added to the existing QA branch.

**WHAT FAILED/BLOCKED:** G3 authenticated WAV retrieval not built, early-crash case newly reported failing on main; Manus live workspace not independently accessible.

**WHAT IS PROVEN:** Checked GitHub identities and created mission artifact SHA. Prior synthetic QA remains limited to its executed harness scope.

**WHAT IS NOT PROVEN:** Manus NASA-005 execution, live two-user playback, fixed early-crash recovery, or deployed Studio.

**WHAT JUSTIN MUST DO:** Upload the single `.md` to the existing Manus project when credits are available. No extra source ZIP or routine explanation is required.

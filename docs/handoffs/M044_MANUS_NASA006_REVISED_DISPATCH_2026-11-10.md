# Manus NASA-006 revised single-upload dispatch — November 10, 2026

**Classification:** EXECUTION SPEC, independent QA, **NOT** product certification.

**Canonical repository rename:** GitHub ID `1427534706` was previously `justinbusiness461-lab/pulseforge-songforge` and is now `justinbusiness461-lab/SARA_studio`. Same repository, not two owners. New confirmed main `14e2fb9cc55c8ce2909803a66d509915a18eb625`.

## Latest observed boundaries

| Source | Head | Status |
| --- | --- | --- |
| PR #10 | merge `27f954a2a3ce423717721d30e26c6a2cab485bba` | merged |
| PR #11 | `a53e3b8a55e7bb06747a19a9d19229b791881138` | open; still old Bobby base |
| PR #16 | `b1d3e00e94efeff3644d747369bd92ff821370f3` | documentation-only WAV contract |
| PR #17 | `7f509613b1bb975c570db661ac35cfdbc46cc9f6` | current early-kill regression and coupled recovered-WAV delivery contract |
| PR #18 | existing QA branch | independent NASA-004 tooling |
| PR #19 | `929073cd67fe29df89fb0d4b4ec351dd86a00aaf` | Runnable clean-room harness |

No **new Bobby R3 repair SHA** was visible at refresh. NASA-006 real R3 stress is **BLOCKED** until exact successor is published, not falsely marked PASS.

## New single-upload artifact

`SARA_STUDIO_MANUS_NASA006_REFRESHED_SINGLE_UPLOAD_2026-11-10.zip`

- SHA-256 `85cacb22e998d002d50a43a32b6e980a30030649d1f420c8a8af1aa1264d1d47`
- **10 members**, ZIP integrity and member digest readback PASS.
- Updated `START_HERE_MANUS_NASA006.md`: authoritative repo rename, current PR head pins, branch-preservation law, 60 crash tests, two-user WAV authorization, real R1/R2 A/B at same musical position, cold reopen, web/mobile parity, resource/performance gates.
- `internal/crash_stress.py` + `test_crash_stress.py`: **19/19 local harness tests PASS**; no candidate checkout causes **BLOCKED (exit 2)**.
- New P0 coupled discriminator: **the very same recovered late R1 WAV from crash restart must be delivered byte-identically over the authenticated revision-bound route; deny wrong revision, user and project.** Distinct successful fixtures do not establish this combined result.

**Certification ceiling:** Only harness correctness, archive integrity, GitHub identity and PR snapshots. Real R3 trials = 0/60, real authenticated HTTP = UNVERIFIED, hosted Manus playback = UNVERIFIED.

## Ownership / next action

Bobby owns R3 source and G3 artifact accessor, Work B qualifies and merges, Work A handles PR #11 retarget, Manus preserves managed local checkpoint and executes independent endurance on the next verified SHA. No product source, engine, private Manus workspace, governance, Forge or PR #11 mutation by this handoff.

No need for Justin to repeat the source ZIP. Upload **only the refreshed single ZIP** to the existing Manus project when its executor is available.

## JUSTIN 101

- **WHAT CHANGED:** identity-corrected, executable single-upload NASA-006 packet with recovered-WAV delivery coupling.
- **WHAT FAILED/BLOCKED:** Bobby's new R3 candidate, real authenticated WAV accessor and managed Manus runtime verification absent.
- **WHAT IS PROVEN:** 19 runner self-tests, archive digest, GitHub current identity/heads.
- **WHAT IS NOT PROVEN:** repaired recovery, two-user WAV delivery, Studio app or deployment.
- **WHAT JUSTIN MUST DO:** upload one ZIP when Manus can execute.

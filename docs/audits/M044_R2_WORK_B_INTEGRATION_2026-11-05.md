# M044-R2 Work B integration receipt — 2026-11-05
Repository: justinbusiness461-lab/pulseforge-songforge
Disposition: QUALIFIED_INTEGRATION / PASS — bounded headless vertical slice
PR10_HEAD: 9f200d5e3b45494cca4f46728cc9e3e8a64766fc
MERGED_SHA: 27f954a2a3ce423717721d30e26c6a2cab485bba
M044_MAIN_SHA: 27f954a2a3ce423717721d30e26c6a2cab485bba

## Executed evidence
Authenticated GitHub connector fetched candidate source, test files, dependency lock, existing handoff and qualification receipt. 18 locally executed source/test files were matched to Git blob identities. The pinned raw server bytes independently matched SHA-256. This was a connector-materialized source subset, not a full Git clone. Initial materialization appended a blank line; it was removed and all suites rerun on exact authenticated bytes.

Python 46/46 PASS; Node 8/8 PASS; HTTP/render/restart probe 19/19 PASS.
Additional executed assertions: R1 historical artifact exactly once; absent from R2 history; wrong sourceRevisionId rejected; R2 unchanged.
Malformed bytes, truncated WAV and inconsistent channel metadata rejected by the operation tests.
Separate-process termination at durable-pending-before-history-bind recovered on ordinary open without caller replay.
All three generated WAVs independently decoded using Python wave: PCM16, 44100 Hz, 2 channels, 463050 frames, 10.5 seconds.
Locality: 220494 changed frames; zero changed frames outside [220500, 445410), including declared 4410-frame tail allowance.

R1 SHA256: 908f6f5745ff3afd794aea296c5b9a23245d0778e18a4f37cf82e0e089cda399
R2 SHA256: ee0bec084d0c745748ca9fd6b413844c0568133eaa3ac40ef0e660ca939b7fd4
R1 late SHA256: a98d1da19494b08521a1d8f0f40b201e85cbffbc0db98f689e8dd881a7d0c94f
Late artifact is a declared one-LSB variation of the real R1 render; its distinct digest is a fixture discriminator, not a new composition.

## Source hashes
tools/studio_server.py: f2707c42cbce9b1958cf9bf64af95b1557005bfe40ec6f6ca113b0de9ea947a8
tools/m044_probe.cjs: e227581c0449b2a444ada82354d3dd7eb7fd4a4c7af154f46de6783dc303cae5
tests/test_m044_operations.py: 105a9ee076416ef7476c12c3108f3c6985ced784f47b79d9937ef421ed4bbf1e

PR #10 was marked ready and merged. GitHub readback confirms merged=true and unchanged tested head. Main commit was reread at MERGED_SHA. Server, probe, operation tests, session adapter, app-core, app-ui and package lock matched the tested candidate blobs.

## Findings and handoff
| Severity | Evidence / finding | Owner | Impact / blocker | Next action |
|---|---|---|---|---|
| Prior high defect: bounded regression PASS | Invalid historical WAV rejected | Bobby / B | Earlier garbage-byte reproducer closes in tested render path | Preserve regression |
| Prior high defect: bounded regression PASS | Admitted pending render recovers after process termination | Bobby / B | Recovery no longer requires caller replay after durable pending admission | Preserve process-crash test |
| Scope limit | Generic exports before durable render admission have no recoverable render ownership | Bobby / architecture | No claim that arbitrary unassociated CAS bytes recover | Keep admission boundary explicit |
| Unverified | Manus NASA endurance campaign | Manus | No independent endurance PASS claimed | Run exact merged SHA |
| Unverified | Work C full physical certification, D listening, browser UI, full song | C / D / A / Cody | Product completion remains unproven | C measure main; A retarget #11; UI owners implement |

## Access and environment
Python 3.12.14; Node v24.22.1; npm 11.9.0; Linux.
npm ci --ignore-scripts --no-audit --no-fund completed.
No Actions run or paid provider used. No listening or deployment claim.
Refreshed supplied Sara studio 5.txt repair/qualification sections, PR #10, candidate commit/diff, repository root/docs/tests listings, source files and existing main receipt.
Root AGENTS.md absent from repository listing. Broader project corpus, Floot runtime, separate governance repo and latest sonic blueprint were not fully refreshed; UNVERIFIED and outside this bounded integration decision.
Unavailable attachments: ELEVEN_MUSIC_DONOR_FORGE_2026-10-19.zip, all2.zip, SoundForge-Studio-Release-v2.18.zip. They were not read and were unnecessary for this qualification.

## Gates
M044_VERTICAL_SLICE_QUALIFIED = PASS
AUDIO_ADMISSION = PASS
LATE_R1_HISTORY = PASS
CRASH_RECOVERY = PASS — after durable pending admission, process termination
R2_AUTHORITY = PASS
REAL_AUDIO = PASS — decoded fixture, no listening certification
MANUS_NASA = UNVERIFIED

## JUSTIN 101
WHAT CHANGED: Independently reran repaired candidate, undrafted and merged PR #10, reread main.
WHAT FAILED/BLOCKED: No failed product assertion in this bounded run. Manus/C/D/UI gates remain.
WHAT IS PROVEN: Exact source identities, 46 Python + 8 Node + 19 integration checks, decoded distinct late WAV, bounded locality, restart/history/current authority.
WHAT IS NOT PROVEN: Full-clone clean room, power-loss durability, comprehensive endurance, browser UX, listening quality, finished Studio.
WHAT JUSTIN MUST DO: Nothing. Downstream owners have the exact main SHA.

# S.A.R.A. Studio / M044 — Internal Manus NASA-004 Independent QA

**Date:** 2026-11-10. **Consequence:** HARDENING_ADVANCE (QA-only). **Release status:** UNVERIFIED.

## Source refresh / identity

- Sound Forge owner: `justinbusiness461-lab/pulseforge-songforge` `main` `14e2fb9cc55c8ce2909803a66d509915a18eb625`; PR #10 merged. PR #11 open on old Bobby branch, `cb80d4fe06cc1148651787872ad89216c20328f3`.
- Forge research owner: `justinbusiness461-lab/dj_rezrxtion` `main` `cd8997c260f552d28c1230d16954a59203a78d57`.
- Governance source: `justinbusiness461-lab/engineering-organization-governance` `main` `f45ae27df34c9b53507bff653b59258f05eac020`.
- Manus managed app: `manus/nasa003-auth-bridge` latest checkpoint `f6001a15b314a2c90b1b2737d92117b41a360a1f` **REPORTED only**; not available remotely; not overwritten.
- G3 bridge: PR #16 documentation-only; no qualified authenticated revision-bound WAV route proved on main.

## Executed work

1. Reused the prior real-byte WAV and locality verifier; executed **15/15** Python synthetic unit tests (PASS).
2. Built a real-HTTP GET-only external acceptance probe supporting **two independently authenticated** users, with 12 fixed own/cross-user/anonymous/history/artifact/WAV verification cases. Executed **16/16** tests against a disposable localhost HTTP server (PASS), with negative cases for cross-user leaks, malformed WAVs, wrong audio hash, wrong/missing source revision header, redirect and target tampering.
3. Built a non-production A/B publication-fence reference; executed **10/10** Node tests (PASS), including 60 rapid selections, stale R1 completion, R2 current preservation, canceled playback, invalid digest and explicit historical R1.
4. Executed live probe with no credentials: **HOLD / exit 2**, 0/12 actual authenticated cases attempted; correctly fail-closed.
5. Ran SHA-256 and Git blob readback for new source, verified ZIP integrity and packaged logs; no private media, credentials or proprietary donor code.

**Total independent harness self-tests: 41/41 PASS.** These are synthetic/local-harness tests. They are **not** live hosted application results.

## Severity, evidence, impact, owner, blocker, next action

| Severity | Finding / evidence | Owner | Impact | Blocker | Next action |
|---|---|---|---|---|---|
| P0 | Mainline Sound Forge serves project metadata but has no verified authenticated revision-bound WAV read route, as mapped in PR #16 | Bobby / Work A | Cannot play real authenticated R1/R2 artifacts inside Manus | G3 | Implement narrow lawful artifact retrieval seam and independently qualify |
| P0 | Manus auth patch reportedly local at `f6001a15...`, not retrievable via GitHub | Manus | Cannot independently validate actual app owner isolation or port tests safely | Remote source unavailable | Export/push exact checkpoint before merge/host qualification |
| P0 | Unknown current hosted audio route, two real test sessions and canonical source identities | Manus / Work B | Live two-principal HTTP probe cannot execute; false-certification risk | Qualified G3 runtime absent | Supply approved private fixture and actual two sessions, execute 12 required GET cases |
| P1 | A late R1 response could overwrite R2 playback without a client publication fence | Work A / Cody | Wrong audio/current label during A/B | Actual UI integration not proved | Adopt/test ephemeral generation fence; verify 60 live browser toggles |
| P1 | Valid PCM bytes may still represent wrong musical edit | Work C / Music Specialist | Audio admission can be misread as musical correctness | Musical A/B unavailable | Check exact MIDI delta, audio edit locality and auditory quality separately |
| P1 | Preview and Proof surface behavior is not yet verified on mobile | Manus / Pixel / Chat D | Capability-demoted mobile workflow | Hosted browser acceptance pending | Execute same project/revision actions at desktop and mobile widths |

## Reproduction

```bash
python3 -m unittest discover -s tests/manus-nasa004 -p 'test_*.py' -v
node --test tests/manus-nasa004/transport_fence.test.cjs
```

This is the **GitHub QA branch source**, not an attempt to use the local Manus app. A separate downloadable ZIP includes the same tested source bytes, logs and a credential-free example fixture.

## Integrity

Artifact: `SARA_STUDIO_MANUS_NASA004_INDEPENDENT_TEST_HARNESS_2026-11-10.zip`  
ZIP SHA-256: `fe2aba86275101224c15c9d13e26883f2b1545c541382397a3b5365fe9c82972`  
Entries: 14, ZIP structure: PASS.

GitHub repository additions are only under `tests/manus-nasa004` plus this audit. Source commit/PR can be verified by readback. No engine, Manus workspace, Forge authority or PR #11 mutation. No deployment or merge.

## JUSTIN 101

- **WHAT CHANGED:** Executable read-only Manus NASA-004 HTTP verifier, A/B publication-fence reference, reproducibility tests and pinned QA evidence.
- **WHAT FAILED/BLOCKED:** Live two-principal G3 test cannot run without an authenticated audio route and actual independent sessions.
- **WHAT IS PROVEN:** The external harness passes 41 synthetic/local self-tests and credential-absent invocation fails closed.
- **WHAT IS NOT PROVEN:** Real Manus app security, real R1/R2 hosted playback, browser transport race, mastering/listening or production deployment.
- **WHAT JUSTIN MUST DO:** No routine step. Once the owner-approved G3 connector is present, the application executor needs to run the GitHub QA tests and supply live evidence.

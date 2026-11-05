# M044 — executable vertical slice candidate

Owner: BOBBY. Date: 2026-11-01. Work B integration/qualification pending.

## Result

Prompt -> bounded MusicIntent -> existing SongSpec -> persisted composition R1
-> actual WAV A -> section bass octave edit -> persisted composition R2 -> actual
WAV B -> SIGKILL -> restart -> exact current project and WAV reproduction.

Executed: **42 Python regression tests, 8 Node tests, 16 HTTP/render/restart checks**.
The seven new Python cases cover replay, changed-payload conflicts, invalid IDs,
late-render CAS rejection, recovery before pointer promotion and ambiguous reply
after promotion. Two Node cases cover capture before await and no stale retry.
RED runs preceded implementation; final GREEN logs are retained in
evidence/m044/integration/. Existing tests ran as shared-server regression checks,
not as a reopened M043 certification campaign.

## Exact source and qualification

B's prior qualification is main commit 1173fb05a9efd476a4d8ea3ea546121cd02e36c7,
evidence/m044/WORK_B_SYMBOLIC_QUALIFICATION.json, against candidate caeac41b....
Source/environment hashes for this executed successor are in source-pins.json.
The remote source tree is byte-identical to the locally executed committed tree.
Subsequent evidence commits do not change that source identity or M043's freeze.

## Owner preservation

- No changes to app-core.js, app-ui.js, lyric_timeline.py, cinema, UI or DSP.
- m044-session.cjs delegates to exact existing parser/render/WAV functions in
  isolated VMs and uses only existing HTTP export/commit/open routes.
- studio_server.py adds an optional operation receipt to existing immutable
  ProjectRevision core. Its digest covers the complete request, including base
  revision, output/source bindings and edit context. Project lock serializes
  lookup, CAS and promotion. Only committed ancestry qualifies as replay truth.
- Same operation ID/identical payload returns the original revision with the
  current manifest; it does not reselect history. Changed payload returns 409.
  IDs are project-scoped. No new scheduler, project format or operation ledger.
- An edit rereads its immutable base and clears obsolete output bindings while
  preserving source assets. Existing server logic conserves lyric authority.
- A render captures spec, source bindings and revision before awaiting. Its
  completion commits against that captured revision only. 409 ends the attempt;
  there is no automatic rebase/retry. Exported unadmitted bytes may remain in the
  existing object store; no garbage collection or orphan promotion is added.
- A composition save and its later render binding are distinct immutable
  revisions, following the existing full-snapshot API. The receipt names both
  final rendered R1/R2, each retaining its composition parent. It does not pretend
  that an already committed revision acquired mutable output fields.

## Actual fixture and locality

Original deterministic four-bar instrumental engineering fixture: 96 BPM, E minor,
4/4, seed 44044. Intended section selection is bars 3–4, bass minus 12 semitones.
Not BAD HABIT, not GRAVEYARD FREQUENCY and not a musical-quality candidate.

Both WAVs: PCM16, 44,100 Hz, two channels, 463,050 decoded frames, 10.5 seconds.
Existing renderer is dual mono. Two channels do not establish stereo interest.

Edit interval [220500,441000) frames, declared allowance 4,410 frames (100 ms).
220,494 frames differ. First changed frame 220506; last 442056.
**Zero changed frames outside the declared edit plus allowance.** This is a
conservative allowance for this existing renderer, not a universal effect-tail
claim. Non-target symbolic structure is deeply equal to its pre-edit value.

R1 WAV SHA256: 908f6f5745ff3afd794aea296c5b9a23245d0778e18a4f37cf82e0e089cda399
R2 WAV SHA256: ee0bec084d0c745748ca9fd6b413844c0568133eaa3ac40ef0e660ca939b7fd4
Decoded PCM digests, revision IDs, bindings and every check are in receipt.json.
R1.json/R2.json retain exact authoritative snapshots; WAV bytes are committed.

## Reproduce

Declared dependency installation: npm ci --ignore-scripts --no-audit --no-fund

    python3 -m unittest discover -s tests -v
    node --test tests/scorecore.test.cjs tests/m044-session.test.cjs
    node tools/m044_probe.cjs /tmp/soundforge-m044-proof

Use a new empty output directory when retaining independent proof. The probe
starts a loopback-only server on an ephemeral port with a temporary export root,
acquires its per-process capability, and kills/restarts it. It deletes temporary
server state only after retaining snapshots, audio and receipts. No browser cache,
paid provider or Actions execution is required. Probe receipts contain no capability.

## Limits / Work B next action

This is an executable headless integration tool, not browser wiring or UX approval.
No release/package is produced or promoted. Current packager includes tools/*.cjs
but not Node test files; release packaging/test inventory needs B's later review.
No stereo upgrade, mastering, trained vocals, LUFS/true-peak certification,
independent C measurements, D listening, arbitrary bar-range editor or 80-bar song.
The public full-SongSpec API remains trusted-caller snapshot admission; these tests
qualify the new captured-input path, not malicious caller proof of audio generation.
Replay lookup traverses committed ancestry; long-history indexing/performance is
not qualified. No claim of cross-host execution or power-loss resilience.

Before merge, B should independently run exact source, inspect operation receipts,
verify late-result/replay semantics and conserve this evidence. Then B determines
freeze and hands exact audio/revisions to C/D. BOBBY does not promote M044 PASS.

## JUSTIN 101

WHAT CHANGED: existing project owner now retains optional replay receipts; new
headless session/probe executes generation, save, render, edit and recovery.
WHAT FAILED/BLOCKED: initial tests exposed absent replay behavior; fixed. Direct
Git push lacked credentials; authenticated connector retains the candidate instead.
Superpowers package unavailable. Six unavailable attachments remain outside scope.
WHAT IS PROVEN: 42 Python + 8 Node + 16 integration checks; actual WAV locality;
exact cold reopen and rerender. See source pins and raw logs.
WHAT IS NOT PROVEN: independent B/C/D qualification, browser workflow or good music.
WHAT JUSTIN MUST DO: nothing. Next owner is Work B.

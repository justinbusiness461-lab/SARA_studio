# M044 Work C — mainline physical audio and recovery receipt

Date: 2026-11-10 ET. Repository: justinbusiness461-lab/pulseforge-songforge.
Live default branch at execution: `14e2fb9cc55c8ce2909803a66d509915a18eb625`. PR #10 was merged at `27f954a2a3ce423717721d30e26c6a2cab485bba` per the mainline receipt. Work C tested current main directly and made an evidence-only change.

| Gate | Verdict | Scope |
| --- | --- | --- |
| Audio validity | PASS | Three fresh PCM WAVs passed strict RIFF preflight and complete FFmpeg decode. Six malformed fixtures failed preflight. Engine malformed admission unit also passed. |
| Musical edit correctness | PASS | Four target bass events moved exactly −12 semitones in section `sec-7680`. Canonical SongSpec otherwise compares equal, including timing. Decoded PCM has zero changes outside the section and its 100 ms release allowance. Audible isolated pitch and artistic quality are unverified. |
| Playback authority | PASS / UNVERIFIED | PASS for engine artifact identity, current R2, ordinary late R1 history and cold reopen. UNVERIFIED for authenticated WAV streaming, actual browser playback, A/B, and mobile. |
| Crash recovery | FAIL | The post-pending crash test passed. The earlier kill after the artifact durability fence, before the ownership record, lost the R1 history association on fresh reopen. |

## Physical measurements

Fresh engine integration probe: 19/19. Project `f6aab3985aee4ea69bb0e865218d2a42`.
Captured R1 `251ea0797a563268ff0d558383f1b094a0cd6c6baed1ceafabe2cf3623515d8c`.
Current R2 `66f4ba222eb56b3d64c560f9de9de25ef932abd85454596aa3a23d9f4b3258fb`.
The engine probe verifies the late artifact is distinct, is attached to captured R1 and survives normal cold reopen. It adds one LSB to distinguish the late fixture.

| Artifact | WAV SHA-256 |
| --- | --- |
| R1 | `908f6f5745ff3afd794aea296c5b9a23245d0778e18a4f37cf82e0e089cda399` |
| R2 | `ee0bec084d0c745748ca9fd6b413844c0568133eaa3ac40ef0e660ca939b7fd4` |
| R1 late | `a98d1da19494b08521a1d8f0f40b201e85cbffbc0db98f689e8dd881a7d0c94f` |

All three: signed little-endian PCM16, 44,100 Hz, two channels, 463,050 frames, 10.500 s, zero invalid samples and zero full-scale samples. PCM16 cannot encode nonfinite samples. FFmpeg and Python WAV decoders produced identical PCM for each file.

| Artifact | Sample peak dBFS | True peak dBTP | LUFS-I | DC L/R (normalized) | Exact-zero frames | Longest exact-zero run | L/R correlation |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| R1 | −9.9043 | −9.3 | −28.6 | 0.0001062964 / 0.0001062964 | 21,756 | 0.450 s | 1.000000 |
| R2 | −9.9558 | −9.4 | −28.8 | 0.0001124184 / 0.0001124184 | 21,630 | 0.450 s | 1.000000 |
| R1 late | −9.9043 | −9.3 | −28.6 | 0.0001062965 / 0.0001062964 | 21,755 | 0.450 s | 0.9999999999987 |

True peak and loudness come from FFmpeg ebur128 with true peak enabled, rounded to tool output precision. These are fixture measurements. R1/R2 are dual mono. Exact-zero runs characterize silence, with perceptual dropout unverified. Independently comparing decoded R1/R2 PCM found 220,494 changed frames from 220,506 through 442,056 inclusive, all within the permitted interval `[220500, 445410)`. The 100 ms allowance is 4,410 frames.

## P0 — historical audio can become unreachable on process death

**Owner** Bobby for repair, Work B for independent verification.
**Evidence** On exact main, Work B's published reproducer exited its child at the real `project_artifact_fence` return, before pending record creation. The fresh reopen used no caller replay. Artifact `aa8c4d282e333d204368f18f88ec71303d58c4c45e27839c7991598a2899f7d1` survived and passed hash and WAV validation. Captured R1 `485ec37ea63b4e391a5a2b213db9afc63b934ee4547501449a32aa333262082c` had **zero** matches. Pending count was **zero** and R2 stayed current.
**Impact** A valid completed WAV can become unavailable from the source revision's history.
**Blocker** Full automatic historical crash recovery from durable state.
**Next action** Persist authenticated render ownership ahead of the artifact durability window and rerun the exact early and later crash cases. Preserve subordinate R1 history and R2 current authority. This finding applies to live main and does not change the merge receipt for PR #10.

## Reproduce

- Use Node v24.22.1, Python 3.12.14, FFmpeg 7.1.5 and the repo lockfile. In the exact checkout run `npm ci`, then `node tools/m044_probe.cjs /absolute/output`. Retain generated WAVs, receipt and R1/R2 snapshots for comparison. Media are reproducible with the pinned probe.
- Run the PR #14 preparation checker at commit `38ea46833d2f31cf85fe755538990c1d356af57b` against that checkout and all three WAVs. Work C preflight rejected garbage, truncation, bad RIFF length, wrong channels, inconsistent byte rate and inconsistent block alignment (6/6). With FFmpeg, decode using `-nostdin -v error -xerror -i INPUT -map 0:a:0 -f s16le OUTPUT` and measure using `-af ebur128=peak=true -f null -`. Compare four-byte PCM frames using section tick boundaries and the declared tail.
- Run `PYTHONPATH=tools:tests python3 -m unittest -v test_m044_operations.OperationTests.test_malformed_historical_wav_rejected test_m044_operations.OperationTests.test_crash_before_history_bind_recovers_without_replay` (2/2).
- Run the [Work B early-kill reproducer](https://github.com/justinbusiness461-lab/pulseforge-songforge/blob/c107da1308dcd972676d237d33b8c318f7d34f33/evidence/work-b-m044-r2-crash/independent_pre_pending.py) from a temporary directory, with the exact checkout's `tools` and `tests` on `PYTHONPATH`. Update its hard-coded reported target SHA to the test pin above. Inspect the JSON verdict. Exit 0 means the reproducer executed.
- SHA-256 source pins: `tools/studio_server.py` `f2707c42cbce9b1958cf9bf64af95b1557005bfe40ec6f6ca113b0de9ea947a8`, `tools/certify_mix.py` `142371900128090b388db11403617ee49cb2dda18a821c077c8ffbb0d1e4d6c5`, `tools/m044_probe.cjs` `e227581c0449b2a444ada82354d3dd7eb7fd4a4c7af154f46de6783dc303cae5`.

Refresh scope: current coordination, accessible project source inventory, live Sound Forge main and PR refs #10/#11/#14/#16, mainline audit, preparation and Work B reproducer. Floot, separate organization governance, current sonic benchmark and hosted runtime remain unverified in this execution. This is a synthetic instrumental engineering fixture and provides no GRAVEYARD FREQUENCY listening evidence.

## JUSTIN 101

- Changed — Measured three regenerated WAVs on current main and reproduced the earlier crash case.
- Failed or blocked — Durable WAV can be stranded before pending ownership. Hosted playback awaits an integrated authenticated accessor and actual UI.
- Proven — Valid fixture audio, exact symbolic bass edit, PCM locality, bounded history and current output identity.
- Unverified — Isolated bass listening, artistic quality, browser and mobile playback, and power-loss recovery.
- Justin action — None. Bobby owns the crash ordering, Work B verifies, and Chat D owns the connected product attack.

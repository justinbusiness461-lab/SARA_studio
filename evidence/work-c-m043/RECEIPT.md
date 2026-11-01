# Work C Mission 043 — physical signal timing and recovery

Tested freeze: 076aed8d438a938119a7c2d5b34bb5eeb3ba4409. B freeze receipt authenticated from docs/audits/PF_MISSION_043_FREEZE.md. PR #6 merged.

LYRIC_TIMING_PHYSICAL = PASS — bounded signal-placement measurement
LYRIC_REVISION_RECOVERY = PASS — bounded fresh-process HTTP workflow

Neutral harness: exact-zero reference plus four invalid-bound cases pass. Independent measurement validates decoded PCM digest, frame count, integer ranges, stable occurrences, phrase containment, parent lineage and unchanged correction timing. Maximum error 8.5 ms; median absolute start 4.25 ms, end 4.5625 ms. A declared 10 ms measurement tolerance is used for this C receipt; it is not a pre-existing product acceptance standard.

25/25 freshly executed frozen-owner HTTP workflow checks PASS, including process kill/restart, cache-free reopen by project ID, R1 retrieval, R2 current, stale project and lyric rejection, audio unchanged, and unknown/empty no-transcript instrumental case. C independently recomputed timing from the resulting objects and actual decoded WAV. Harness and full resulting R1/R2 records are retained alongside this receipt.

Fixture: synthetic spoken Flite, supplied text, 8000 Hz mono, 17539 frames, 2.192375 seconds. Ground truth means construction placement bounds, not human phoneme annotation. No ASR, singing, listening quality, browser/PWA or general vocal detection certification. No broader Mission 043 promotion; D and Runnable remain separate owners. Crash-window verification was not rerun by C this turn.

Cinema: current R5 production packet remains remotely reachable at fixtures/3d/production-packet.v2-r5.json in dj_rezrxtion; blob dfc8268172472dc61782d465cc15c415229492a7 matches the supplied historical packet identity. Release digest e5e26578dbc9b7a81c8c6c4edf7f4e6881160806d6c2020654cae867f34451ae. No cinema mutation or render. Media-byte reachability and all R5 source pins were not reverified; full non-invalidation remains UNVERIFIED.

Refresh limits: accessible project corpus, GitHub candidate/freeze and cinema packet inspected; Floot runtime and independent governance repository not refreshed. No certification claimed for those surfaces.

JUSTIN 101
WHAT CHANGED: C executed the frozen lyric workflow and retained independent signal timing.
WHAT FAILED/BLOCKED: private cinema CLI clone lacks credentials; connector packet read succeeded. Full media/source-pin verification incomplete.
WHAT IS PROVEN: bounded synthetic guided-alignment timing and 25 workflow checks.
WHAT IS NOT PROVEN: ASR, singing, perceptual alignment, final lyric gate, full cinema non-invalidation.
WHAT JUSTIN MUST DO: nothing; D/Runnable own remaining independent gates.

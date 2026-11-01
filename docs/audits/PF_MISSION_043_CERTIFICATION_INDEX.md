# Mission 043 — Authoritative certification index

Updated: 2026-11-01. Owner: Work B. Evidence consolidation only.

## Frozen product authority

- M043_FREEZE_SHA / M043_MERGED_SHA: `076aed8d438a938119a7c2d5b34bb5eeb3ba4409`
- PR #6 head: `95ebbe4ae9e2c8588976ccb2e571f8294149f941`
- Release: **2.20.0**
- Parent M042 freeze: `7c92fe7a39d6b4209be510d02781adb6a1ef4182`
- C evidence PR #7 head: `1f59490cae892b56eb5d90e1c34863acb778dc1d`
- C evidence merge: `3fc4759789989d317d4834a06a3b62ee783618d3`
- D evidence source commit: `9c7ff3af40be67b676102d3a30ade037021ec1e4`
- Runnable receipt commit: `b9e9b851bd57bc0792fea7ac0505d6cb4f40c30a`

Evidence commits do not replace the product certification freeze.

## Fixture identity

Synthetic Flite spoken **rise higher**, supplied candidate text **rise fire**.
Method: `known-text-energy-islands-v1`; recognition confidence unknown/null.
PCM encoding s16le, 8,000 Hz, mono, 17,539 frames, 2.192375 seconds.

- WAV SHA-256: `b64d26f624da0722337be7153ab01296ef4c645a68e6527d9b6ac9946ab904e3`
- Decoded PCM SHA-256: `4746aca332f19dfc72e45383a75e7a876f6c8e09f8e5b10df149725441a051bb`
- R1 revisionId: `84925a9dfd6e2de09c04ed9ae2ab07118a0eeceb4a0014d1c8c59a0888795abc`
- R2 revisionId: `29ccc96908571632e5a323385a8230a88a0e805d026606ba5b9c8a7295160b07`
- R2 parent is R1. TEXT_ONLY correction changes occurrence w1 from fire to higher.
- Container digest, decoded PCM digest and domain revisionId are distinct identities.

## Retained evidence chain

All links below select immutable source commits; C and D files are also consolidated on main.

| Owner | Evidence | Recorded result |
|---|---|---|
| B | [Qualification/freeze](https://github.com/justinbusiness461-lab/pulseforge-songforge/blob/81a9198011fc00127de382c4ad05e1cea719d723/docs/audits/PF_MISSION_043_FREEZE.md) | 35/35 unit; bounded authority qualification |
| C | [Physical receipt](https://github.com/justinbusiness461-lab/pulseforge-songforge/blob/1f59490cae892b56eb5d90e1c34863acb778dc1d/evidence/work-c-m043/RECEIPT.md) | 25/25 workflow checks; timing/recovery PASS bounded |
| C | [Measurement](https://github.com/justinbusiness461-lab/pulseforge-songforge/blob/1f59490cae892b56eb5d90e1c34863acb778dc1d/evidence/work-c-m043/measurement.json) | Maximum boundary error 8.5 ms |
| C | [R1/R2 recovery records](https://github.com/justinbusiness461-lab/pulseforge-songforge/blob/1f59490cae892b56eb5d90e1c34863acb778dc1d/evidence/work-c-m043/recovery.json) | Source/timing preserved; fresh process, no cache; stale rejects |
| D | [Adversarial report](https://github.com/justinbusiness461-lab/pulseforge-songforge/blob/9c7ff3af40be67b676102d3a30ade037021ec1e4/audits/chat-d/PF_M043_CHAT_D_FROZEN_LYRIC_AUDIT_2026-11-01.md) | 35 unit + 25 HTTP/restart + 15 custom assertions PASS bounded |
| D | [Machine-readable receipt](https://github.com/justinbusiness461-lab/pulseforge-songforge/blob/9c7ff3af40be67b676102d3a30ade037021ec1e4/audits/chat-d/PF_M043_CHAT_D_FROZEN_LYRIC_EVIDENCE_2026-11-01.json) | Exact freeze/release/fixture binding |
| Runnable R-010 | [Clean reproduction](https://github.com/justinbusiness461-lab/pulseforge-songforge/blob/b9e9b851bd57bc0792fea7ac0505d6cb4f40c30a/docs/audits/PF_MISSION_043_REPRODUCIBLE.md) | 35 unit + 25 HTTP/restart PASS; clean clone, Linux/Python 3.12 |

C receipt blob: `a6afc26631540a7be81fc11cf2622825df18d923`.
C measurement blob: `4c05a2c0f211b28dc37a56ce0d1916c083eb1597`.
C recovery blob: `04e7f1a3af5df936663fa89c9a0a9c603c1883a7`.
D report blob: `e3845ead77c31a8b2567b656ef3cea26a801487c`.
D JSON blob: `b79eafa98e747688d6ccd6bab0a5b1f88fdf6bcd`.
Runnable receipt blob: `4eb517dc5382e06438a4e57547ea68c5794c90e0`.

## Consolidated disposition

`LYRIC_INTELLIGENCE_PASS = PASS — BOUNDED`

The required clean-reproducibility receipt is present and authenticated. This disposition consolidates the independent owners' recorded results; B did not rerun C/D/Runnable campaigns during evidence integration.

Earned scope: supplied-text guided alignment; sample-bound occurrences; immutable R1/R2 correction lineage; ProjectRevision selection; source/timing preservation on text-only correction; fresh-process recovery; stale rejection; no-transcript instrumental unknown state; bounded synthetic signal-placement accuracy.

Limits:
- C's 10 ms tolerance is declared for its receipt, not a universal product standard. Construction placement is not human phoneme annotation.
- Instrumental unknown without supplied words is not general vocal detection.
- Corrected truth is conserved by tested unit/HTTP boundaries. D did not execute the full competing-R3 promotion race or end-to-end repeated chorus; no broad race or multi-occurrence certification.
- Full ASR rerun API: NOT_APPLICABLE_TO_CURRENT_GUIDED_ALIGNER.
- Runnable describes Linux/Python 3.12 and a fresh clone, but does not retain an exact environment image digest or separate raw run logs in that receipt. Do not imply bit-for-bit environment reproduction.
- No general ASR, singing recognition, duets, multilingual recognition, phoneme-grade alignment, browser/PWA product journey, finished master, or completed musician product.
- Cinema is unchanged by this evidence-only integration; no cinema recertification or rerender.

M043 bounded evidence closeout is complete. Mission 044 implementation/promotion remains subject to Team Lead scope and the normal A/Cody → B → C/D ownership boundaries.

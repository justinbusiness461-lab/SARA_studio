# Chat D — M044 R2 historical-playback provenance contract v2
Date: 2026-11-05. Status: HARDENING_ADVANCE. This is NOT runtime or musical certification.

## Fresh GitHub readback
- PR #10 current head: `9f200d5e3b45494cca4f46728cc9e3e8a64766fc`, OPEN/DRAFT, not merged.
- Current main: `a53cac6a0c81ed3d5285e4e0c02346784a6bf643` (B evidence commit).
- B independent receipt: `docs/audits/PF_MISSION_044_R2_QUALIFICATION.md`: 46/46 Python, 8/8 Node, 19/19 integration PASS on the PR #10 candidate; invalid WAV and crash recovery bounded PASS.
- PR #11 remains stacked on earlier PR #10 base `220010f44...`.
- No C merged-main physical audio or actual product playback evidence was established in this pass.

## Material improvement
Previous Chat D checker accepted a plain `audioValidation: PASS` and compared only the selected revision, not the actual playback bytes/artifact identifier. It could miss playback of the wrong, valid WAV.

The v2 independent *observation-contract checker* requires:
1. playback artifact ID == selected history artifact ID;
2. decoded PCM SHA-256 == selected history WAV decoded PCM SHA-256;
3. a historical artifact is playable only if its validation state is PASS, its digest is well-formed, and its source revision matches its historical revision;
4. pending, unavailable or failed audio cannot be labeled playable;
5. exactly one visible current badge and no duplicate displayed revision;
6. current revision stays R2 throughout captured late-render history observations;
7. playback may start only from the verified selected historical item.

## Prepared local executable
`M044_ChatD_History_Provenance_v2_2026-11-05.zip` includes checker, 14 unit tests, and observer instructions.
Local checker suite: **14/14 PASS** (synthetic contract vectors only; NOT product execution).

SHA-256 identities:
- README: `2090f71ed8358143474fc59316ae2fa6906f944c4820eec4161f322e8f38670c`
- checker: `bb48cb947e09cdcd1a3cbd52548859a2b1f42963c82abe17d50f13948ae672e6`
- tests: `f812f7b0be42cd962b14d82a84ef7f194363a819031d28b48b764acb858aed0a`

## Real product attack after merge + Work C
D44-01 valid late R1; D44-02 malformed late R1; D44-03 unavailable R1; D44-04 pending R2; D44-05 cache-free restart; D44-06 rapid A/B; D44-07 stale UI; D44-08 failed decoder; D44-09 crash-before-bind recovery.
Collector must independently decode WAV bytes and record real UI/API observations; labeling a synthetic JSON record "real" is insufficient proof. An observation checker alone cannot establish these facts.

## Findings
- **P1 — Checker false-negative risk (mitigated locally):** prior contract did not tie actual playback artifact and decoded PCM to selected history. Owner: Chat D. Impact: wrong-but-valid audio could be considered correct. Action: execute v2 with independent collected observations.
- **P1 — Runtime evidence pending:** PR #10 unmerged, C mainline audio pending, actual history playback UI unqualified. Owner: B/C/Cody. Impact: product certification cannot advance. Wake: B exact M044_MAIN_SHA + C physical receipt + UI implementation.

## JUSTIN 101
WHAT CHANGED: Added v2 observable playback-provenance negative contract and executed 14 synthetic unit tests.
WHAT FAILED/BLOCKED: Actual browser/backend observations not available; mainline/C gates open.
WHAT IS PROVEN: Checker contract vectors, B receipt exists; neither proves product UX.
WHAT IS NOT PROVEN: UI playback, wrong-audio prevention in deployed product, musical quality.
WHAT JUSTIN MUST DO: Nothing.

# Chat D — M044 Historical Audio Product Attack (2026-11-05)

Mode: evidence-only handoff; **not** product certification or repair code.

Current source readback: main `2c17603bf1fe58059bf236b21543cd670556247a`; PR #10 draft/open at `5403e50fb9399795e1ae52c57100c17d2f0dab9e`; PR #11 open at `cb80d4fe06cc1148651787872ad89216c20328f3`. Team Lead reports B's malformed-WAV historical admission defect and Cody's crash-before-binding recovery defect; no merge authorized.

## Product negative matrix — run after B merged main + C physical result + real Studio UI

| Case | Trigger | Required behavior |
|---|---|---|
| D44-01 | R1 valid render arrives after R2 becomes current | R1 playable via R1 history; R2 current audio unchanged |
| D44-02 | R1 historical file is malformed WAV | Historical Play disabled, visible error, no false success |
| D44-03 | R1 artifact unavailable | Disabled Play, no silent R2 fallback |
| D44-04 | R2 still rendering while history opens | Separate truthful R1/R2 states, no fake playable result |
| D44-05 | Process restart; browser cache absent | ProjectRevision and artifact history survive from durable server |
| D44-06 | Rapid R1↔R2 A/B | Selected audible digest/revision always agrees with provenance |
| D44-07 | Stale browser tab | Stale edits reject/reconcile; R1 never badged current |
| D44-08 | Historical WAV decoder fails at Play | Playback never begins; error displayed; R2 survives |
| D44-09 | Crash-before-R1 historical bind, recover | Exactly one R1 history item; no phantom revision; R2 current |

## Prepared executable checker

Local bundle: `M044_ChatD_History_Product_Adversary_2026-11-05.zip` contains `README.md`, `m044_history_checker.py`, `test_m044_history_checker.py`.
The snapshot-observation checker validates: exactly R1/R2 history, correct current badge, audio validation before Play, selected-to-played revision agreement, and false-success prevention.

**Locally executed checker unit suite: 12/12 PASS.** These tests exercise only **synthetic observation contract vectors**, not the application. Source files SHA256:
- README `c0175d7b37dceb92f9aea469a7aecbae86c6f1d8bd32412567b7bc3b39a93e5f`
- checker `86db73e8a7905716a3f1b64ab7b5f32972e8de339361ef5b0f27bd6b2121a4db`
- tests `5e4ca29ce844855f9c52a17c7c40955c02cb65807aae797d0f9a464274dccc20`

A PASS from the checker is admissible for product review ONLY when supplied observations are genuinely collected from the real browser and durable backend and the audioValidation field was determined by independent actual decoding/digest verification. It cannot replace Work B/C proofs.

## Audit findings

- P0: malformed historical WAV admission. Evidence: latest Team Lead relaying Work B's independent failure; impact history may present garbage as audio. Owner Bobby. Next: exact admission repair; B independently tests.
- P1: crash-before-historical-binding recovery. Evidence: latest Team Lead relaying Cody review; impact valid artifacts stranded absent caller replay. Owner Bobby. Next: deterministic durable attempt reconciliation; B/Manus qualify.
- P1: potential misleading history/transport. Evidence: risk derived from same product edge, not a reproduced browser defect. Owner Pixel/Cody; Chat D independently certifies after merge. Next: execute D44-01..09 with actual product.
- BLOCKED: no merged repaired M044 main/C audio/complete UI demonstrated in this refresh. Wake on exact B `M044_MAIN_SHA` + C physical receipt + real UI.

## JUSTIN 101
WHAT CHANGED: Built local executable observational check and retained nine-case product attack contract.
WHAT FAILED/BLOCKED: Product-runtime validation gated on B/C and working UI.
WHAT IS PROVEN: 12 local checker contract tests, not Sound Forge behavior.
WHAT IS NOT PROVEN: malformed WAV fixed, crash reconciliation fixed, full UX/audio quality.
WHAT JUSTIN MUST DO: Nothing.

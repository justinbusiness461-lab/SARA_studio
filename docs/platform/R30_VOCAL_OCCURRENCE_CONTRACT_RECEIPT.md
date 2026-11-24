# Engineer #1 — R30 Studio VocalOccurrence Candidate Contract

**Status:** SOURCE + FOCUSED TESTED. No Studio server/API integration, no acoustic certification, no approval, no main merge.
**Rightful owner:** SARA_studio (repo ID 1427534706). **Parent reviewed:** PR #37 `d876cad4d55aadee144e7bf6756c224b41a8c117`, stacked on PR #36 `862a7ed11f12835b92c4f0b5673241ae4362b8c2`; main `d6aa889a0def72bb8e1c87009a98d6c29e47067e`.

## Why this is owner-correct

`tools/lyric_timeline.py` already owns immutable sample-bound lyric evidence attached through Studio ProjectRevision. Its known-text energy-island method **is not speech recognition, vocal isolation, acoustic onset proof, or full-song alignment**. This PR adds a bounded, pure **non-authoritative** projection of Studio word IDs into proposed vocal occurrences; it neither creates a shadow `LyricTimelineRevision` nor writes musical history. Only an already authorized `project_operation(open)` result may be supplied to this pure helper; it is **not** a public authorization endpoint.

Every proposed occurrence binds: `ProjectRevision`, `LyricTimelineRevision`, `sourceArtifactId`, `sourceAudioDigest`, source sample rate and Studio `wordId`. Repeated words with the same text remain distinct by ID. The proposal cannot supply trust, confidence, alternative musical clock, or commercial/creative approval flags. Consumer-usable output is always `VOCAL_ONSET_UNVERIFIED`. `require_verified_vocal_onsets` always denies until Studio implements its **own** trusted evidence lookup + issuer verification; arbitrary booleans cannot promote truth. Historical revision use stays possible when the lawful exact Studio revision was selected.

## TDD & physical source receipt

- RED (module absent): `PYTHONPATH=<src>/tools python -m unittest discover -s <src>/tests -v` failed with `ModuleNotFoundError` (expected initial RED; not a product bug).
- Intermediate candidate: **12 passing, 1 fixture error**; corrected the invalid test end-sample fixture after the test revealed its inconsistency. No test disabled.
- GREEN: **13/13 Python unittest PASS**, `python -m compileall -q` PASS on the standalone exact two-file candidate in a local Python 3.13.5 environment. This does **not** certify the complete PR #37 source tree or browser test.
- Exact local UTF-8 source SHA-256: `df8498dbeb3a7da3b0a018e23e227cfeedeb64932811d5a4a805e5cd56222cd4`.
- Exact local UTF-8 test SHA-256: `0aca4fcaae35f5781fe7d663cc05961e86a5dfe784aa4f3025f701dd6fbcbc93`.
- **GitHub independent blob identity:** source Git blob `bd2ad5cf64ea3f8ef9335da5f339c4509c6639a4`; test Git blob `202a25237b42e20ca00b2355c7ae85f13377a9c7`. Both match local `git hash-object`.

## Exact blocking boundary for broader R30

1. **P0 musician playback:** positive `SARA_R25_REAL_MEDIA_STRICT=1` three-song Chromium / 390+1440 / R1↔R2 ≤50ms and cold restart are **NOT EXECUTED HERE**; no synthetic substitution.
2. **P0 vocal truth:** this projection cannot claim singing word onsets. Independent annotated acoustic `VocalOccurrence` evidence, repeated-occurrence ID reconciliation, accepted sourceProjectRevisionId + sourceArtifactId, actor authorization, and a Studio-trusted verification issuer are still required. User-supplied annotations or an FFT band score are not attestation.
3. **P0 chain qualification:** complete exact-head Python, Node, Chromium, rights/scope and two-principal permission gates unexecuted in this round; PR #36→#37→main must not be promoted on this receipt.
4. **P0 continuity:** existing Drive `ENGINEER_1_SARA/CURRENT/` and immutable `ROUNDS/R28/` remain prior checkpoint; R30 `CURRENT` **not updated/verified** by this PR. Treat `CONTINUITY_DELTA=INCOMPLETE` until 9/9 readback and immutable round archive.
5. **Safety:** zero external spend. No live HMAC or Drive ID, music master, personal data, or private rights material committed.

## JUSTIN 101

WHAT CHANGED: two owner-correct code/test files that reject forged vocal timing authority and preserve repeated-word identities.
FAILED: Real-song/Studio integrated vocal occurrence certification and strict three-song browser execution are outside this local candidate.
PROVEN: 13/13 focused tests, syntax compilation and byte-identical GitHub blobs.
UNPROVEN: full suite, audio listening, true onset timing, production Studio integration, commercial/creative approval, and release.
TEAM NEXT: qualified Studio host completes R30 real-media and exact-head suites; lyric issuer owner adds trusted acoustic evidence without shadow authority; QA retries this new module in full tree; archive Drive `CURRENT`.
JUSTIN ACTION: None for this candidate.

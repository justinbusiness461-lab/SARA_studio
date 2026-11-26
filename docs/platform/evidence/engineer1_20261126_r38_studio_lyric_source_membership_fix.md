# S.A.R.A. Studio Engineer #1 — R38 lawful lyric-source read repair

**Scope:** `SARA_studio` PR #44 only. **Disposition:** SOURCE + FOCUSED TESTED; FULL EXACT-HEAD AND LIVE ISSUER UNVERIFIED. No merge, no key issuance, no audio approval.

## Root cause independently traced to exact project source

`tools/studio_server.py` in Studio PR #44, 
`project_operation(commit=True, lyric=True, action='candidate')` lines ~1228-1251 registers a new lyric-source WAV in the revision's `sourceAssetDigests` and does **not** necessarily add it to `outputArtifactIds`. In contrast, `project_audio_bytes()` lines ~976-997 authorizes `outputArtifactIds` and historical render associations; it is not a general source-asset read method.

The R36 helper required the lyric WAV in BOTH source and output arrays, then passed this legitimate source to `project_audio_bytes()`. An authorized current/historical Studio lyric revision whose WAV is only a source would fail `ARTIFACT_NOT_IN_REVISION` or `artifact is not lawfully bound to requested revision`. A fabricated output binding must never be introduced to silence this error.

## Minimum owner-correct repair

- Keep the existing principal-authorized `project_operation(root, {'projectId': ..., 'revisionId': ...})` first, with explicit historical/current ancestry authentication.
- Require original master and lyric-source WAV in the **authorized selected revision's** `sourceAssetDigests`, and require `snapshot.lyricTimeline.sourceArtifactId == decoded_id`.
- Only then read both digest-addressed immutable source objects with existing `studio_server.artifact_bytes(root, digest)`; this checks physical digest integrity. Never scan CAS or accept digest/path alone as authorization.
- Keep source PCM identity, Studio lyric timeline rate/channels/frames and signed witness/principal/grant checks unchanged. Do not create a second media authority or a new public route. No change to M043's bounded 60-second candidate method.

## RED / GREEN

- RED: 21 focused tests with 2 errors (`ARTIFACT_NOT_IN_REVISION`) on the unmodified R36 code. New tests assert an authorized lyric-only source is admitted and that the output-render reader is *never invoked*.
- GREEN: 21/21 focused Python tests pass, 0 failures, 0 skips. Older test treating output absence as failure was corrected to assert actual original-source membership. No test disabled.
- Reproduction: `PYTHONPATH=tools python -m unittest discover -s tests -p 'test_m045_v3_signed_occurrence.py' -v` in the exact two-file test snapshot.
- Independent FFmpeg physical readback on uploaded `Denial & Error.mp3` (original SHA-256 `aad232ff0b9e5672e59db1cf29f229b1c3f10492dfc2f6d366518ba2af281dec`): 48 kHz, stereo, interleaved PCM16LE, 10,154,880 frames/211.56s/40,619,520 bytes, PCM SHA-256 `9ddb2468d5aa4b367852c9e6efbc18098e507284cbadb40f23a7eacb64232f42`. Reconstructed decoded full-source 60–94 s window SHA `6279d4603ff390f58d567feff668454163e6c63e4bba12225be3dbe25e9a1668`. This is private physical signal identity, **not** accepted Studio CAS association or independent observed vocal onset.

## Active holds

1. Studio owner must durably accept the complete master/WAV and bind source ProjectRevision, LyricTimelineRevision and lawful CAS membership; none is fabricated here.
2. Current M043 60s lyric candidate cannot create a 211.56s full-song lyric timeline; owner-specific full-song ingestion path remains missing.
3. Independent DENIAL_01 performed-word onset witness, production Ed25519 keys/grant registry, full exact-head Python/Node/Chromium, and real PulseForge final-container proof are **NOT RUN / NOT VERIFIED**.
4. PulseForge PR #100 consumer remains E2 reference only; no downstream authority, production render, approval, deployment or merge.

**Security law:** `principal -> authorized project -> selected revision ancestry -> sourceAssetDigests membership -> lyric timeline association -> CAS immutable read -> independent digests -> witness verification`. No CAS ownership inference from mere existence.

**TEAM NEXT:** Verify exact PR #44 current Git blobs, independent full repo source suite and later real authorized Studio host state; preserve PR #36 / #37 stacking and separate cinema PR #100. **JUSTIN ACTION:** None for this source repair.

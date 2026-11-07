# M044 — S.A.R.A. Studio Non-Destructive Precision Edit Consumer Contract
Date: 2026-11-07 | State: **DESIGN CANDIDATE ONLY / UNVERIFIED IN RUNTIME**
Canonical product: `justinbusiness461-lab/pulseforge-songforge`
Base inspected: `main@14e2fb9cc55c8ce2909803a66d509915a18eb625`; M044 PR #10 merged; #11 unmerged/retarget needed; #13 draft Forge consumer contract. Floot listing does not establish an operational Sound Forge app.

This is a **scoped proposed consumer extension** to PR #13's `docs/product/SARA_STUDIO_FORGE_CONSUMPTION_M044.md`, not a competing registry, new runtime, separate renderer, or alternative source of authority.

## Product law
**PRESERVE → SELECT → PROPOSE → RENDER CANDIDATE → VERIFY → AUDITION → APPROVE → COMMIT.**
Creator use case: keep the original `Four Corners, No Brakes` and its 108 BPM backing groove unchanged, replacing only the rushed Scene Two male rap with a slower/half-time-delivered take. Do not conflate slowing *vocal phrasing* with reducing song tempo. Source and previous accepted takes must remain recoverable after retries, crashes, and cross-session reopen.

## Owner law / extension map
- `SongSpec` and `MusicIntent`: existing `app-core.js` / `tools/scorecore.cjs`. Extend section/track intent, not a duplicate composer.
- `ProjectRevision`, source/current/candidate state, CAS and immutable artifacts: existing `studio_server.py`. Browser local state is only an address.
- `ProductionTimeline`: reuse authoritative sample and beat boundaries; no guessed timing certified as exact.
- M043 LyricTimeline: existing guided provided-text alignment; **NOT** general ASR or natural singing recognition.
- Audio and recovery: existing content-addressed strict PCM/WAV admission, durable jobs, source digest and late-render binding rules.
- Audio QA: Work C physical measurement/locality harness, plus independent listening when musical quality is claimed.
- Work A UI: waveform editor, transport, revision comparison and explicit approval. No authoritative Manus demo oscillator.
- Canonical DJ RezrXtion competition/donor Forge: source, license and donor trace only; no shadow source-rights database.
- Cinema stays in existing PulseForge/Cinema owner. No auto-cinema timeline mutation.

## Product surfaces to extend
1. **Version Vault** — freeze original audio, version history and branch/candidate ancestry with source/render/model identity, digests and restore.
2. **Waveform/Section Editor** — linked lyric line, musical section, source-sample spans, beat/grid and editable track scope; mark exact vs estimated alignment.
3. **Replace Section** — immutable candidate for a selected span and allowed domains (vocal phrasing, lyrics, instrument or FX); never writes current directly.
4. **Remaster** — non-destructive mastering-only candidate versus generative remix clearly classified; level-matched A/B, peaks/LUFS/stereo metrics.
5. **Remix / Cover / Extend** — different operation types with rights, prompt, renderer/model provenance and version lineage, not implicit overwrites.
6. **Phrasing controls** — original tempo maintained while user asks for slower unhurried delivery. Exact natural-vocal preservation is not yet qualified.
7. **DJ / Weird Sound** — self-recorded Foley import, audio preview, chop/loop/onset alignment, beat-locked scratch/fader events, rights and provenance.
8. **Compare / Approve / Undo** — aligned A/B audition, explicit accept, atomic expected-revision CAS, easily recoverable original.
9. **Mobile client** — inspect, select, propose, preview and approve; server remains durable audio authority.
10. **Guided assistant** — translates “slow Scene Two, preserve rest” into a proposed scoped edit, never silent mutation.

## Data contract (PROPOSED — NOT CURRENT SERVER ENDPOINT)
```json
{
  "operation": "proposeSectionReplacement",
  "projectId": "<project>",
  "expectedCurrentRevisionId": "<current>",
  "sourceRevisionId": "<source>",
  "sourceAudioArtifactId": "<hash>",
  "selection": {
    "sectionId": "<canonical>",
    "trackIds": ["<canonical>"],
    "startSampleInclusive": 0,
    "endSampleExclusive": 1,
    "timebaseDigest": "<hash>"
  },
  "change": {
    "instruction": "Slow Scene Two rap; no double-time; original 108 BPM instrumental stays",
    "allowedDomains": ["vocalPhrasing"],
    "lockedDomains": ["tempo", "sectionOrder", "otherSections"]
  },
  "idempotencyKey": "<operation ID>",
  "sourceRightsState": "<admission>"
}
```
Output: immutable candidate revision, source/parent IDs, exact audio container and decoded PCM digests, render/tool identity, actual sample-rate/frame count, scope, QA receipts and provenance. Candidate becomes current **only** after explicit CAS approval. Reject ambiguous or out-of-range spans, unsupported formats, bad source rights, cross-tenant references and orphan artifacts.

## Gates (not yet implemented by this document)
- **G0** source/readback: preserve original, strict media admission, PR #11 owner reconciliation, full current M044 R2 evidence.
- **G1** revision history: selected/current/candidate visible, durable source and CAS candidate approval.
- **G2** deterministic PCM splice: exact outside-envelope sample equality *if claiming exact preservation*, explicit boundary fades and length contracts, A/B sample alignment.
- **G3** mastering/remix: disjoint semantics, source identity and measurable QA, non-destructive mastering, model/provider trace.
- **G4** natural-vocal, stems, Foley and mobile: truth-labeled capability gates and independent audio-device qualification.

## Required independently executed negative/positive tests
1. Source audio unchanged after proposal, failed render, cancel and accepted candidate.
2. Original, R1, R2, rejected candidate all retrievable after cold restart.
3. Nonselected audio samples identical if an exact splice/locality claim is made.
4. Instrumental remains 108 BPM while vocal phrasing changes; no inadvertent timebase mutation.
5. Concurrent approvals with same expectedCurrentRevisionId: exactly one current successor.
6. Late historical R1 render cannot overwrite current R2.
7. Malformed RIFF/WAV, wrong encoding/channels/rate, truncation, digest mismatch rejected.
8. Crash after durable output before binding recovers on ordinary reopen, without caller replay.
9. A/B switching at same playhead and loudness; no auto-accept.
10. Tenant A cannot read/write/list/download tenant B project or artifacts.
11. Unknown or unlicensed source rights fail closed for release.
12. Save/reopen after scoped edit preserves non-target SongSpec/ProductionTimeline nodes.
13. Mobile UI offers honest preview/current/candidate status and server-only authority.
14. Vocal identity/stems/natural singing are never claimed on unqualified guide audio.
15. Musical QA rubric: >=7/10 overall, no category <5, stereo/dynamics/variation/emotional usefulness >=6, measured with actual listening.

## Findings
| Severity | Finding / evidence | Owner | Impact | Blocker | Next lawful action |
|---|---|---|---|---|---|
| P0 | Full section-replace UI not established by main/PR #11 | Work A / ScoreCore | whole-song regeneration risks originals | missing full UI→audio edit proof | Build G1–G2 on existing owners |
| P0 | Historical/candidate authority must be kept separate | ProjectRevision owner | wrong current take or data loss | no consumer candidate approval gate | CAS+reopen+late-render tests |
| P1 | M043 only guided synthetic speech, not singing ASR | Lyric owner / Work C | false word/timing accuracy | natural vocal evidence | mark unknown and independently qualify |
| P0 | Manus donor previously had auth/audio proxy concerns per PR #12/#13 | Manus / Work A | cross-tenant or fake A/B | independent tenant and real audio trace | deny integration absent negative proofs |
| P1 | Sample and upload licenses not certified for new flows | Sample Creator owner | publishing risk | rights admission | provenance gate |
| P1 | Floot account currently lists Visualizer, not verified Studio editor | deployment owner | mistaken runtime readiness | actual Studio readback | verify deployed device/browser |

**Scope:** repository documentation-only. No source mutation, endpoint, waveform tool, renderer, external provider, deployment, or release certification. SOURCE ≠ RUNTIME. BUILD ≠ FEATURE PROOF. PROMPT ≠ AUDIO PROOF.

## JUSTIN 101
WHAT CHANGED: candidate precision-editor architecture, ownership, controls, workflow, QA and acceptance criteria.
WHAT FAILED/BLOCKED: no shipped full replace-section/remaster/compare/audio playback certification.
WHAT IS PROVEN: live GitHub main and PR inspection; this document exists as a proposed repo-backed contract.
WHAT IS NOT PROVEN: implementation, audio preservation on real songs, tenancy, cross-session UI, music quality or publishing rights.
WHAT JUSTIN MUST DO: none to draft the contract; rightful engineers must implement and independently certify before merge/release.

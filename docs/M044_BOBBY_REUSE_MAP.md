# M044 — BOBBY ScoreCore preparation

Date: 2026-11-01. Implementation candidate, not a release or certification.
Base: pulseforge-songforge c4f681878134f76b429788f58ccf2686198045da.
M043 freeze remains 076aed8d438a938119a7c2d5b34bb5eeb3ba4409, release 2.20.0.

## Source refresh

Read current repository tree, main identity, open PRs, README, package.json,
app-core.js, app-ui.js, tools/studio_server.py, tools/m040_music_probe.cjs,
M043 certification index and reproducibility receipt. No AGENTS.md or named
governance/current-state/work-log files were present in this repository tree.
Related dj_rezrxtion repository metadata refreshed; its full governance and cinema
source were not re-audited. Supplied Sound Forge 6 context searched for owner/repo
identity; historical dj_rezrxtion ZIP inventory inspected (659a1ffc..., Oct 18).
Floot project listing confirms the PulseForge Visualizer; hosted code/runtime
not refreshed or modified. Superpowers package unavailable after attempted read.
Git workflow skill read and applied. No Actions runs or paid provider calls made.

Current main's Work B index already records LYRIC_INTELLIGENCE_PASS = PASS — BOUNDED
and R-010 35 unit + 25 HTTP/restart checks. This is authenticated repository receipt
reporting, not BOBBY independently executing or promoting M043. Index explicitly
limits environment reproducibility: no exact image digest/separate raw logs.

## CODY_M044_REUSE_MAP

| Concern | Disposition | Existing owner / exact limit |
|---|---|---|
| SongSpec | REUSE | app-core.js parsePrompt returns the existing skeleton.v2.8 representation; no second song schema |
| Prompt constraints | EXTEND | tools/scorecore.cjs adds a bounded typed admission adapter; delegates generation to parsePrompt |
| ProductionTimeline | REUSE | studio_server.py project_operation derives it from SongSpec and binds its digest |
| Section graph | EXTEND | structure.sections has IDs and tick intervals; currently ordered sections, not a generalized branching graph |
| Tempo | REUSE | timebase.initial_bpm, parser 60–180 BPM, TPQ 960 |
| Meter | EXTEND LATER | stored string is 4/4; generation hardcodes four quarter notes per bar; adapter rejects other meters |
| Key | REUSE bounded | six supported key tables; adapter rejects unsupported explicit key requests |
| Chords | EXTEND LATER | hardcoded degree progression; no explicit editable chord-plan authority found |
| Motifs | EXTEND LATER | repeated note arrays exist; no persistent motif identity/variation constraint found |
| Track events | REUSE | tracks[].events with NOTE_ON, tick, note_number, velocity, duration_ticks |
| Instruments | REUSE / EXTEND LATER | DRUMS/BASS/PAD/LEAD/STRINGS/VOCAL type dispatch; not a qualified real-instrument sample library |
| Lyrics | REUSE, FROZEN | composition section text distinct from observed LyricTimeline; no changes here |
| Rendering | EXTEND LATER | existing renderMixBuffer and WAV serializer; offline renderer ignores pan and bypasses live spatial/filter chain |
| Revisions | REUSE | ProjectManifest selects immutable ProjectRevision; expectedCurrentRevisionId fence |
| Artifacts | REUSE | content digests, persisted bytes, outputBindings, reread before pointer advancement |
| Scheduler | DO NOT CREATE | first slice is synchronous candidate computation, existing server handles persistence |

## FIRST_IMPLEMENTABLE_SLICE

Added isolated CommonJS candidate adapter, not loaded by the app or release packager:
prompt -> MusicIntent -> existing parsePrompt -> existing SongSpec -> immutable
section/track transposition. Default tempo/key/meter/seed are explicit adapter
policy (102, F# minor, 4/4, 0), not inferred artistic truth. Prompt interpretation
is limited lexical admission, not general musical cognition. Only existing key
names and 4/4 are supported. Other requested production concepts remain uncompiled.

Edit boundary: NOTE_ON notes fully contained in [start_tick,end_tick); crossing
notes reject pending split/tie policy. DRUMS/VOCAL transposition is excluded.
Input remains unchanged; unchanged fields/events survive byte-equivalent JSON
structure. Adapter grants no persistence, render, lyric or certification authority.

The next integration slice must route this through existing project commit/open
and existing renderMixBuffer, not new revision or timeline storage. Work B owns
integration. This branch deliberately adds no script tag, UI wiring, package
script or release bump. No existing product file is changed.

## TEST_PLAN

Executed RED: node --test tests/scorecore.test.cjs failed MODULE_NOT_FOUND before
implementation. Executed GREEN: same command, 6/6 passing on Node v24.22.1.
Tests execute the exact base app-core parser in a VM, not a replacement compiler.
Coverage: intent constraints/seed; explicit unsupported/conflicting constraints;
immutable bass-only octave edit; invalid/ambiguous target; MIDI range; half-open
section end; crossing-note rejection. These are local symbolic tests only.

Remaining required integration proof:
1. Generate original instrumental SongSpec and render through existing renderer.
2. Persist R1 and its exact audio via existing artifact/project APIs.
3. Transpose bass in one named section, render R2 and commit with expected R1.
4. Compare every unrelated symbolic field and event; measure changed PCM frames
   against edit interval plus explicitly measured instrument/effect release tail.
5. Terminate server, restart on same export root, reopen by project ID, verify
   exact R2 spec/timeline/output digests, retained R1, and stale-R1 rejection.
6. Address offline stereo/pan separately with an intentional new RED test before
   DSP changes. Two channel count alone cannot establish stereo interest.
7. Submit actual song to C measurement and D listening gates; no quality score
   follows from these unit tests.

Full generate/edit/render/kill/reopen proof NOT RUN in this slice. The declared
web-audio-engine dependency is absent locally. No audio/listening certification.
No baseline Python test campaign rerun; M043 evidence remains attributed to owners.

## FILES_EXPECTED_TO_CHANGE

This branch only adds tools/scorecore.cjs, tests/scorecore.test.cjs and this map.
Follow-on requires coordinated app-core.js/app-ui.js integration, new M044
render/recovery probe and packaging inclusion; shared files must be assigned by B
against A's current cone before editing. studio_server.py and lyric source need
no change for this symbolic slice. Existing M043 files remain byte-identical.

## BOB_MECHANISMS_REUSED

Inspected build-pro-assist main 1af51ea3fbdf2ffdbcc49e5ba8a7f7b3b9d97d55:
server/laboratory-runtime/hands/durable-semantic-workgraph-persistence.ts and its
test. Source delegates atomic admission to canonical RPC, preserves operation
identity/generation and classifies conflict versus uncertain transaction outcome;
ambiguous effects require authoritative reread before retry. Tests assert those
contracts with mocks; BOB production execution was NOT verified here.

Disposition: reuse engineering rules through Sound Forge's already present
expectedCurrentRevisionId, immutable content addressing, atomic durable write and
readback. No BOB code transplanted. No BOB runtime claim or imported authority.

## BOB_MECHANISMS_REJECTED

- Supabase WorkGraph RPC/SQL and BOB actor/repository authority: unnecessary coupling.
- New durable job scheduler: no durable asynchronous job requirement in this slice.
- Second content-address store or hash vocabulary: existing artifact owner suffices.
- Generic provider/tool fabric, confidence certification and distributed coordination:
  outside the music edit obligation; add no proof of musical usefulness.
- Citizen DJ legacy cache/runtime: not inspected or imported in this preparation.

## JUSTIN 101

WHAT CHANGED: isolated executable intent/edit candidate and six tests; reuse map.
WHAT FAILED/BLOCKED: Superpowers loading unavailable; local audio dependency absent.
WHAT IS PROVEN: six local symbolic checks against the existing parser.
WHAT IS NOT PROVEN: app integration, actual audio edit locality, durable reopen of
this new adapter, browser workflow, general prompt fidelity or >=7/10 song quality.
WHAT JUSTIN MUST DO: nothing; B reviews this candidate and coordinates integration.

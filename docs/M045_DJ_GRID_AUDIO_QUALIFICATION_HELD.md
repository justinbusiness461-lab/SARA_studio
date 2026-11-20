# Scratch Surgeon — source-backed sample-accurate audio qualification HOLD

Source: SARA_studio M045 native DJ grid, ScoreCore, ProductionTimeline and
Studio ProjectRevision authority.
Status: SYMBOLIC P0 EVENT EDITING QUALIFIED; PHYSICAL DJ AUDIO UNVERIFIED.

Implemented:
- Native ScoreCore two-deck scratch markers with technique values baby,
  chirp, 2_click_flare, two_deck_juggle.
- 16-step 1/8-note grid in current section; independent A/B deck event IDs.
- Rational 44,100 Hz frame/sample positioning based on canonical BPM and tick.
- Exact non-target SongSpec event identity preserved by immutable editing.
- Studio server rejects forged event IDs, sample positions, unsupported
  techniques and direct writes that modify a locked track/section.
- UI draft -> authoritative project save -> cold browser reopen.

NOT IMPLEMENTED / NO CLAIM:
- No source SampleAsset has been bound to these markers.
- Marker "sample_index" is a scheduled timing position, not proof that
  a physically decoded scratch sound was rendered.
- No original scratch gesture audio, two-deck transport model, scratch
  envelope, pitch/speed curve, sample interpolation, limiter or physical
  44.1-kHz PCM16 master is certified.
- Unchanged audio outside a scratch region is not proven by symbolic P0
  event invariance alone.
- Neither Star Light dry stem reconstitution nor any production-master
  bit-for-bit SHA equivalence was reproduced in this slice.

OWNER / WAKE:
SARA_studio SampleAsset, SongSpec, ProductionTimeline, ProjectRevision and
RenderArtifact authorities must qualify a lawful sample source and exact
scratch operation before rendering. Publish staging + durable artifact
identity + authorized revision association; then measure sample placement
and verify playback. Do not borrow cassette/turntable IP or GPL donor code
without separate provenance and license qualification.

The prior Sample Lab owner gap and exact reconstruction contract remain
in docs/M045_SAMPLE_LAB_STEM_EXPORT_HELD.md.


## Local DSP/publication qualification annex — 2026-11-19

New source: tools/m045_scratch_dsp.py and the canonical Studio
render_authorized_scratch_operation() / POST /api/m045/scratch/render.

VERIFIED LOCALLY: Synthetic project-attached 44.1 kHz stereo PCM16 audio
drives bounded dual-deck float64 scratch DSP with deterministic forward and
reverse fractional interpolation, technique-specific crossfader breakpoints,
and 2 ms cosine edge fades (short windows clamp the fade). PCM outside the
event-window union remains byte-identical. Two decks sum before one PCM16
quantizer. The pre-existing render_publish_operation() durably publishes
the resulting WAV to canonical CAS, and independent authorized
project_audio_bytes() physically decodes/readbacks the published master.
Foreign/unbound source digests and unauthorized project principals fail closed.

STILL HELD: This source revision attachment does not independently establish
first-class SampleAsset source/decoded/transform/rights provenance. No real
turntable sample, physical DJ audition, artist creative approval, or complete
rights qualification was provided. A local synthetic renderer proof cannot
certify production SampleAsset governance. The initial marker edit identity
proof remains P0 symbolic, not a blanket exact audio-isolation claim.

WAKE: verify authorized source and rights provenance in the rightful
SampleAsset owner, then audition real scratch content and certify output.


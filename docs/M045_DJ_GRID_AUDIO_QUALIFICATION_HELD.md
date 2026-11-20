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

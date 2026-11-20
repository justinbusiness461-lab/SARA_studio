# Sample Lab stem export — source qualification HOLD

This is an owner-scoped engineering contract, NOT a completed stem-export repair,
physical audio result, or approval.

Source reviewed: canonical SARA_studio feature branch, app-ui.js
renderMixBuffer(), tools/m044-session.cjs render(), tools/studio_server.py
revision/CAS authority, and scorecore.js editing adapter.

VERIFIED CURRENT SOURCE: The existing renderer sums tracks into one
OfflineAudioContext master at 44.1 kHz. It does not implement a Sample Lab
per-track dry reconstruction exporter, tanh master bus, persisted mix_recipe,
or the Star Light source fixture. A different engine's nonlinear stem
processing must not be presumed to exist here.

OPERATOR-REPORTED, NOT INDEPENDENTLY VERIFIED: Star Light residual 0.008508
RMS and exact regenerated master SHA-256
409427bcebe6e0397cff7a005efc940eb429c22ed0b1eecacbb842d57e4206fc.

REQUIRED STUDIO CONTRACT:
- reconstruction_stems: dry, integer-sample-aligned, same channel layout,
  pre-bus components. Their immutable CAS identities must be lawfully bound
  to the exact ProjectRevision. No independent waveshaping/normalizing.
- mix_recipe: version, sourceProjectRevisionId, productionTimelineDigest,
  stemArtifactIds in deterministic summation order, bus_waveshaper and exact
  parameters, fade_ms, target_peak, sample_rate, channels, sample_count,
  PCM rounding/clipping, WAV encoder/header version, and canonical digest.
- creative_stems: independent artistic processing permitted, explicit
  exact_reconstruction_certified: false.
- production_master: float64 sum of reconstruction stems, then the exact
  revision-bound recipe, then deterministically encoded WAV; assert entire
  WAV SHA-256 equals a source-verified master in a fresh process.
- Recovery: durably record artifact ownership before CAS publication, then
  lawful project/revision association. Never authorize media via CAS
  existence/digest alone or overwrite CURRENT with late historical audio.

REQUIRED REGRESSIONS WHEN SOURCE ARRIVES:
- RED reproducer from authentic dry stems, exact mix script, and Star Light
  original master; GREEN whole-WAV digest match after cold restart.
- Negative creative-stem exactness claim, nonassociative float ordering,
  sample-shift, stereo layout, clipping/NaN, recipe identity tampering,
  unauthorized reads, and crash-fault boundaries.

BLOCKED OWNER: S.A.R.A. Studio music/render authority.
BLOCKED EDGE: no canonical Sample Lab export implementation or qualifying
Star Light source master/stems/recipe in inspected repo and Project evidence.
WAKE CONDITION: authenticated owner source and source-bound media with
independent digest readback; then change the actual renderer, not a shadow
CAS/master implementation. This note is not certification.

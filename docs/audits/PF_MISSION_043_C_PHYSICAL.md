# Mission 043 — Work C physical lyric timing + recovery

**Freeze:** `M043_FREEZE_SHA = 076aed8d438a938119a7c2d5b34bb5eeb3ba4409`  
**Release:** 2.20.0  
**Parent M042:** `7c92fe7a39d6b4209be510d02781adb6a1ef4182`

## Fixture (physical)

| Field | Value |
|-------|--------|
| Path | `evidence/m043/fixtures/rise-higher.wav` |
| Provenance | **synthetic spoken** Flite 2.2 `cmu_us_kal` — NOT human / NOT singing |
| Container | WAV PCM |
| Sample rate | **8000** Hz |
| Channels | 1 |
| Decoded frames | 17539 |
| Duration | 2.192 s |
| File SHA-256 | `b64d26f624da0722337be7153ab01296ef4c645a68e6527d9b6ac9946ab904e3` |
| **Decoded PCM SHA-256** (authority) | `4746aca332f19dfc72e45383a75e7a876f6c8e09f8e5b10df149725441a051bb` |
| Known phrase | rise / higher |

## Timing vs ground-truth placement bounds

| Rev | Word | startΔ samples | endΔ samples | startΔ ms | endΔ ms |
|-----|------|----------------|--------------|-----------|---------|
| R1/R2 | rise | 0 | +12 | 0.0 | 1.5 |
| R1/R2 | higher | −68 | +61 | −8.5 | 7.625 |

**Aggregate:** median |start| error **4.25 ms**; median |end| **4.56 ms**; **max boundary error 8.5 ms**.

Correction is **TEXT_ONLY** (sample windows identical R1→R2). Audio digest unchanged.

R1 revisionId `84925a9d…` · R2 `29ccc969…` parent=R1.

## LYRIC_TIMING_PHYSICAL = PASS — BOUNDED

Boundary method is signal-placement bounds, not human phoneme annotation. Max error ≪ 50 ms informal ceiling.

`observationId` present as `wordId` in fixture intentionalCorrection (`w1`); discriminator word objects may omit separate observationId field — occurrence identity via revision + index + wordId is sufficient for this cone.

## LYRIC_REVISION_RECOVERY = PASS — BOUNDED

- 35/35 unit tests on freeze
- 25/25 lyric-discriminator checks PASS (`fresh-process-cache-free-R2`, stale reject, instrumental negative, audio-unchanged, etc.)

## Non-claims

- Not full ASR quality
- Not sung-vocal alignment
- Not LYRIC_INTELLIGENCE_PASS until D adversarial matrix
- Not product candidate

## Verdict

```
LYRIC_TIMING_PHYSICAL = PASS — BOUNDED
LYRIC_REVISION_RECOVERY = PASS — BOUNDED
```

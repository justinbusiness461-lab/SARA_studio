# Chat D M044 — Playback publication race hardening v3 (2026-11-10)
Main on verified refresh: `14e2fb9cc55c8ce2909803a66d509915a18eb625`. PR #10 merged; PR #11 still open, PR #16 draft documentation-only.
## First user-facing risk
A valid R1 network response may complete after user chooses R2. A revision-bound artifact by itself does NOT stop a stale browser completion replacing transport playback.
## Contract
Keep ephemeral request generation outside project authority. Only publish if request generation matches latest user intent AND requested revision/artifact match selected history. Historical R1 playback is permitted only when explicitly selected and labeled historical. Never mutate current ProjectRevision in response to network completion.
## Evidence
TDD local v3: three failure assertions were RED before adding generation checks; six focused tests PASS after adding checks. Local full v3 ZIP at `M044_ChatD_Stale_Playback_Publish_Fence_v3_2026-11-10.zip`. A repository-compatible minimal checker and six scenario tests are in `audits/chat-d/m044_playback_publication_fence.py` and `audits/chat-d/test_m044_playback_publication_fence.py` (independent repo execution not claimed).
## Findings
P1: stale R1 fetch could overwrite selected R2 presentation absent generation fence (risk, not observed production defect). Owner Bobby/Cody Studio UI. Impact wrong song heard. Next real browser async race.
P1: authenticated stream/playback remains unqualified (PR #16 docs only). Owner Work A/Bobby. Impact cannot certify Studio. Wake implementation PR + Work C real physical decode.
## JUSTIN 101
WHAT CHANGED: machine-checkable stale publication contract committed outside product source.
WHAT FAILED/BLOCKED: no connected Studio browser/audio exercise.
WHAT IS PROVEN: local six focused contract tests, main SHA/PR metadata.
WHAT IS NOT PROVEN: production transport/cross-user authorization, musical quality, deployed app.
WHAT JUSTIN MUST DO: Nothing.

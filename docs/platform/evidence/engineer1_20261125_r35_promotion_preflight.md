# Studio Engineer #1 · R35 — stale-main preflight and real DENIAL_01 authority hold

**Date:** 2026-11-25. **Owner:** `SARA_studio`, Engineer #1, sole Studio `main` promotion queue. **Authorization:** READ-ONLY preflight only; no merge, issue, project revision, rights grant or deployment. **Evidence class:** E1 source inspection + E2 local reference tests; historical R33 media observation, not Studio accepted audio. **Production:** HOLD.

## Exact intake and first failed edge

- Canonical Studio `main=d6aa889a0def72bb8e1c87009a98d6c29e47067e`.
- PR #36 `862a7ed11f12835b92c4f0b5673241ae4362b8c2`, PR #37 `d876cad4d55aadee144e7bf6756c224b41a8c117` stacked on #36, PR #44 `2d3953b6bdc3f24143803c2f45e49460dfe58ea6` stacked on #37 (all **DRAFT**, NOT MERGED at intake).
- New constitution requires a candidate-qualified `main` SHA, candidate head SHA, parent/base SHA, receipt digest, full suites and conservation, owner, temporal currentness and 9-file continuity before serial promotion. A PR showing `mergeable=true` is not physical qualification.
- Real required suite for PR #44 (`SARA_R25_REAL_MEDIA_STRICT=1` positive 3-song Chromium; fresh 390/1440; 6 media clocks, 2 A/B switches <=50ms) **NOT EXECUTED**. Full exact-head Python/Node/Chromium **NOT EXECUTED**. Host-private R2 immutable receipt not read here. Rights `UNVERIFIED_HELD`.
- Denial original full 48-kHz stereo PCM16 = 10,154,880 frames (211.560s), historical reference decoded SHA `9ddb2468d5aa4b367852c9e6efbc18098e507284cbadb40f23a7eacb64232f42`; 60–94 second review WAV 1,632,000 frames and SHA `760dc44937e905176d8da72adc9c4e4f0884822adbe7b045e1b1dfd4d67048ef` physically reread this round. Neither is an accepted Studio ProjectRevision/decoded artifact.
- `tools/m045_vocal_occurrence_contract.py` exact PR44 source still always raises `VOCAL_ONSET_UNVERIFIED` from `require_verified_vocal_onsets`; RIGHTFUL Studio authentication not yet implemented. `tools/lyric_timeline.py` `pcm_info` still has an explicit 1–60-second WAV bound: the 34s observation candidate fits the older metadata tool but its digest is **not interchangeable** with a full-song accepted decoded PCM digest; a 211.560s full song cannot be passed through that existing method unchanged.

## Bounded source repair (no shadow governance authority)

`tools/studio_promotion_ticket.py` is a **pure negative preflight**. It accepts a structured candidate ticket and separately supplied fresh GitHub main, PR head and base readbacks; checks unique canonical owner, exact hashes, freshness, suites, continuity, blockers and cross-repo prerequisites. Any mismatch produces a HOLD/stale status. Even structurally complete evidence returns `REQUIRES_INDEPENDENT_REVIEW`, never `mergeAuthorized=true`. The checker cannot fetch GitHub, verify source contents, certify hashes or authorization, merge, or attest a real-onset witness. Main integration remains the rightful human/CI gatekeeper's separate action.

`tests/test_studio_promotion_ticket.py`: RED initial `ModuleNotFoundError`, GREEN **16/16** local Python focused tests, no skips/failures; syntax compile PASS. Scope includes stale main, changed candidate head/base, wrong owner, missing positive Chromium, fake booleans, skipped tests, failed conservation, bad/absent qualification receipts, stale recovery, unqualified Studio→PulseForge prerequisite and deceptive E3/E6 claims. These are synthetic/reference ticket tests only.

`docs/platform/evidence/engineer1_20261125_r35_promotion_preflight.json` records one concrete PR44 preflight with the observed actual SHA values. It returns `QUALIFICATION_HOLD` / `mergeAuthorized=false`. No qualification receipt is substituted or invented, and no observed DENIAL_01 onset is asserted.

## Required wake condition / stop

- **Studio issuer:** lawful principal+project, accepted ProjectRevision/audio artifact and decoded-PCM origin identity, independent performed `DENIAL_01` witness proving pre-onset context plus transition inside a source-bound window, then Studio-issued immutable authenticated LyricTimelineRevision/occurrence with exact artifact+digest+origin. Until then `onsetSample=null`, `verification=UNVERIFIED`, 55-word expansion HOLD, PulseForge render HOLD.
- **Studio #2 qualified executor:** exact PR36→37→44 integrated runnable tree, private authorized R2 revision/receipt; strict positive real master 390/1440, six actual audio clocks, two real A/B <=50ms, cold restart, full exact-head suite, rights noncommercial gate.
- **Studio #1 main queue:** wait for source/test/physical tickets from independent lanes, reconcile against fresh main, serial merge only if all gates pass. No main merge, deployment, release or creative approval performed R35.

**JUSTIN 101:** SOURCE/TEST delta=R35 preflight negative gate; PROVEN=16 focused reference tests and actual PR44 negative decision; FAILED=Studio accepted source signal and positive strict full suites; TEAM NEXT=canonical source issuer and qualified Studio #2 runtime, Studio #1 serial queue last; JUSTIN ACTION=none for this source-level handoff.

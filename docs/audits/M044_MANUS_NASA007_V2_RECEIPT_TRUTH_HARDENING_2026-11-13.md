# M044 / NASA-007 — receipt-assertion bypass and QA-only repair

**Date:** 2026-11-13. **Owner:** Internal Manus independent QA lane. **Classification:** HARDENING_ADVANCE / QA artifact, not production certification.

## Exact current authority

- `justinbusiness461-lab/SARA_studio`, repo ID `1427534706`, main `749127ce0ce2cd08cdc5a6354626a078064f4704`.
- PR #22 candidate `91ed45f67f8c0bd432a7f4afb5de7a9ebe1dbdf5`, merged `1ea3909a25a2365862bd6a1106cfb386d933a504`.
- PR #23 Runnable NASA-002 head `9e301f20786fdb3b6edc8ef3ab2d3d1c9484fc80` (open, clean-room reproducibility preparation).
- PR #24 Work C physical-audio head `546e73ae51dfe3245736d806126f3237002d3ae1` (open; reported 50.5-second audio with 8 target bass events, 0 PCM changes outside declared edit/tail, direct API only; browser/audio quality not certified).
- PR #18 remains independent QA owner; no main/product mutation.

## Material finding

**Severity: P1 (qualification false-positive), QA owner: Manus.**

The previously generated NASA-007 validator accepted 60 switch objects containing just `{index, passed:true}`, alongside self-asserted `proofOrigin='REAL_BROWSER_AND_SERVER'`. It did **not** require per-switch source/target revision identity, audio artifact SHA, playback Proof, A/B Proof, request generation, or observed musical position.

This could cause an unsupported or contradictory product PASS without demonstrating the advertised A/B invariant. This is a *test-harness defect*, not a demonstrated defect in merged Studio.

## RED → GREEN

Reproduced in a disposable local JS test suite:

- **RED** original checker with stronger tests: **27/30 pass, 3 fail** (specifically complete observed receipt not accepted while legacy asserted-only receipt accepted).
- **GREEN** corrected checker and browser-receipt recording: **30/30 pass**; JS syntax checks pass.
- Existing exact-main browser execution: **0/60** in this executor, because the authorized exact checkout and Playwright are unavailable.

Revised receipt schema: `sara.nasa007.product.v2`. Legacy v1 assertion-only receipts fail closed.

Every actual switch now has to carry **strictly increasing request generation; COMPLETE state; expected alternating R1/R2 from/to revision and artifact identities; exact matching transport, playback and A/B Proof; WAV SHA; independent backend-current reread; positive timing; <=50 ms A/B musical-position difference**. A mismatch is a HOLD, regardless of `passed:true`.

This is **structural assertion checking**, not cryptographic authentication of raw browser evidence. Independent source log/runtimes, real WAV bytes, authorization and resource statistics remain required.

## Downloadable execution package

One file: `SARA_STUDIO_MANUS_NASA007_HARDENED_SINGLE_UPLOAD_2026-11-13.zip`.

- ZIP SHA-256: `c97389de25a6b504558f18fdbfa74062ffd6567a77e84860c692c2d7a78c3c66`
- 12 members; ZIP CRC and all per-member SHA-256 manifest entries pass.
- Includes `NASA007_V2_CORRECTION.md`, original mission, updated browser/contract code, 30 tests, 47-entry execution matrix, RED/GREEN logs and v2 receipt.
- Corrected QA source hashes:
  - `nasa007_browser.cjs`: `a72c712b5ecaee474b5b2863ae47838370bbb213042fd3d33b7dae4bb2cd845f`
  - `nasa007_contract.cjs`: `1c1f4e676501d62984975362ce983289e3b646ff5cea57c7949f91e5d7c8088d`
  - `test_nasa007_contract.cjs`: `96e82f70875ece15b148a383a764243e79339d30b58eca61bbc2d962f9361eb1`

**Important:** GitHub contains this audit/receipts, not the executable bytes of the local ZIP. The ZIP is an explicitly separate ChatGPT handoff. Real independent execution requires exact authenticated source checkout.

## Remaining boundaries, no false inference

- Real 60-switch UI endurance: **NOT RUN** here.
- Hosted two-principal tenancy: **UNVERIFIED**; local Studio mints sessions for the same `LOCAL_PRINCIPAL_ID`.
- Work C direct-media measurements do not qualify real browser A/B.
- Work B bounded post-PR22 PASS remains valid in its own scope; it is not re-run or undermined here.
- Bobby, Work A/B, cinema, and `main` untouched.
- Manus work is owner-disjoint; Runnable PR #23 covers deterministic clean reproduction.

## JUSTIN 101

**WHAT CHANGED:** Closed a false-positive gap in NASA-007's *independent certification harness* with 30 local tests and an executable one-file update.  
**WHAT FAILED/BLOCKED:** Real Studio physical endurance and hosted multi-tenant security not executed in this runtime.  
**WHAT IS PROVEN:** RED 3 failures against old verifier, GREEN 30/30 against corrected verifier, ZIP CRC/member digests, exact GitHub currentness.  
**WHAT IS NOT PROVEN:** 60 real browser switches, production hosted security, deployment or creative musical approval.  
**WHAT JUSTIN MUST DO:** No repo action; new one-file NASA-007 packet replaces older one when the Manus execution environment is available.

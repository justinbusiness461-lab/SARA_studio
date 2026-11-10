# M044 — Manus NASA-004 independent QA harness

**Scope:** tests-only, owner-disjoint, no production runtime mutation. **Date:** 2026-11-10.

> **Do not deploy or present this code as S.A.R.A. Studio.** This folder tests a prospective real audio transport seam and contains a pure non-production presentation-fence reference. It does not implement any Sound Forge endpoint or another revision store.

## Exact refresh pins

- \`pulseforge-songforge/main\`: \`14e2fb9cc55c8ce2909803a66d509915a18eb625\`; PR #10 merged; PR #11 still open/stacked at \`cb80d4fe06cc1148651787872ad89216c20328f3\`.
- \`dj_rezrxtion/main\`: \`cd8997c260f552d28c1230d16954a59203a78d57\` (Forge research reference only).
- \`engineering-organization-governance/main\`: \`f45ae27df34c9b53507bff653b59258f05eac020\`.
- Manus managed local checkpoint \`f6001a15b314a2c90b1b2737d92117b41a360a1f\` was **reported**, not remotely verified or imported.
- [G3 bridge contract, PR #16](https://github.com/justinbusiness461-lab/pulseforge-songforge/pull/16) is **documentation-only**; the real authenticated audio read endpoint is **not verified on main**.

## What this tests

- \`studio_acceptance.py\`: independently verifies PCM16 RIFF/WAVE structure, chunk lengths, decode, audio identity, stereo/peak/DC and unchanged PCM outside a bounded edit.
- \`test_studio_acceptance.py\`: 15 synthetic unit tests (reused from the earlier independent QA packet).
- \`live_nasa004.py\`: an **actual HTTP GET-only** two-principal probe. Twelve required cases check own/foreign/anonymous project reads, R1/R2 WAV retrieval, historical read, arbitrary digest denial, audio SHA-256 and response revision association. It never logs credentials or raw audio.
- \`test_live_nasa004.py\`: 16 tests against a disposable localhost HTTP test server, including broken authorization, bad WAV, wrong digest, missing/wrong revision header, forbidden redirect and target tampering.
- \`transport_fence.cjs\` / \`transport_fence.test.cjs\`: ten Node tests of a **pure, ephemeral, non-production reference**: 60 rapid A/B selections, delayed R1 result, explicit historical play, current-authority change, cancellation, missing/malformed audio and no phantom current revision.
- \`NASA004_LIVE_FIXTURE_TEMPLATE.json\`: **placeholder paths and dummy hashes only**. It does NOT identify any existing product endpoint.

## Reproduce (Python stdlib + Node built-in runner)

From repository root:

\`\`\`bash
python3 -m unittest discover -s tests/manus-nasa004 -p 'test_*.py' -v
node --test tests/manus-nasa004/transport_fence.test.cjs
\`\`\`

**Executed locally against the byte-identical files submitted on this branch: 31/31 Python tests and 10/10 Node tests PASS.** This covers synthetic fixtures and a disposable local HTTP test service; it **does not** prove any hosted Manus app, production auth, or product playback.

## Gate when the real G3 accessor is qualified

Replace placeholder routes, target SHA and expected canonical R1/R2 hashes with **independently captured** values in a private runtime fixture. Store actual authenticated session cookies in protected environment variables **only**. Never paste them into source, GitHub, chat, proof logs or a public file.

\`\`\`bash
export NASA004_COOKIE_A='REPLACE_IN_PRIVATE_EXECUTOR'
export NASA004_COOKIE_B='REPLACE_IN_PRIVATE_EXECUTOR'
python3 tests/manus-nasa004/live_nasa004.py \
  --fixture /private/runtime-nasa004-fixture.json \
  --output /private/nasa004-live-receipt.json
\`\`\`

The executable refuses missing/equal credentials. It returns exit 0 on all 12 live GET checks, exit 2 on HOLD. A local no-credential test was **executed** and correctly returned HOLD / exit 2.

The approved audio route must prove project ownership and source-revision association—not just artifact digest or filename. The verifier currently requires \`X-Source-Revision-Id\` and \`X-Audio-SHA256\` on authenticated audio responses. An alternate owner-approved proof binding can be accepted only through an independently reviewed verifier change, **not** by silently disabling the identity test.

**WARNING:** The live probe is read-only; it cannot certify user mutations, mobile/desktop UI, restart recovery, audio range semantics, or actual 60-switch browser behavior. Those require additional app-level tests and Work B/C/D qualification.

## Qualification ceiling and owner boundaries

| Item | Result |
|---|---|
| Synthetic audio/security verification | PASS 15/15 |
| Fake-local-server HTTP verifier negative/positive tests | PASS 16/16 |
| Standalone publication-fence reference tests | PASS 10/10 |
| Real hosted Manus run | UNVERIFIED |
| Live two-user project/audio HTTP probe | BLOCKED — endpoint and two authenticated sessions unavailable |
| Canonical Sound Forge G3 artifact retrieval endpoint | BLOCKED — owner-approved implementation/proof missing |
| Manus/GitHub branch synchronization | UNVERIFIED |
| Product runtime code changes | NONE |
| Real deployment or creative listening proof | NONE |

**Next handoff:** after Bobby/Work A deliver a qualified revision-bound, tenant-authorized WAV retrieval seam and Manus has a verified checkout, run the two-principal live probe against the exact approved SHA, then run real browser playback and race tests. Do not reinterpret this harness's synthetic PASS as production certification.

**SJ³:** VALIDATE → REUSE → EXTEND → REFACTOR → CREATE ONLY IF REQUIRED. Source != runtime. Build != feature. Prompt != sound.

# M045 / HVC-003 — Studio soundtrack-grant issuer candidate

**Date:** 2026-11-20 · **Rights owner:** SARA_studio (repo ID 1427534706)
**Branch:** feat/m045-native-generation-attempt; Wave 004 starting SHA \`5ddb3b5e7de75c7aca64f68dc9b599bd0c1032f8\`.
**State:** SOURCE COMMITTED + BOUNDED ISSUER TESTED. HTTP / cross-product production authorization **not** certified.

## Implemented
- \`tools/m045_soundtrack_grant.py\` issues signed \`sara.soundtrack.grant.v1\` with scoped audience \`pulseforge_cinema\`, 300-second TTL, host-only HMAC keyring, 44.1/48 kHz PCM16 physical digests, exact \`ProjectRevision\` + \`ProductionTimeline\` readback, lawful historical revision→artifact association via the **existing** Studio \`project_operation\` and \`project_audio_bytes\` owners, host-only independent \`rights_policy\`, 24/1 or 30000/1001 rational frame cover. It rejects all client sample/frame/rights overrides and does not mutate Studio current revision. Current implementation limits an issued section to 15 seconds; no general 210-second or 7,114-frame master support claimed.
- \`tools/studio_server.py\` wires authenticated \`POST /api/m045/soundtrack-grant\` into the existing same-origin capability/session/principal controls. **Without host configuration** using \`configure_m045_soundtrack_grant(HostSigningKeyRing, rights_policy)\`, the route returns 503 BLOCKED. Caller-supplied rights/keys never enable issuance.
- \`index.html\` and \`app-ui.js\` add a 48px+ mobile "Create Music Video" grant request, binds the currently selected **verified playable revision/audio** and existing cinema project ID with project-open/request generation fences. A grant receipt explicitly does **not** claim a film was rendered, accepted, or qualified.
- \`tests/test_m045_hvc003_grant_issuer.py\` covers signed historical R1 without current promotion, denied client frame/sample override, wrong artifact/rights refusal, rational 29.97 fps nonzero sub-window, tamper/revocation.

## Execution evidence

\`\`\`bash
PYTHONPATH=/path/to/studio/tools python -m unittest discover \
  -s /path/to/studio/tests -p 'test_m045_hvc003_grant_issuer.py' -v
# 5 tests, 0 failures, 0 skipped — local isolated replay
\`\`\`

The previous Wave004 result **256/256** is the supplied baseline for \`5ddb3b5e\`, **not** a rerun result for this new issuer code. Full Studio Python, Node, Chromium, browser, HTTP/live host and cross-session suites need rerun on the exact new SHA before promotion. After a test runner first failed for missing \`PYTHONPATH\`, rerunning with the correct tools path passed 5/5; report only the correct command for reproducibility.

**Fresh cross-repository synthetic media smoke** independently called the actual Studio issuer source, signed a 720,000-sample 48-kHz 15-second mock-authorized R1 grant, and passed it to cinema's independent HMAC/authority resolver, rendered an H.264 blue bar/spline preview, decoded 360 global frames, and measured 0.99962 assigned-control correlation for two bars. This smoke used **synthetic PCM, a fake Studio revision, and a test-only rights callback**, not a real Studio artist project. No live HTTP grant or real artist soundtrack was used.

## Security and operator gates

- Real rights evidence and signing keys must be supplied by the trusted **host**, bound to a real principal+project+historical R1/R2+artifact. Browser session tokens alone do not authorize rights.
- Production cinema must **re-read Studio authority** for project/revision/artifact, lawful membership and audio sample window; signed self-assertions or matching CAS digest alone never grant access.
- HMAC has shared-secret operational risk; enforce separate scoped key storage, revocation/rotation, and an independent host trust boundary before deploying.
- A returned signed grant is not a RenderArtifact, film VisualRevision, audio playable, physical QA, or creative approval. UI must not mark it as such.
- Historic R1 remains available lawfully without becoming R2 current; cinema V1→V2 explicit artist rebinding remains the cinema owner's job.
- No changes to \`song_forge\` or cinema product authority.

## JUSTIN 101
**Changed:** Studio-owned code for issuer, route, UI and five conformance tests.
**Proven:** Scoped source tests and GitHub source readback; synthetic 15-second cross-repo code compatibility.
**Unproven:** Real host-configured issuer call, current Studio runtime full suite, real media rights, authenticated cross-server transfer, production film.
**Team next:** Studio Work A configures and certifies host signing+rights authority, reruns full tests and live HTTP readback; PulseForge owner wires canonical VisualRevision and decoded-film proof.
**Justin action:** None for this draft. No spend, merge, or release.

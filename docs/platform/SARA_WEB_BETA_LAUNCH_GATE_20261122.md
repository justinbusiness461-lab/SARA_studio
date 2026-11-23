# S.A.R.A. Studio™ — R18 controlled web-beta launch gate
2026-11-22 · Engineer #1 · canonical owner: `SARA_studio`

**Current decision: HOLD — not a launch authorization.** This is an engineering acceptance ledger, not a release receipt. `main`, cinema authority, production accounts and billing remain outside this document's write scope.

## Evidence newly available
- The user-identified authorized private Google Drive folder (source IDs withheld) has three real artist source files. Independent transfer, source SHA-256 and full 44.1/48 kHz stereo PCM16 decoding are recorded in `docs/platform/evidence/kernel_20261122_round18/three-song-source-observation.json`.
- Round 18 host-ingestion source exists on the Studio draft feature branch in `tools/m045_artist_master_ingestion.py` and `tests/test_m045_artist_master_ingestion.py`. Its host-rights callback, canonical project graph, exact render-artifact association, and fail-closed timing check should be preserved.
- That manifest does **not** certify these media as commercially rights-cleared, imported Studio project revisions, accepted soundtracks, physically playable via the hosted app, or approved for cinema.
- Source-byte verification is independent of upstream title/metadata; local filenames are not creative authority. All three decodes succeeded, but all `issuedGrantCount` fields remain zero.

## Web-beta release boundaries
| ID | Minimum exit evidence | Disposition |
|---|---|---|
| WB-01 | Authenticated production principals; HTTPS Secure cookies, CSRF protections, session revocation, rate limits, account recovery; independent access-control testing | HOLD |
| WB-02 | Three host-authorized source catalogs with rights evidence; admission to ProjectManifest/ProjectRevision/CAS; lawful exact-revision media reads; fresh-process reopen | HOLD |
| WB-03 | Verified browser player for each actual accepted source; A/B musical-position proof and Sonic Lock preservation; no stale playback/currentness claim | HOLD |
| WB-04 | Real accepted soundtrack binding: sourceProjectRevisionId + acceptedAudioArtifactId; secure signed short-lived grants with separate durable historical associations | HOLD |
| WB-05 | Production host sample/master rights, creator publication consent, license policy, takedown, and independent revocation proof | HOLD |
| WB-06 | Deployed public deletion-request URL; verified ownership and fully reconciled erasure/retention and recovery controls | HOLD |
| WB-07 | Production payment receipt verification, atomic credits, idempotent events, reconciled refunds and authorization; no client-minted credits | HOLD |
| WB-08 | Hosted deploy health, metrics, error reporting, bounded jobs, backup/restore, incident handling and rollback | HOLD |
| WB-09 | Full exact-SHA Python + Node + Chromium regression and independent security/performance QA in target hosting environment | HOLD |
| WB-10 | Artist-validated critical journey: login → source → generate/edit exactly → listen → reopen → prove preservation → authorized publish/unpublish | HOLD |
| WB-11 | Explicit accountable owner approval, legal/privacy review, terms and customer support coverage before exposing paying customers | HOLD |

**Separate later gate:** native signed builds, iOS/Android audio/lifecycle/interruptions, StoreKit and Play Billing, accessibility and Apple/Google store review. A web beta PASS must not be presented as a native release PASS.

## Required Round 18 next lawful execution
1. Use exact Drive-file identities and locally measured source digests to qualify the **host-managed rights catalog**. Do not derive `ARTIST_ORIGINAL` solely from Drive ownership, title, a user-supplied field or a source SHA.
2. In a fully authenticated Studio executor with the source bytes, run `ingest_three_song_batch` against the current exact branch and issue three *reproducible project/revision/audio identities*. Reopen independently and read back the selected, historically associated audio.
3. Qualify musical sections and timing before calling `issue_accepted_master_grant`; reject the built-in 120 BPM placeholder as a grant source. Require exact rights, signer, audience, expiry, project membership and physical audio checks. Until then, the three-song grants manifest must remain a truthful HOLD.
4. Re-run the complete Python, Node and Chromium cohorts on the exact final product tree. Record actual tests, failures/skips, branch/SHA and raw logs; no borrowing historical test counts.
5. Independently assess the gate above before a protected branch merge, external deployment, payment collection or production publication. Paid GPU remains separately unauthorized.

## Authority and recovery
`SongSpec`, `ProductionTimeline`, `ProjectRevision`, `ProjectManifest.currentRevisionId`, and immutable `RenderArtifact` remain the only musical authorities. Source CAS digest does not authorize content consumption, and historical successful playback never promotes a stale revision. Never blind-retry after an ambiguous durable commit; reread canonical project selection first.

**Disposition:** Source-media retrieval and decoding PROVEN locally; source-specific Studio ingestion implementation EXISTS in draft PR #37; production authorization, canonical three-song imports, signed grants, browser playback and commercial launch remain **HOLD**.

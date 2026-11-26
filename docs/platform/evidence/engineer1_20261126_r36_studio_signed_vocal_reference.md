# R36 Studio V3 signed DENIAL_01 witness/occurrence reference contract

**Owner:** `justinbusiness461-lab/SARA_studio` (music truth). **Scope:** additive pure validation helper, not publication. **Evidence ceiling:** E1 source + E2 synthetics; not E3 real musical occurrence.

Reuses exact existing Studio `ProjectManifest`/`ProjectRevision`/`LyricTimelineRevision` return shape; requires lawfully principal-authorized `project_operation` response, source audio bytes and decoded WAV bytes that were lawfully retrieved after revision membership checks. It verifies that original bytes hash to a CAS `sourceAssetDigests` member and decoded WAV hashes to an `outputArtifactIds` member, and that lyric metadata binds to the decoded PCM digest, rate, channels and complete frame count. Never grants authorization based on a caller-provided digest alone.

V3 differences vs supplied ZIP: Python-native module (Studio server is Python), canonical JSON decimal-string sample coordinates (portable to JS), independently signed observer evidence, separate Studio issuer signature, real Ed25519 verification, exact authorization-grant identity/currentness, explicit pre-onset sample in window, exact `windowStart + localOnset` derivation. Signed receipt is a **candidate only** until Studio's rightful immutable LyricTimelineRevision publisher stores the lawful association and durable signature/trust-root record. The module adds no REST route, key registry, CAS scanner, hidden publisher, or production permission bypass.

`cryptography>=42,<48` required at runtime for Ed25519; absence is a hard failure. Production signing keys must come from the owner-controlled secret manager and the trusted key registry must be independently provisioned. The included test creates **ephemeral synthetic keys** and a five-second artificial WAV; those observations are not performed word evidence. Real DENIAL_01 is still **UNVERIFIED**. Do not promote 60–94-second local audition into full original Studio PCM association. No 55-word expansion, commercial authorization, audio playback certification or creative approval.

Test: `PYTHONPATH=tools python3 -m unittest discover -s tests -p 'test_m045_v3_signed_occurrence.py' -v`.

Current blocked edge: accepted canonical Studio full-song decoded PCM and lawful `ProjectRevision`/CAS association; independent performed attack witness and Studio persistent issuer; then PulseForge signed receipt consumption and physical final-container decode proof. The real existing M043 lyric metadata helper retains its 1–60 second bound and has not been silently widened.

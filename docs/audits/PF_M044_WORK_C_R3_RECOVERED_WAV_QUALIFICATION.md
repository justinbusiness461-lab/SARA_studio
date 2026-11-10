# M044 Work C — recovered WAV delivery qualification

November 10, 2026 · Sound Forge main `14e2fb9cc55c8ce2909803a66d509915a18eb625` · Candidate runtime **BLOCKED**

The early-crash reproducer in PR #17 and the two-user GET probe in PR #18 cover separate boundaries. Join them using the same physical artifact. A passing recovery test against one fixture and a passing HTTP test against a different fixture leave the recovered-output delivery path unverified.

| Severity | Evidence | Owner | Impact | Blocker | Next action |
|---|---|---|---|---|---|
| P0 | PR #17 and mounted NASA-005 receipt report zero R1 bindings after the early kill | Bobby, then Work B | Valid bytes survive without discoverable history | Exact R3 candidate | Run retained fault probe at both boundaries. If the seam moved, instrument the replacement and prove where the kill happened |
| P0 | PR #18 has an executable GET probe, with no live qualification in its receipt | Bobby / application owner, then Work B and Work C | Recovered audio may exist on disk but remain inaccessible, or be served under the wrong identity | Approved candidate accessor and two test principals | Use the recovered artifact from the crash run as the HTTP fixture described below |
| Evidence identity | Mounted `tlspec2.zip` names Manus result `520155e9995732f89388556f45aa8ab1e96a8003`; pasted report names `c307cb5e8aecd914374e7d8ce6f94f04cc496bf4` | Manus | A build claim may attach to the wrong checkout | Remote checkpoint readback | Retain the identities separately until Manus publishes and rereads the intended checkpoint |

## Combined acceptance case

1. Pin a clean successor SHA and use an isolated test workspace with two principals. Capture R1's initial output, R2's current output and a distinct late R1 output. Record project ID, committed revision IDs, operation ID and each WAV/decoded PCM SHA-256 from the trusted engine side before making HTTP requests. Require three distinct WAV digests so a default-output fallback is detectable.
2. Kill at the qualified early durability boundary. Restart against the same durable workspace, with a fresh process and no caller replay. Open twice. Require exactly one late-artifact binding on R1, immutable R1 revision, and the same R2 current ID and output digest.
3. Through the owner-approved route and principal A, GET all three WAVs from their actual revisions. Verify each complete response against its engine-side expected SHA-256, independently decode it, and verify PCM SHA-256 and format. The recovered R1 response must differ from the original R1 response. A revision label or response digest header alone is insufficient.
4. Request that same recovered digest as R2, under another project, as principal B against A's project, and anonymously. Require denial and no audio bytes. Run the existing two-principal probe for the general matrix. If Range is supported, check exact byte slices of the already authenticated full object and repeat an unauthorized range request.
5. Report separate verdicts for recovery, physical audio validity, exact musical edit, authorized HTTP delivery and browser playback. Engine and HTTP results cannot certify audible A/B. Browser proof must check the selected artifact and same musical position.

Retain prior local PCM and transposition measurements when relevant fixture PCM and edit-event identities match. Rerun measurements that depend on changed bytes or changed render/analysis inputs. A successor with a missing fault seam, accessor, or principal pair stays blocked at the affected boundary. No candidate runtime tests ran for this handoff.

- [Work C recovery evidence and reproducer](https://github.com/justinbusiness461-lab/pulseforge-songforge/pull/17)
- [NASA authenticated HTTP harness](https://github.com/justinbusiness461-lab/pulseforge-songforge/pull/18)

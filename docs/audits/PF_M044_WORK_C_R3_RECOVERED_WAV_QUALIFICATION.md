# M044 Work C — recovered WAV delivery qualification

November 10, 2026 · Sound Forge main `14e2fb9cc55c8ce2909803a66d509915a18eb625` · Candidate runtime **BLOCKED**

The early-crash reproducer in PR #17 and the two-user GET probe in PR #18 cover separate boundaries. Join them using the same physical artifact. A passing recovery test against one fixture and a passing HTTP test against a different fixture leave the recovered-output delivery path unverified.

| Severity | Evidence | Owner | Impact | Blocker | Next action |
|---|---|---|---|---|---|
| P0 | PR #17 and mounted NASA-006 receipt report zero R1 bindings after the early kill | Bobby, then Work B | Valid bytes survive without discoverable history | Exact R3 candidate | Retain the probe as a negative control. Verify that the exact WAV digest and intended CAS identity are durable before publication, then qualify Crash A and Crash B |
| P0 | PR #18 has an executable GET probe, with no live qualification in its receipt | Bobby / application owner, then Work B and Work C | Recovered audio may exist on disk but remain inaccessible, or be served under the wrong identity | Approved candidate accessor and two test principals | Verify pre-reconciliation denial and post-reconciliation byte identity on the same crash artifact |
| P0 | Runnable PR #19 at `929073cd67fe` accepted a synthetic receipt with `verdict=PASS` and `historyOccurrences=0` (checker exit 0) | Runnable | Contradictory evidence can pass the gate | Corrected verifier with negative tests | Recheck the verifier independently and preserve raw observations for Work C |
| Evidence identity | Mounted `tlspec2.zip` names Manus result `520155e9995732f89388556f45aa8ab1e96a8003`; pasted report names `c307cb5e8aecd914374e7d8ce6f94f04cc496bf4` | Manus | A build claim may attach to the wrong checkout | Remote checkpoint readback | Retain the identities separately until Manus publishes and rereads the intended checkpoint |

## Combined acceptance case

1. Pin a clean successor SHA and use an isolated test workspace with two principals. Capture R1's initial output, R2's current output and a distinct late R1 output. Record project ID, committed revision IDs, operation ID and each WAV/decoded PCM SHA-256 from the trusted engine side before making HTTP requests. Require three distinct WAV digests so a default-output fallback is detectable.
2. Exercise the actual late R1 render twice in fresh isolated copies of the same project state. Start with the late digest absent from CAS and record the staged WAV's validated metadata and independently computed file and PCM digests. At each kill point, read back the durable attempt without opening the project. Require matching operation, project, source and expected revision, render meaning and configuration, staging identity, exact artifact digest and intended CAS identity.

   | Crash | Required state at kill | Required restart observation |
   |---|---|---|
   | A | The attempt has durably recorded the exact artifact identity as `VALIDATED_NOT_PUBLISHED`. The intended CAS object and R1 binding are absent. | At initial reconciliation, the one known incomplete attempt is identified. While CAS is absent, no R1 binding appears. Keep any owner-approved staged publication or render retry separate from this observation. |
   | B | The exact object and CAS directory are durable, and the R1 binding is absent. Target the first such point, before the `ARTIFACT_DURABLE` attempt update if separately observable, so the test catches recovery that relies only on the state label. | Verify the same CAS object against the prepublication attempt digest and metadata. After the HTTP denial checkpoint below, reconcile once and verify a single R1 binding across two cold reopens. |

   Both cases must preserve R2's exact current revision and audio and the original revision count. The baseline probe preloads the late WAV through `late_request()` and kills at the binding call’s artifact fence. It is a negative control for lost history. The R3 qualification requires observed phase ordering and a real CAS publication.

3. For Crash B, before startup or project-open can reconcile, have the owner-approved test harness pause reconciliation at an observable boundary. Submit the real owner-authenticated WAV GET for the exact late R1 tuple. Require a denial with no WAV bytes and verify the association is still absent. Repeat the pre-reconciliation request with Range if the accessor supports it. On the pinned baseline, `project_operation()` reconciles before reading a revision, so a project open is not a safe precondition check. If startup, project open, or the first GET already reconciled the artifact, the pre-reconciliation case is **BLOCKED** until the owner supplies a phase control. A successful response after that implicit recovery cannot score as pre-reconciliation proof.
4. Release reconciliation, with no render or caller replay. Reopen in two fresh processes. Require exactly one late-artifact binding on R1, unchanged revision identities and count, and the same R2 current ID and output digest. Replay the identical authenticated GET from step 3 with the same principal and project/revision/artifact tuple. Require the exact complete CAS WAV, with the same container SHA-256, format, frame count, and independently decoded PCM SHA-256 as both the staged WAV and the durable CAS object. Compare the original R1 and current R2 responses to their own trusted engine-side identities to catch fallback.
5. Request the same recovered digest as R2, under another project, as principal B against A’s project, and anonymously. Require denial and no audio bytes. Reuse PR #18 for the general matrix. If Range is supported, compare an authorized range to the exact slice of the full WAV and require denial for unauthorized ranges.
6. Record recovery, physical audio validity, musical edit, authorized delivery and browser playback separately. Browser A/B requires the selected artifact at the same musical position.

## November 10 baseline readback

GitHub repository ID `1427534706` resolves to `SARA_studio`. The retained probe was run from a clean checkout of `14e2fb9cc55c8ce2909803a66d509915a18eb625`. Both child processes received SIGKILL. The early window produced R1 binding counts `[0, 0]` across two cold reopens. The later window produced `[1, 1]`. Both preserved R2 and its audio. NASA-006 independently reports the same early failure in `tlspec3.zip` (archive SHA-256 `cb05626acf7b0bde3240a63570989398524ed13b5160d33ceb9d0cd58284799a`). No owner-designated R3 SHA was visible at refresh. No candidate HTTP request was attempted.

Retain prior local PCM and transposition measurements when relevant fixture PCM and edit-event identities match. Rerun measurements that depend on changed bytes or changed render/analysis inputs. A successor with a missing fault seam, accessor, or principal pair stays blocked at the affected boundary. No candidate runtime tests ran for this handoff.

- [Work C recovery evidence and reproducer](https://github.com/justinbusiness461-lab/SARA_studio/pull/17)
- [NASA authenticated HTTP harness](https://github.com/justinbusiness461-lab/SARA_studio/pull/18)

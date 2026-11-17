# M044 Work C successor qualification · 2026-11-10

Sound Forge main `14e2fb9cc55c8ce2909803a66d509915a18eb625` was verified against the live GitHub refs. No successor R3 ref was found. PR #10's merge and existing bounded audio and edit evidence remain applicable to that baseline. No full fixture renders or listening tests were repeated.

| Severity | Finding | Evidence and impact | Owner and next action |
| --- | --- | --- | --- |
| P0 | Early historical recovery FAIL | The retained artifact-fence kill returned SIGKILL. The valid WAV survived, but two cold reopens found zero R1 bindings. R2 revision and output stayed intact. | Bobby repairs ordering. Work B and C rerun the exact successor. |
| P0 | Authenticated delivery BLOCKED | PR #16 is the documented WAV contract. PR #18 retains a live HTTP probe. No implemented R3 WAV path was found for execution. | Bobby supplies the candidate, endpoint contract and authorized fixture. Work C compares served bytes and decoded PCM. |
| Qualification | Prior probe could reject repaired ordering | Its baseline-only assertion required zero pending records at the early kill. The updated probe records that count as telemetry and verifies durable outcomes across two fresh processes. | Work C runs the pinned probe on R3. If either hook moves, inspect the new durability sequence and explicitly remap the fault hook before certifying. |

## Run on a clean candidate checkout

From the candidate root, use the adjacent `m044_r3_recovery.py` from this evidence branch. Pass the full SHA separately from the checkout so the check can reject a mismatched pin.

```bash
PYTHONPATH=tools:tests python3 /absolute/path/m044_r3_recovery.py EXACT_CANDIDATE_SHA
```

The baseline execution exited 1. Early kill yielded R1 counts `[0, 0]` and the later control yielded `[1, 1]`. In both cases the R1 revision, R2 revision, and R2 current output were preserved. A wrong SHA exited 2. A valid successor needs `[1, 1]` at both verified fault points. Count pending records for diagnosis. Certify the actual interval between durable artifact bytes and committed historical association, including when the candidate changes a seam name or removes the old hook. This checks a process kill in the project render-binding path.

For HTTP, reuse PR #18's live qualification harness with independent authenticated sessions. First acquire the admitted R1, late historical R1 and R2 artifact identities from authoritative project history. Compare full HTTP bodies against the corresponding authorized SHA-256, independently decode PCM, and compare frame counts and PCM digests. Require no audio bytes for unauthorized, cross-project, wrong-revision, malformed, or corrupted cases. If ranges are supported, verify returned slices against the same authenticated full object. Keep physical validity, musical edit correctness, and actual browser playback separate. Browser A/B requires the same musical position and the selected revision's bytes.

## Evidence and scope

- Live refs reviewed for main, Bobby and PRs #10, #11, #14, #16, #17, #18. PR #18 QA source inspected at `d2ceeac964aaf8bccd2eb8e6ae92c98bd4b7cf2e`.
- Project archive `tlspec2.zip` SHA-256 `14da3a9efff5c1d267507d4c9aaee53ca70b71711b0168f7a29779211a6e6465` contains the NASA-005 receipt and the Work C physical report. NASA-005's receipt independently reports zero early-recovery bindings at the same Sound Forge SHA. It is supplied evidence, separate from this execution.
- Floot inventory exposed the October 14 PulseForge Visualizer and the October 10 SARA AURUM Runtime Lab. A matching Sound Forge Studio runtime was not established.
- The project transcripts retain GRAVEYARD FREQUENCY as the benchmark. The standalone governance repo and standalone sonic blueprint revisions remain unverified in this run.

## JUSTIN 101

- Changed — Made the recovery probe usable against a successor that persists ownership earlier, and ran it against the known failing baseline.
- Failed or blocked — Early kill still loses the history link on baseline. Successor recovery and HTTP delivery await Bobby's exact candidate and authenticated fixtures.
- Proven — At the retained hooks, baseline early recovery fails, the later control recovers exactly once on each reopen, and R2 remains intact.
- Unverified — Successor behavior, authenticated audio delivery, browser/mobile A/B, listening and deployment.
- Justin action — None.

# Chat D — M044 orphan-CAS playback authorization contract v5
Date: 2026-11-10. Campaign PF-COMPLETION-001. Read-only product-adversary evidence.

## Verified currentness
- Live canonical GitHub repo: `justinbusiness461-lab/SARA_studio`; same renamed music authority, not `dj_rezrxtion`.
- Main: `14e2fb9cc55c8ce2909803a66d509915a18eb625`.
- PR #11 open, head `c4a8d811520b6838063a29daf8e9a36ef4c2cc5c`, old base, no qualified connected audio.
- R3 successor was not located in queried branches/main.
- Physically inspected `tlspec3.zip` → `nasa006-receipt.json`, dated 2026-11-10, identifies NASA-006 19/19 harness self-tests, known-bad main PASS_DETECTS_FAIL and 0/60 R3 stress BLOCKED (no successor). This is supplied archival evidence, not independently rerun engine behavior.

## New executable contract
Test pair of independently captured authenticated GET/durable-state observations of **one exact** late R1 artifact:
1. Before reconciliation: WAV bytes already exist and digest validates in CAS, yet no durable R1 association exists. The service must return denial/not available, **zero audio bytes**.
2. After known-attempt reconciliation: R1 durable history contains that artifact exactly once, and authorized HTTP yields exact matching artifact SHA.
3. Throughout both: R2 remains current; R2 active artifact unchanged; neither historical response alters current authority.

This is a *product truth* check, not Bobby's engine repair, Work B's source qualification or Work C's media decoding.

## Execution
Bundle: `M044_ChatD_Orphan_CAS_Auth_Contract_v5_2026-11-10.zip`.
ZIP SHA-256: `11df571e1a82878b972db0cc3684d646c16fdf3859747394d37ae906e36a78bb`.
Files:
- `orphan_access_contract.py` SHA-256 `8aa115e3c30a8d012c64ff806710e9d863619e02a4e1a6f35ed5278b6fd7c53c`
- `test_orphan_access_contract.py` SHA-256 `98d5c68bca91f78a83b4c629d791bf5a88686bc6ea54bc6419c54be193fb002d`
- `README.md` SHA-256 `fb4280c571fe29e4a448a3ab00fda6d5c428af1618c21e1a7b10c250883604e7`
Executed locally: `python -m unittest discover -s /mnt/data/m044_chatd_v5 -p 'test_*.py' -v` → **9/9 PASS**. Synthetic observations only; real app authorization not tested.

## Findings
- **P0 risk — CAS existence confused for access authority.** Evidence: NASA-006 pre-pending orphan negative control; this is a *required negative test*, not a newly observed unauthorized HTTP leak. Owner: Bobby backend / Work B qualification. Impact: cross-revision/tenant audio exposure if authorization uses digest alone. Blocker: no R3 accessor. Next action: execute pre/post scenario against exact authorized HTTP route.
- **P1 risk — orphan restoration changes current transport or badge.** Evidence: UI regression hypothesis; no production UI yet. Owner: Cody/Work A Studio transport, Chat D negative qualification. Next: verify R2 current selection and output stay fixed through reconciliation and late audio availability.

## JUSTIN 101
WHAT CHANGED: Created a machine-checkable CAS-vs-authorization product test and retained a repo audit.
WHAT FAILED/BLOCKED: Backend R3 candidate and actual authenticated HTTP behavior unavailable.
WHAT IS PROVEN: 9 local synthetic checker tests; source/receipt readback; ZIP digest.
WHAT IS NOT PROVEN: Real two-principal denial, recovered HTTP audio, deployed playback or musical quality.
WHAT JUSTIN MUST DO: Nothing.

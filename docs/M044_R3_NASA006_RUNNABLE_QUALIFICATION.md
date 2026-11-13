# M044 R3 — NASA-006 / Runnable Qualification Evidence

**Qualified product source:** `eac42c4174f95694389077b8a2125bb7c5f2cdfa`  
**PR:** #21  
**Evidence-only update:** this document and adjacent JSON receipts do not modify product behavior.

## NASA-006 endurance

Executed in a fresh isolated environment against the exact qualified source.

- Crash A: **20/20 PASS**
- Crash B: **20/20 PASS**
- Crash C: **20/20 PASS**
- Real SIGKILL trials: **60/60**
- Two fresh-process reopens per trial.
- R2 remained current in every trial.
- Crash A never fabricated R1 history/playback.
- Crash B reconciled the exact durable CAS object to R1 exactly once after fresh reopen.
- Crash C retained exactly one R1 historical association.
- No phantom revision, duplicate R1 binding, or pending orphan survived terminal reconciliation.
- Recovered B/C audio matched exact SHA/byte length and decoded as valid stereo PCM16 WAV.

## Coupled authenticated WAV discriminator

The same Crash-B recovered R1 artifact was exercised through the real HTTP accessor:

- before reconciliation: **403**
- after lawful reconciliation: **200**
- response bytes: exact digest/length match
- wrong principal: **403**
- anonymous: **403**
- wrong revision: **403**
- R2 current authority: unchanged
- R1 historical occurrences: exactly 1

## Negative control / verifier

The original Work B pre-pending reproducer was executed against the canonical baseline source `14e2fb9cc55c8ce2909803a66d509915a18eb625`.

Observed:
- artifact hash valid: true
- artifact decode valid: true
- R2 still current: true
- history occurrences: 0
- pending records: 0
- verdict: FAIL

Therefore the qualification system still detects the known defect.

PR #19 hardened receipt verifier:
- self-tests: **13/13 PASS**
- candidate receipt: **PASS**
- contradictory top-level PASS with `historyOccurrences=0`: **REJECTED** with exit 20

## Evidence ceiling

**PROVEN**
- exact R3 source identity;
- Cody integration review PASS;
- 60/60 SIGKILL endurance across A/B/C;
- association-before-access HTTP behavior;
- baseline negative-control detection;
- hardened receipt-verifier acceptance/rejection behavior.

**NOT CLAIMED**
- Work B human/owner merge approval;
- browser/mobile/device certification;
- listening/creative approval;
- release readiness;
- deployment readiness.

**Disposition:** `R3_TECHNICAL_QUALIFICATION_ADVANCED / WORK_B_OWNER_DECISION_PENDING`

# M044 Bobby R3 — Render Durability Handoff

**Owner:** Bobby 2  
**Base:** `14e2fb9cc55c8ce2909803a66d509915a18eb625`  
**Branch:** `bobby2/m044-r3-render-durability`

## Repair

R3 closes the pre-pending ownerless-CAS crash window by replacing the render path's split:

`render → write CAS → commit association`

with one server-owned publication transaction:

`render bytes → validate → durable RenderAttempt identity/digest/intended CAS → CAS publish → ARTIFACT_DURABLE → lawful revision/history binding`

The pre-existing `pending-renders` recovery remains readable for historical compatibility, but new M044 session renders use `/api/projects/render`.

## States / crash semantics

- `VALIDATED_NOT_PUBLISHED`: exact digest, byteLength, source revision and intended CAS durable; CAS may be absent; no historical playback invented.
- `ARTIFACT_DURABLE`: exact CAS bytes durable; CAS existence alone is not authorization.
- `HISTORICALLY_BOUND`: late historical render associated exactly once with its captured revision.
- `REVISION_BOUND`: current-source render bound through the existing ProjectRevision authority.

Recovery enumerates only known `render-attempts/*.json`; it never scans arbitrary CAS objects to guess ownership.

## Cody acceptance mapping

1. artifactDigest + intended CAS durable before CAS publication — implemented.
2. recovery enumerates known incomplete RenderAttempts only — implemented.
3. Crash A: digest known, CAS unpublished, no invented history — focused PASS.
4. Crash B: CAS published, history unbound, fresh open restores exactly one R1 association — focused PASS.
5. orphan/unbound CAS artifact → authenticated HTTP DENY — focused PASS (HTTP 403).
6. same bytes after lawful R1 reconciliation → HTTP PASS exact WAV — focused PASS (HTTP 200, exact bytes).
7. digest knowledge alone never authorization — focused PASS.
8. R2 current revision/output unchanged through historical reconciliation — focused PASS.
9. requestGeneration remains presentation-only; R3 does not modify project authority/currentness semantics.

## Executed evidence

Independent isolated executor, exact branch source:

- `python3 -m unittest -v test_m044_r3_durability` with inherited `OperationTests`: **16/16 PASS**.
- Actual localhost HTTP evidence inside that run: `POST /api/projects/audio` returns **403** before reconciliation and **200** after, exact WAV bytes.
- `node --test tests/m044-session.test.cjs`: **2/2 PASS** after supplying unchanged `scorecore.cjs` dependency.

## Evidence ceiling

Focused execution only. Full repository regression, NASA-006 20/20/20 SIGKILL campaign, independent Cody diff review, and merge qualification remain unproven.

**R3_PASS_CLAIMED:** NO  
**READY_FOR_CODY_EXACT_DIFF_REVIEW:** YES

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


## Successor hardening — principal → project authorization

Cody's independent review correctly identified that the first R3 candidate authenticated only a process-wide capability and artifact/revision association. It did not prove caller principal ownership of the project.

The successor keeps the R3 durability model unchanged and adds:

- opaque `X-Studio-Session` token;
- server-side session → principal resolution;
- durable `ProjectOwner.json` beside project authority;
- project-owner check before project open/commit/render/audio authority;
- project-owner check before revision/artifact resolution;
- no ownership encoding in CAS;
- no second project/currentness store.

Authorization order is now:

`session principal → ProjectOwner → ProjectManifest/revision history → revision→artifact association → CAS digest/integrity → WAV validation → bytes`

Legacy pre-auth projects may be adopted only by the historical local Studio principal; arbitrary named principals cannot claim unowned legacy state.

### Executed two-principal evidence

Independent isolated executor:

- focused Python suite: **17/17 PASS**;
- Node render-session suite: **2/2 PASS**;
- A → A artifact: HTTP 200 exact bytes;
- B → B artifact: HTTP 200 exact bytes;
- A → B valid project/revision/artifact: HTTP 403;
- B → A valid project/revision/artifact: HTTP 403;
- anonymous → either project: HTTP 403;
- exact identifier knowledge does not alter denial.

### Evidence ceiling

This proves the local server's explicit session/principal/project ownership gate and the focused R3 durability coupling. It does **not** claim an external identity provider, hosted multi-tenant account system, full repository regression, NASA-006 endurance, or merge readiness.

**READY_FOR_CODY_SUCCESSOR_REVIEW:** YES


## Successor hardening — immutable first-owner serialization

Cody's second HOLD correctly identified that first `ProjectOwner.json` establishment occurred before the per-project lock.

### RED

Exact RED commit:

`432a657fdf60efbfb7c0278244ced83e9e15c234`

A deterministic concurrent first-claim test reproduced the defect before repair. Both principals were synchronized at first creation; the unfixed source failed before a lawful single owner could be established, including a directory-creation race.

### Repair

The render durability model and CAS authorization model are unchanged.

A root-level synchronization-only mutex:

`projects/.owner-create.lock`

now serializes:

`projects namespace → project directory creation/existence → ProjectOwner existence check → immutable first owner write`

After ownership is established, the existing per-project `.lock` continues to serialize project mutation.

The mutex is not authority, state, or a second currentness store. `ProjectOwner.json` remains the sole durable project-principal authorization record.

### Concurrent acceptance

Two principals simultaneously create the same explicit projectId:

- exactly one succeeds;
- exactly one receives project-principal DENY/CONFLICT;
- `ProjectOwner.json` equals the winner and remains immutable;
- exactly one ProjectRevision exists;
- ProjectManifest.currentRevisionId equals that winning revision;
- losing principal cannot subsequently open the project.

### Regression evidence

Independent isolated executor, exact source candidate `98177f6184af0a9be2cb9946f48da2aca74ed7a0`:

- focused Python R3/authorization suite: **18/18 PASS**;
- Node render-session suite: **2/2 PASS**;
- repository-documented full Python suite:
  `python3 -m unittest discover -s tests -v`
  → **64/64 PASS**.

The first full-suite materialization initially lacked the committed binary fixture
`evidence/m043/fixtures/rise-higher.wav`, producing 14 fixture-not-found errors.
After the exact committed fixture was staged, the same full command passed 64/64.
This was an executor-materialization defect, not a product source failure.

**READY_FOR_CODY_SUCCESSOR_REVIEW:** YES


## Successor hardening — first-owner crash recovery

Cody's third HOLD correctly identified a crash window after durable project-directory creation but before durable `ProjectOwner.json`.

### Valid RED

Exact valid RED commit:

`a0d51653ac70f706ad14b1d0c13de4f89962dc70`

(The immediately prior test commit had a harness-only missing `import os`; product source was unchanged. The corrected RED above failed for the intended product reason: retrying principal A received `ProjectConflict: project principal denied` after the ownerless directory survived.)

### Repair

The existing `projects/.owner-create.lock` remains the serialization mutex.

A recovery-only claim is now durably written under:

`projects/.owner-claims/<projectId>.json`

before first project-directory creation.

Claim contents are limited to:

- `projectId`
- `principalId`
- `formatVersion`

The claim owns no revision, current pointer, artifact, render, Proof, or project content.

First-create sequence:

`owner-create.lock → durable owner claim → durable project directory → immutable ProjectOwner.json → verify owner → delete claim → fsync claim namespace → normal per-project .lock → project mutation`

Recovery behavior:

- directory absent + matching claim + same principal → resume first creation;
- directory present + owner absent + matching claim + same principal → finish owner establishment;
- matching projectId + claim owned by another principal → DENY / CONFLICT;
- existing owner → normal immutable owner check;
- ownerless legacy directory + no claim → existing fail-closed policy remains; named principals cannot adopt it.

### Executed evidence

Independent isolated executor, exact repaired source candidate `23cb4228b198919a7ba84841fbb9241311dde6ec`:

- focused R3/authorization/crash-recovery Python suite: **19/19 PASS**;
- repository-documented full Python suite:
  `python3 -m unittest discover -s tests -v`
  → **65/65 PASS**;
- Node render-session suite: **2/2 PASS**.

Crash-recovery acceptance proved:

- process dies after durable project directory exists but before `ProjectOwner.json`;
- fresh process, same principal A retries and succeeds;
- `ProjectOwner.json = A`;
- exactly one revision exists;
- `ProjectManifest.currentRevisionId` equals that revision;
- principal B is denied;
- ownerless legacy directory with no recovery claim remains denied to named principal.

R3 render durability, CAS authorization, two-principal steady-state isolation, and first-owner concurrency behavior remain unchanged and green.

**SECOND_AUTHORITY_CREATED:** NO  
**READY_FOR_CODY_SUCCESSOR_REVIEW:** YES

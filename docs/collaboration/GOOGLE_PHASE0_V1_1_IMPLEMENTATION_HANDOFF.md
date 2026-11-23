# Google Engineering Handoff — S.A.R.A. Collaboration Fabric V1.1 (FROZEN)

**Status:** ARCHITECTURE FROZEN; CONTRACT / RED WORK ONLY; NO LIVE COLLABORATION CERTIFICATION.
**Repo:** justinbusiness461-lab/SARA_studio (ID 1427534706); **review base main:** `d6aa889a0def72bb8e1c87009a98d6c29e47067e`; **captured:** 2026-11-23.
**Constitution:** AN AUTHORIZED PROPOSAL IS NOT AN AUTHORIZED COMMIT.™
The room owns relationships; the existing Studio project/revision/manifest owners own music. Realtime events never elect a current revision. S.A.R.A. operates as the requesting principal.

## Exact observed reuse hooks on this pinned SHA

| Rightful owner | Exact source | Decision |
|---|---|---|
| Studio local principal | `tools/studio_server.py:37-59` in-memory `SESSION_PRINCIPALS`, `resolve_studio_session` | Reuse behind external authenticated principal; local token is **not** hosted multiuser proof. |
| Immutable first owner | `tools/studio_server.py:147-225` `ProjectOwner.json`, `.owner-create.lock`, `.owner-claims` | Never overwrite or bypass existing owner; grant read/edit scopes through rightful grant issuer. |
| Canonical revision/CAS | `tools/studio_server.py:717-889` `project_operation`, `.lock`, `ProjectManifest.currentRevisionId` | Extend **one** Studio commit gateway with semantic admission; preserve expectedCurrentRevisionId CAS. |
| Stable operation replay | `tools/studio_server.py:753-813` `operationId` and meaning digest | Reuse idempotency and authoritative reread after uncertain ACK. |
| Render durability | `tools/studio_server.py:466-641` render attempts and durable binding | Private candidates are not approved/current; never scan unbound CAS for authority. |
| Media access | `tools/studio_server.py:642-664` `project_audio_bytes` | Principal → lawful membership/revision → bound artifact → integrity → PCM validation → bytes. |
| API adapter | `tools/studio_server.py:921-1043` `StudioHandler` | Use existing Studio endpoints; fail closed when collaboration authority unavailable. |
| UI and score | `app-ui.js`, `app-core.js`, `scorecore.js` | Browser draft and request-generation remain non-authoritative. |
| Regression seeds | `tests/test_project_authority.py`, `tests/test_m044_operations.py`, `tests/test_m044_r3_durability.py`, `tests/r2-ab.browser.cjs` | Extend existing Python unittest/Node test conventions. |

**Missing / not verified from Studio source:** `CollaborationRoom`, `CollaborationGrant`, approval issuer, `rightsGeneration`, `authorizationGeneration`, project generation counter, durable collaboration outbox. These may exist in **other rightful repositories**. Do not convert an uninspected source into a claim of nonexistence. **EXECUTOR_VANTAGE_MISSING=authoritative identity/Explore/room/grant/rights repo+issuer contract.**

## Required target semantic transaction

```ts
interface SemanticCommit {
  operationId: string; projectId: string; baseRevisionId: string;
  expectedProjectGeneration: number; actorPrincipalId: string;
  candidateArtifactIds: string[]; semanticWrites: unknown[];
  dependencyReads: unknown[]; requiredGrantIds: string[];
  requiredApprovalIds: string[]; authorizationGeneration: number;
  rightsGeneration: number; idempotencyKey: string;
}
type ConflictVerdict = "COMMUTES"|"DETERMINISTIC_REBASE"|"REVIEW_REQUIRED"|"REJECT_STALE";
type CommitFailure = "STALE_REVISION"|"AUTHORITY_REVOKED"|
 "APPROVAL_INVALIDATED"|"DEPENDENCY_CHANGED"|"ARTIFACT_IDENTITY_CHANGED";
```

Types are an **admission target**, not a declaration that these fields are implemented. Studio must check the trusted principal, current grants, approvals, rights, candidate digest, dependencies and revision *at the commit boundary*. For external grants/rights, require a demonstrably linearizable fence or fail closed; a two-stage read alone is not a distributed atomic transaction.

Logical lifecycle: `PROPOSED → ADMITTED → EXECUTING → CANDIDATE_CREATED → AWAITING_APPROVAL → COMMITTING → COMMIT_ACK_UNKNOWN → RECONCILING → COMMITTED → REBROADCAST`. The state list does not require every transition. `REBROADCAST` does not establish all-client convergence; clients reread canonical Studio state. Hold states and operation receipts remain under existing owners.

**No silent auto-merge:** separate tracks do not prove independence when tempo, sidechain, bus, reverb, routing, stretching, arrangement or automation can couple them. A safe rebase must preserve musical invariants and historical identity.

## COL-001…028 RED fixture implementation inventory

All below are **specified acceptance scenarios; none is claimed executed**. Create actual deterministic RED tests with a real owner adapter before any GREEN claim. Preserve distinct test IDs and exact SHAs.

| Case | Required negative or positive assertion |
|---|---|
| COL-001 | Two authorized principals join a room; identities remain separate. |
| COL-002 | Cross-tenant private room subscription/message read DENY. |
| COL-003 | Revoked member cannot obtain subsequent media/project access. |
| COL-004 | Shared audition requires exact authorized artifact and musical position. |
| COL-005 | Reconnect rereads current Studio revision; session has no current authority. |
| COL-006 | Concurrent edits merge only after proven commutativity or safe rebase. |
| COL-007 | Conflicting edits must not silently overwrite. |
| COL-008 | Late R1 response cannot replace newer selected/current R2. |
| COL-009 | Revision acceptance cannot imply commercial rights clearance. |
| COL-010 | Shared S.A.R.A. acts as requester; denied scopes stay denied. |
| COL-011 | Lost commit ACK recovers original operation by readback. |
| COL-012 | Both principals cold reopen lawful revision and decode same audio. |
| COL-013 | Revoke edit grant after candidate before commit => HELD_AUTHORITY. |
| COL-014 | Revoke during media/AI job => no new unauthorized access/publication. |
| COL-015 | Duplicate delivery/lost ACK => at most one canonical operation. |
| COL-016 | Two CAS writers same revision => one current promotion. |
| COL-017 | Different tracks with shared tempo/bus => no unproven auto-merge. |
| COL-018 | Room prompt injection cannot export foreign project. |
| COL-019 | Voice-model operation denied absent exact performer/asset/purpose consent. |
| COL-020 | Oversized/mislabeled/digest-mismatched media rejected/quarantined. |
| COL-021 | Accepted song revision without license => commercial release still denied. |
| COL-022 | Crash after pointer promotion before rebroadcast => recover event, no recommit. |
| COL-023 | Artifact identical but musical sample position different => audition FAIL. |
| COL-024 | Candidate B replacing A invalidates A-specific approval. |
| COL-025 | Revoked signer/policy change before commit => approval held. |
| COL-026 | Realtime provider outage => no change in Studio history/current. |
| COL-027 | Cross-room/project media/subscription mismatch => DENY and audit. |
| COL-028 | Offline stale edit => private candidate/HELD_STALE, no promotion. |

First Phase 0 RED candidates: COL-013/015/016/024/025. COL-024 is a later-phase business workflow but its immutable approval identity is a Phase 0 precondition. Existing CAS test coverage may be reused as a seed for COL-016, **not** relabeled collaboration proof.

## Smallest lawful patch ordering

1. **OWNER_MAP:** locate true identity, room, grant, rights/consent owners and authenticated test principal. Pin exact repo/branch/SHA/PR heads and publish absent/unseen boundaries explicitly.
2. **CONTRACT:** version `NetworkPrincipal`, `CreatorProfile`, `CollaborationRoom`, `RoomMember`, `RoomProjectBinding`, `CollaborationGrant`, `CollaborationOperation`, `SessionState`, `CollaborationDecision`; extend rightful issuer contracts rather than inventing Studio DBs.
3. **RED:** implement 28 acceptance tests at correct owner adapters; first reproduce five P0 critical gates and capture exact error trace, fixture identity and negative controls.
4. **PHASE 0 STUDIO:** narrowly extend `project_operation` admission while retaining existing project lock, manifest CAS, immutable revisions, replay digest, render attempt, and media read owner. If no atomic grant generation fence exists, HOLD.
5. **RECOVERY:** durable operation intent/outbox within Studio operation lifecycle; crash injection before/after commit pointer; readback by operationId prior to retry.
6. **SCOPED NO-OP:** two authenticated principals, one room binding, one existing project, one no-op private candidate; prove zero musical revision change. Only later permit narrow edit and provider transport.
7. **VERIFY:** full existing Studio Python/Node/browser regressions; cross-tenant DENY; two-client cold reopen; physical artifact/position check independently qualified. Separate creative and commercial approval gates.

**DO NOT CREATE:** ProjectRevision2, ProjectManifest2, SongSpec2, ProductionTimeline2, Rights2, ApprovalAuthority2, Proof2, CASScanOwnership, room-owned music, realtime-owned current revision, browser-owned canonical currentness, DriveProjectTruth, duplicate render authority, global musical CRDT, or a provider-locked project model.

**Return:** exact base+PR SHAs; source-to-contract map; smallest diff paths; real RED/GREEN receipts; concurrency/revocation/ACK fault traces; authoritative post-state; proof tier; missing issuer owner+edge+wake condition. Stop on uncertain effect; no blind retries.

## JUSTIN 101

**WHAT CHANGED:** Pinned implementation map and all 28 adversarial cases in a reviewable contractor source note, without product-source edits.
**PROVEN:** Source map inspected via connected GitHub; architecture freeze reflects owner instruction.
**UNPROVEN:** Current external collaboration provider and authority, executable RED behavior, hosted two-principal approval, physical audition.
**TEAM NEXT:** Google find owner APIs, author real RED tests, implement the smallest owner-correct Phase 0 diff; independent QA qualify.
**JUSTIN ACTION:** None.

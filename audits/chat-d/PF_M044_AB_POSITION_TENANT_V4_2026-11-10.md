# Chat D — M044 A/B Musical Position and Project Identity v4
Date: 2026-11-10. Status: **HARDENING_ADVANCE**. Owner: Chat D, read-only product adversary. No product-source change.

## Refreshed source and access
- Sound Forge `justinbusiness461-lab/pulseforge-songforge` main: `14e2fb9cc55c8ce2909803a66d509915a18eb625`; PR #10 merged.
- PR #11 open, still based on old Bobby branch; PR #17 open Work C physical/crash evidence; PR #18 open NASA-004 test harness.
- Local project sources: `Sara studio 5.txt`, `Sara studio 6.txt`, `Sara studio 7.txt`, `S.A.R.A (3).md` accessed and scoped. Other source material uninspected, NOT declared absent.
- Actual Studio browser execution and authenticated live WAV access NOT evidenced here.

## First new adversarial edge
Previous v3 checker tested request generation and selected revision/artifact. It did not demand an *identical musical position* during R1/R2 A/B, nor reject a nominally valid artifact from a different project. Result can be technically valid WAV and still misleading to musician or unauthorized by tenant.

## Machine-checkable supplemental contract
`M044_ChatD_AB_Position_and_Authority_v4_2026-11-10.zip`, SHA-256 `6e335229e5748cb782955a056953b97c9ad5504eccaa6a1a7ebe22f5e466bc29`:
- `m044_position_auth_contract_v4.py` SHA-256 `7f2fa7a2e4ae03d223fe6799f9329a3bf98f37408231e2559574ec050b73b0bf`
- `test_m044_position_auth_contract_v4.py` SHA-256 `44bf277d7dcb579ff584e1e0b1b7271c68efb2e95f1a675b480a6f683c99ed50`
- Includes v3 checker for context, README and direct interpreter instructions.

Test cycle: initial RED from missing v4 checker module, then GREEN **9/9** focused synthetic unit tests. Verified ZIP integrity PASS. Tests: aligned A/B; wrong beat; foreign project; wrong artifact; unavailable B without fallback; false fallback; changed timeline without verified alignment; changed timeline with verified alignment; foreign history revision.

The checker DOES NOT authenticate a real user session, decode the WAV, or prove actual player behavior. These must be proven independently with real artifacts and browser/network receipts.

## Findings
| Severity | Evidence | Owner | Impact | Blocker | Next action |
|---|---|---|---|---|---|
| P1 (coverage gap, locally addressed) | v3 did not check musical-position/tenant fields; v4 9/9 synthetic PASS | Chat D | deceptive A/B at different beats or mixed projects | real observations absent | exercise v4 on connected Studio |
| P0 (known current-main regression, external independently reported) | Work C PR #17 and Manus NASA-005 report pre-pending crash after artifact durability | Bobby/Work B | valid R1 WAV may be orphaned | exact repaired successor missing | TDD repair and independent early-crash requalification |
| P0 (application integration gap) | PR #16 contract only, PR #11 older stack | Bobby/Work A | browser cannot retrieve authorized project/revision WAV | authenticated accessor not proven | implement owner-native read bridge, qualify with 2 users |

## JUSTIN 101
WHAT CHANGED: Added v4 executable A/B musical-position and project-identity observation checks; 9/9 focused synthetic tests passed; evidence report retained.
WHAT FAILED/BLOCKED: Connected UI and authenticated WAV stream unavailable in this vantage; early crash bug separately reported on main.
WHAT IS PROVEN: Local contract checks, archive hash/integrity, refreshed PR/head metadata.
WHAT IS NOT PROVEN: Real Studio tenant authorization, A/B musical alignment, playback, full-song listening or production readiness.
WHAT JUSTIN MUST DO: Nothing. Wake Chat D on Bobby/Work B application SHA and live Work C audio evidence.

# Mission 044 — Work B independent runtime qualification (PR #22)

## Identities

| Field | Value |
|-------|--------|
| **TARGET_SHA (candidate)** | `91ed45f67f8c0bd432a7f4afb5de7a9ebe1dbdf5` |
| **PR #22** | MERGED |
| **MERGED_SHA / M044_MAIN_SHA** | `1ea3909a25a2365862bd6a1106cfb386d933a504` |
| Candidate is ancestor of main | YES |
| `app-ui.js` SHA-256 | `90b683b4096353975660511ed06e9ff21d088fafc240dc7fc69b8b3c70f67867` |
| `tools/studio_server.py` SHA-256 | `96048d39ef5a6422e44c2bf507043930c19dc0aace01d35df57097db1075c06e` |

## Independent clean-room execution

Fresh clone of `justinbusiness461-lab/SARA_studio` @ main tip containing `91ed45f`.

| Suite | Result |
|-------|--------|
| Python unittest | **66/66 PASS** |
| Node unit (scorecore / session / prompt-ui) | **11/11 PASS** |
| R1 playback browser | **3/3 PASS** |
| Generate / PWA browser | **2/2 PASS** |
| R2 / A-B browser | **4/4 PASS** |
| R2 cold reopen browser | **1/1 PASS** |

### Discriminators exercised

- Verse 2 Bass −12 only; non-target SongSpec conserved
- R2 becomes current; R1 remains historical / playable
- A/B selects exact revision-bound WAVs
- Musical position preserved: `\|fromPositionSec − toPositionSec\| ≤ 0.05` (≤ 50 ms)
- Late R1 response cannot replace newer R2 selection
- COMPLETE only after transport + playback Proof + A/B Proof + artifact + position agree
- Cold reopen: R2 current, R1/R2 history and exact WAVs retained
- Generate does not enable Play until verified revision-bound WAV
- Audio retrieval failure never presents Generate as playable

```text
WORK_B_R2_RUNTIME = PASS
TARGET_SHA = 91ed45f67f8c0bd432a7f4afb5de7a9ebe1dbdf5
MERGED_SHA = 1ea3909a25a2365862bd6a1106cfb386d933a504
M044_MAIN_SHA = 1ea3909a25a2365862bd6a1106cfb386d933a504

R2_EDIT = PASS
R2_PLAYBACK = PASS
R2_CURRENT_AFTER_RESTART = PASS
R1_HISTORICAL_AFTER_RESTART = PASS
R1_WAV = PASS
R2_WAV = PASS

A_B_REBUILDS_FROM_BACKEND = PASS
A_B_COMPLETION_CONSISTENCY = PASS
A_B_POSITION_DELTA_MS = <= 50

LATE_R1_REPLACES_R2 = NO
STALE_PROOF_REPLACES_CURRENT_PROOF = NO
SILENT_FALLBACK = NO

DUPLICATE_R1_BINDINGS = 0
DUPLICATE_R2_BINDINGS = 0
PHANTOM_PROJECT_REVISION = 0

MERGE_AUTHORITY = EARNED (already merged prior to this receipt)
```

## Not claimed

Human listening / GRAVEYARD FREQUENCY score, hosted deployment, Manus NASA-007 endurance, full musician golden-journey UX polish, neural vocals, Sample Creator production integration.

Next serial edge: product golden journey on main + C/D/Manus/Runnable physical attack.

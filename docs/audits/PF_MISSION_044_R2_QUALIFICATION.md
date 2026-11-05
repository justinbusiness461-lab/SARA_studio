# Mission 044-R2 — Work B independent qualification

**Target:** `9f200d5e3b45494cca4f46728cc9e3e8a64766fc`  
**Branch:** `bobby/m044-scorecore-foundation`  
**PR:** #10 (still draft at qualification time)

## Source authentication

| File | SHA-256 |
|------|--------|
| `tools/studio_server.py` | `f2707c42cbce9b1958cf9bf64af95b1557005bfe40ec6f6ca113b0de9ea947a8` |
| `tests/test_m044_operations.py` | `105a9ee076416ef7476c12c3108f3c6985ced784f47b79d9937ef421ed4bbf1e` |

Full module present. No PLACEHOLDER / loader-only reconstruction.

## Independent results

| Suite | Result |
|-------|--------|
| Python | **46/46 PASS** |
| Node | **8/8 PASS** |
| Integration probe | **19/19 PASS** |

Includes:
- `test_malformed_historical_wav_rejected` (garbage / truncated / bad channels)
- `test_crash_before_history_bind_recovers_without_replay`
- `test_late_render_binds_historical_artifact_to_r1`
- late R1 race, locality outside=0, cold reopen, real 10.5s PCM16 WAVs

## Gates

```
INVALID_WAV_REJECTED = PASS
DISTINCT_LATE_WAV = PASS
LATE_R1_BOUND_TO_R1 = PASS
CRASH_RECONCILIATION = PASS
R2_CURRENT_UNCHANGED = PASS
AUDIO_ADMISSION = PASS
LATE_R1_HISTORY = PASS
REAL_AUDIO = PASS
```

```
M044_VERTICAL_SLICE_QUALIFIED = PASS
PR10_HEAD = 9f200d5e3b45494cca4f46728cc9e3e8a64766fc
```

**Merge still requires undraft of PR #10.** This receipt does not move main.

After merge, set `MERGED_SHA` / `M044_MAIN_SHA` on reread of main.

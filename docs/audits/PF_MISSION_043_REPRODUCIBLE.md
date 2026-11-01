# Mission 043 — Runnable R-010 clean reproducibility

**Freeze only:** `076aed8d438a938119a7c2d5b34bb5eeb3ba4409`  
**Release:** 2.20.0  
**Environment:** Linux, Python 3.12, fresh `git clone` + checkout freeze SHA

## Steps executed

1. Checkout exact freeze SHA
2. Verify fixture file + **decoded PCM SHA-256** `4746aca332f19dfc72e45383a75e7a876f6c8e09f8e5b10df149725441a051bb` (PASS)
3. `python3 -m unittest discover -s tests -v` → **35/35 PASS**
4. `python3 tools/m043_probe.py` → **25/25 lyric HTTP/restart checks PASS**

Probe cone includes: guided-align R1, TEXT_ONLY correction R2, persist, process restart, reopen R2 current, R1 retained, AudioDigest unchanged, stale reject, instrumental negative.

## Model-rerun path

`test_no_replacement_of_corrected_truth` exercises human correction not overwritten by later candidate. Full "ASR model rerun API" is **NOT_APPLICABLE_TO_CURRENT_GUIDED_ALIGNER** (scope is supplied-text alignment).

## Result

```
M043_REPRODUCIBLE = PASS
TEST_COUNTS = 35 unit + 25 lyric HTTP/restart
EVIDENCE_LOCATION = docs/audits/PF_MISSION_043_REPRODUCIBLE.md + evidence/m043/*
ENVIRONMENT_IDENTITY = freeze 076aed8 on clean clone
```

No product over-claim beyond reproducibility of bounded guided lyric authority.

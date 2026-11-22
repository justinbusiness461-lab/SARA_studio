# S.A.R.A. Studio™ · Engineer #1 Round 17 — Execution and Governance Receipt

**Issued:** 2026-11-21. **Exact fresh verification:** 2026-11-22.
**Canonical owner:** `justinbusiness461-lab/SARA_studio`.
**Branch:** `feat/platform-identity-and-catalog` · draft PR #37 · **unmerged**.
**Verified exact product HEAD (including offline security repair):** `7dc7a7c31a7786363a62ead3d1581cd14210e4b3`.
**Round17 implementation source:** `702d4775c7fb9c353990897b3f49735b0abe6f98` (subsequent single-use-container/test commits `06965fd...`, `0e1dae...`; privacy repair `7dc7a7...`).
**No deployment, real Modal API calls, live SoundCloud calls, music-provider spend, main merge or cinema repo mutation.**

## Delivered (R17-A)
- `deploy/modal_acestep.py`: `gpu="L40S"`, `timeout=120`, `startup_timeout=110`, `scaledown_window=30`, `min_containers=0`, `max_containers=1`, `single_use_containers=True`, `retries=0`; the web-server startup is bounded at 100 seconds. Controls are **source configuration**, not a physically verified provider runtime.
- `tools/m045_modal_live_client.py`: host-owned `ModalFunctionCallSupervisor` requires an exact existing GenerationAttempt stage, source revision, project, principal and durable call ID. `cancel_remote_attempt(...,terminate_containers=True)` requests termination on simulated timeout/HTTP 5xx/abort. `poll_remote_attempt()` checks `get(timeout=0)` without resubmission; cold restart and cancellation ambiguity stay unverified pending independent provider readback.
- Untrusted/prebound or wrong-attempt call IDs are rejected before the localhost socket. Cancellation intent crosses a durable write boundary before dispatch. A successful simulated cancel is `CANCEL_DISPATCHED_UNVERIFIED`, never `GPU_TERMINATED`.
- L40S published list-rate GPU-only reference ([Modal pricing](https://modal.com/pricing)) `120s × $0.000542/s = $0.065040`; with 30 seconds hypothetical idle tail, `$0.081300`. This is **NOT** an enforceable $1 total cap: real runtime, billing category, startup, concurrent/multiple inputs, warm container and cancellation timing remain qualification gates. **Live Modal HTTPS remains disabled and `Gate3SpendAuthorizationToken` remains `DRY_RUN_ONLY`.**

## P0 source-security finding — locally reachable offline navigation
The first complete isolated Chromium run returned **32 PASS / 1 FAIL**: the browser was reported offline, but its service worker still fetched the localhost server's **credential-bearing online HTML** instead of cached sanitized offline HTML. The original offline-security test reproduced RED independently; diagnostic response had status 200 from the worker and included bootstrap *variable names* in its document (no bearer values copied to this receipt). Merely adding `fetch(...,cache:'no-store')` did not fix it. The smallest successful repair checks `self.navigator.onLine === false` before navigation and serves only the sanitized CacheStorage shell; existing network-failure fallback remains unchanged. Original test assertion, timeout and offline behavior were **not weakened**. Final full browser regression was rerun after the fix, and the initial red proof is retained. This is a **Studio owner** privacy repair; no cinema code changed.

## G15-001 — historical receipt reference resolved (R17-B)
**Exact resolving immutable Git commit:** `1bd7822436ce19a428e8da368b756fe7256f2136`.
- Round15 receipt: `docs/platform/PLATFORM_ROUND15_ENGINEER1_RECEIPT_20261121.md`, exact Git blob `cf91e8f03a529d606bfb4af1eae58efbe738b1eb`.
- Round15 manifest: `docs/platform/evidence/kernel_20261121_round15/execution.json`, exact Git blob `f560a3ecaf5a845917ba619dff9fc02fcdfc4f86`.
Both historical blobs were independently retrieved and matched; no history rewritten.

## Exact-product execution (R17-C)

| Verification | Observed result |
|---|---|
| Complete Python `unittest discover` | **624/624 PASS**; exit 0; 813.582s; skipped 0 |
| Complete Node unit suite | **51/51 PASS**; independently reproduced 51/51; exit 0; fail/skip/cancel 0 |
| Independent serial Playwright Chromium | **33/33 PASS**; exit 0; fail/skip/cancel 0 |
| All configured executions | **708/708 PASS** |
| New Round17 scoped cancellation tests | 14/14 PASS; independently reproduced 14/14 PASS |
| Deployment RED → GREEN | isolated 600s/60s legacy configuration RED; committed 120s/30s/one-input candidate GREEN |
| Source provenance | Exact GitHub archive CRC PASS; source SHA-256 matched; full raw byte readback after evidence commit required |

Logs were recorded in `docs/platform/evidence/kernel_20261122_round17/`, with SHA-256 digests and sizes in `execution.json`. Prior KERNEL session expired before original RED logs could be retrieved; the disposable fault-reproduction logs are clearly labeled, not passed off as original outputs.

**Independent existing DAW physical verification:** `{'peakRssKiB': 453884, 'sha256': '246948c6e75eba588ed06f7d88d8e8a9520600cae2b93791bb58879553e90041', 'state': 'VERIFIED_UNMODIFIED_BUNDLE', 'zipBytes': 222269212}` in the complete Python log; this is **not** actual ACE-Step music inference or an artist listening certificate.

## HOLD / remaining independent owner controls
1. Provider-side actual billing limit and independently read-back total spend, including overhead, retries, and late termination. A single-reference GPU-rate multiplication is **not authorization or certification**.
2. Actual Modal `FunctionCall` spawn/cancel relationship to web server execution: no real call-ID issuance, actual `cancel()`, billing shutdown, or container termination was executed in Round17.
3. Host-only principal/auth/billing/checkpoint rights integration and production readiness, native store/device acceptance, full music source qualification, human audition/creative approval, and SoundCloud release remain **HOLD**.

## JUSTIN 101
**WHAT CHANGED:** Bounded container source configuration, durable owner-bound Modal `FunctionCall` cancellation/polling mechanism and regression tests; G15-001 evidence provenance verified.
**FAILED:** The first full Chromium run detected offline credential isolation (32/33), reproduced in isolation and repaired in Studio. It is disclosed in the RED proof. Final independent browser replay passed 33/33 without test changes. No live-provider cancellation was performed.
**PROVEN:** 708/708 configured test executions on `7dc7a7c31a7786363a62ead3d1581cd14210e4b3`, 2/2 Round15 historical blob readbacks, simulated no-retry controls, source policy checks.
**UNPROVEN:** Total real cloud bill ceiling, real container cancellation and runtime behavior, actual generated audio quality, human creative approval, final production authorization.
**TEAM NEXT:** Governance audits real billing cap and a separately host-issued cancellable Modal call ID, including timeout race, unexpected remote completion, and durable cancellation receipt; complete rights/source and security signoff.
**JUSTIN ACTION:** No merge, payment or live authorization now. Release stays HOLD.

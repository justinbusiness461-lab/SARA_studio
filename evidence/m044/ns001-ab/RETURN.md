# NS001-STUDIO-AB-FAILURE-TRUTH

Flight 001A, implementation return. Owner is Night Work Chat in SARA_studio (1427534706). Next owner is Night Lead for independent qualification. Justin action is none.

| Identity | Value |
|---|---|
| Order in dj_rezrxtion | 3c5fac40efb8beb9be77e60b370163df3a742c21 |
| Studio main used for RED | d6aa889a0def72bb8e1c87009a98d6c29e47067e |
| Diagnostic PR 25 | 20c19ceec10f115e7518fd72e5c28847ff4fc80c |
| Implementation branch | night-work/ns001-studio-ab-failure-truth |
| Tested candidate commit | e2a3991facb1b6863d378dc8a22e7a2307fb13f6 |
| Exact tested product and test tree | e0700d0a57149211e3ec36e6b8092b2bf81a3e7d |
| app-ui.js SHA-256 | 6e8c6c56e52ff16b6e11ccdc8167beedae52f8ea5f2d1fa71278028e9a81844b |
| service-worker.js SHA-256 | 46dabbfb96f2dece5fac5a981916a2ca30ecb51ba54b189ea0bcbfcc8b954803 |
| tests/r2-ab.browser.cjs SHA-256 | 93b7a9cef606275db8358d5c85f514b7052a7222fe28287a0e98dc0cad2ebdfa |

## Observed behavior

On the exact main baseline, PR 25's diagnostic independently reproduced two stuck switches. Six new browser cases went RED using the same test bytes subsequently executed on the candidate. The candidate invalidates old A/B proof and the selection label before its first await. The active switch either publishes both proofs together or publishes FAILED and disables Play. The retry origin is scoped to the R1/R2 pair. Pending media stays private until the actual seek settles within the existing 50 ms tolerance. A stale request discards its own media. The service worker cache version advances so installed clients can retrieve the repaired script.

| Requirement | Executed evidence |
|---|---|
| N01/N02 | Open or audio HTTP 503 after a successful selection switches to FAILED, clears both proofs, and disables Play. |
| N03 | An injected active verifier returning false produces the same failed terminal state. |
| N04/N05 | A held request invalidates the old proof and selection immediately. A newer R2 at 3 s succeeds. Releasing the older request as a failure preserves the entire recorded success snapshot. |
| N06 | A valid response for another revision fails. A real decoded WAV with an injected browser setter that seeks to 0.99 s instead of the requested 3 s fails. Removing the injection and retrying restores 3 s within tolerance. |
| P01 | Real R1/R2 WAV verification, playback start, same-position selection, and consistent COMPLETE proofs pass in headless Chromium. |
| P02 | A fresh server and browser recover current R2, historical R1, both WAV identities, and A/B. |
| P03 | After the failures and retries, backend readback still identifies R2 as current and lists the original single artifact on each revision. |

## Replay

Use Node 24.22.3, Python 3.12.14, npm ci, Playwright 1.57.0, and a local Chromium executable. Set NODE_PATH if Playwright is installed separately. Set CHROMIUM_PATH to the browser binary. The distribution Chromium 156 launcher was refused a local socket before page startup. The completed browser runs used Chromium headless shell 153.0.8010.0 from @sparticuz/chromium 153.0.0, installed outside the repo. Browser tests start their own HTTP servers on loopback, generate local projects and WAVs, and exercise the Studio UI.

    PYTHONPATH="$PWD/tools" python3 -m unittest discover -s tests -v
    node --test tests/*.test.cjs
    node --test --test-concurrency=1 tests/*.browser.cjs
    node --test --test-name-pattern='A/B failures and retries' tests/r2-ab.browser.cjs

For RED, use an isolated checkout of the main SHA above and copy only the candidate tests/r2-ab.browser.cjs into it. Run the last command. PR 25's unchanged diagnostic can also be run with the baseline checkout as its argument. All WAVs are generated in per-test temporary projects. The reopen tests calculate and compare artifact digests at runtime.

Python passed 66/66 with tools on the import path. Without that path, the same child-process import failed in two discovered instances. Node passed 11/11. The browser runner reports 17/17 including one parent test, six new subtests and ten existing tests. The first full run logged a server-side missing temporary file and disconnected client around the R1 reopen test. An isolated four-test replay of R1 playback and R2 cold reopen passed with a clean log. See SHA256SUMS for the raw evidence.

## Review and rollback

Proof ceiling is source-tested and locally executed in headless Chromium. Human listening, physical phone input, hosted deployment and independent Night Lead qualification are open. First outstanding gate is independent readback and replay of the candidate SHA. The lead can run the four commands above and repeat the wrong-position and late-failure controls. No music, revision, server or cinema source changed. Roll back the code candidate by reverting its single implementation commit. For already installed clients, use a fresh service-worker cache version when distributing a rollback.

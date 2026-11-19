# Night Work Z · Concurrent project reopen

November 19, 2026 ET. Studio PR #31. Independent review belongs to Night Lead.

## Exact source

- Studio main at intake was d6aa889a0def72bb8e1c87009a98d6c29e47067e.
- Baseline PR #31 was 51b928e653896bf2558748f8967b05bd7798146e. Its app-ui.js blob was db0220fceb9ef61076e5b1149802ccf3bc8b4c92.
- Independent order and RED came from PR #32 at c0c3cbab65156dd5e5d80da49406c7fbbd060f9e.
- Tested implementation is c636d42f5d00d65591cb1ee1deb7f6a4ec6c6249. Its tree is 43ce0a1e898167a0cce96b6fa8437e5089a54e2a and its app-ui.js blob is b1459e23966ea419cf2f00c4a48063fd75ba4636.

## Behavior

Open and Restore share one browser selection counter. Each invocation clears prior playback and comparisons synchronously. New Project also invalidates outstanding opens. Only the winning request can update the score, project address, labels, transport, A/B inventory, or Proof. The handler checks the returned project and revision, stages the verified WAV, checks historical lookups, and publishes the WAV and comparison pair together. Superseded staged audio is released. A current error leaves Play disabled and reports the failure. The backend continues to own all revisions and audio associations. The service-worker cache name advances for the changed client.

## What ran

| Check | Previous head | Tested implementation |
| --- | --- | --- |
| PR #32 exact-function assertions | Sequential control passed. Both races failed. | Three passed using the original assertions with the staging-aware dependency fixture. |
| Chromium project-open regressions | All eight new checks failed. Two prior delayed A/B controls passed. | All eight new checks and both prior controls passed. |
| Complete Chromium suite | See earlier PR #31 evidence | 28 entries passed, including parent suites and fresh browser/server recovery of R1 and R2. |
| Complete Node and Python suites | See earlier PR #31 evidence | 14 Node tests and 66 Python tests passed. |

Real Chromium projects and authorized WAVs were generated against local Studio HTTP servers. Browser routing delayed an initial open, an audio response, or an ancestor lookup. Each delay was released as success or failure after opening B. Additional checks cover New Project while A is outstanding and failure of the current request followed by recovery. The snapshots include actual verified transport, Proof, saved address, rendered status and revision controls.

The original PR #32 test double always published decoded audio directly. The new fixture models the production verifier's existing staging argument, publication callback and selection counter. Its three original outcome assertions are preserved. Both fixture versions were executed against the baseline and reproduced the same two failures. See qa-red.log and qa-compatible-red.log.

The first suite run passed 27 of 28 entries. The fresh R1 test read Proof immediately after the HTTP body arrived. Private staging put an additional history lookup before publication. The raw run is preserved in browser-first-run.log. The test now waits for the user-visible verified status and then performs the original identity, WAV digest and Play assertions.

## Independent replay

Use Node 24, Python 3.12, Playwright 1.57.0 and Chromium headless shell 153. Install the repository's npm dependencies and set CHROMIUM_PATH to the browser executable and NODE_PATH if Playwright is installed separately. Run from a clean checkout of the implementation.

    PYTHONPATH="$PWD/tools" python3 -m unittest discover -s tests -v
    node --test tests/*.test.cjs
    node --test --test-concurrency=2 tests/*.browser.cjs

For browser RED, copy only the candidate tests/r2-ab.browser.cjs onto the baseline checkout and run the command below. For the exact-function RED, copy the PR #32 test or the candidate staging-aware Node test to the baseline tests directory. For artifact integrity run sha256sum -c evidence/m044/ns001-ab/overlap/SHA256SUMS from the Studio root on the evidence commit.

    node --test --test-name-pattern='opening a different project' tests/r2-ab.browser.cjs

First remaining gate is Night Lead's independent exact-commit replay. Local browser tests establish selection, revision and transport identity under the specified interleavings. Hosted behavior, physical handset playback and human listening remain unverified.

## Source availability

Studio source, QA source and local execution inputs were recovered for this repair. Unavailable historical project uploads in this executor were specstuff.zip, Sara studio 8.txt, all5.zip, studio2.zip, tlspec3.zip, all2.zip, Sara studio 5.txt, code.zip, tlspec2.zip, SoundForge-Studio-Release-v2.18.zip, all4.zip, Sara studio 7.txt, studio1.zip, all1.zip, all3.zip, Sara studio 6.txt and S.A.R.A.pdf. Retry those uploads only if a separate review requires their contents.

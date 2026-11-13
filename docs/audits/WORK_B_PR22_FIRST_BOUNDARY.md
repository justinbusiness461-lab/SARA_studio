# Work B PR22 independent runtime HOLD

Target 5c1d7f51b2bfbf7088e14a83cf9d8380391e0113
Base cbb297170a94494c89a2924607b8109fdecdcdd5
Owner Bobby 2. Severity P1, integration blocking.

Executed exact GitHub commit archive in independent KERNEL Chromium VM. No candidate source edits.
66/66 Python and 11/11 Node pass.
Browser aggregate 8/9 pass, 1 fails. Execution stopped after inspection of first failure family. No merge.

First failed boundary tests/r2-ab.browser.cjs:167.
The R2 switch wait observes __M044_PLAYBACK_PROOF__.revisionId becoming R2, then reads __M044_AB_PROOF__ whose fromRevisionId still identifies the previous switch's source. Expected 9982bf703e3e09317fb9007613b6f4bfd7668b121c2df3d3444d971f190e6d16, actual d0db01a584b48909fd07cd369563ea3376e6949a9a51380a3fbaa9b1306bdaea.

Source confirms verifyPlayableRevision publishes playback proof and ready state before selectABRevision awaits media.play(), restores/completes the switch, and publishes the AB proof. The test waits for the earlier marker. This is an observed completion/proof synchronization failure; wrong audio bytes are not established.

Minimum correction: define a reliable completion marker for the entire requested A/B switch including target identity, position and completion generation; wait for that completed switch in the browser assertion before reading proof. Preserve candidate scope and verify actual position after completion. Do not relax identity assertions or use arbitrary sleeps.

Commands:
PYTHONPATH=tools:tests python3 -m unittest discover -s tests -v
node --test tests/scorecore.test.cjs tests/m044-session.test.cjs tests/prompt-ui.test.cjs
CHROMIUM_PATH=/usr/local/bin/chromium node --test tests/r2-ab.browser.cjs tests/r2-cold-reopen.browser.cjs tests/r1-playback.browser.cjs tests/prompt-generate.browser.cjs

## Raw browser log
```
TAP version 13
# Subtest: Studio loads ScoreCore, persists Generate, and reopens the exact revision
ok 1 - Studio loads ScoreCore, persists Generate, and reopens the exact revision
  ---
  duration_ms: 5273.988571
  type: 'test'
  ...
# Subtest: Installed Studio precaches the matching ScoreCore adapter
ok 2 - Installed Studio precaches the matching ScoreCore adapter
  ---
  duration_ms: 733.842237
  type: 'test'
  ...
# Subtest: Generate reaches verified revision-bound WAV before Play is enabled
ok 3 - Generate reaches verified revision-bound WAV before Play is enabled
  ---
  duration_ms: 5252.659001
  type: 'test'
  ...
# Subtest: audio retrieval failure never presents Generate as playable
ok 4 - audio retrieval failure never presents Generate as playable
  ---
  duration_ms: 3390.581956
  type: 'test'
  ...
# Subtest: fresh Studio process reopens exact R1 and refetches same authorized WAV
ok 5 - fresh Studio process reopens exact R1 and refetches same authorized WAV
  ---
  duration_ms: 4369.223864
  type: 'test'
  ...
# Subtest: Verse 2 Bass -12 creates lawful R2 and preserves non-target SongSpec
ok 6 - Verse 2 Bass -12 creates lawful R2 and preserves non-target SongSpec
  ---
  duration_ms: 8030.334884
  type: 'test'
  ...
# Subtest: R1/R2 A-B selects exact revision audio and preserves musical position
not ok 7 - R1/R2 A-B selects exact revision audio and preserves musical position
  ---
  duration_ms: 7456.269159
  type: 'test'
  location: '/tmp/pr22/justinbusiness461-lab-SARA_studio-5c1d7f5/tests/r2-ab.browser.cjs:136:1'
  failureType: 'testCodeFailure'
  error: |-
    Expected values to be strictly equal:
    + actual - expected
    
    + 'd0db01a584b48909fd07cd369563ea3376e6949a9a51380a3fbaa9b1306bdaea'
    - '9982bf703e3e09317fb9007613b6f4bfd7668b121c2df3d3444d971f190e6d16'
    
  code: 'ERR_ASSERTION'
  name: 'AssertionError'
  expected: '9982bf703e3e09317fb9007613b6f4bfd7668b121c2df3d3444d971f190e6d16'
  actual: 'd0db01a584b48909fd07cd369563ea3376e6949a9a51380a3fbaa9b1306bdaea'
  operator: 'strictEqual'
  stack: |-
    TestContext.<anonymous> (/tmp/pr22/justinbusiness461-lab-SARA_studio-5c1d7f5/tests/r2-ab.browser.cjs:167:10)
    async Test.run (node:internal/test_runner/test:1054:7)
    async Test.processPendingSubtests (node:internal/test_runner/test:744:7)
  ...
# Subtest: late R1 A-B response cannot replace newer R2 selection
ok 8 - late R1 A-B response cannot replace newer R2 selection
  ---
  duration_ms: 7431.823623
  type: 'test'
  ...
# Subtest: fresh server/browser preserves R2 current, R1/R2 history, exact WAVs and A/B
ok 9 - fresh server/browser preserves R2 current, R1/R2 history, exact WAVs and A/B
  ---
  duration_ms: 10022.199297
  type: 'test'
  ...
1..9
# tests 9
# suites 0
# pass 8
# fail 1
# cancelled 0
# skipped 0
# todo 0
# duration_ms 23311.021428

```

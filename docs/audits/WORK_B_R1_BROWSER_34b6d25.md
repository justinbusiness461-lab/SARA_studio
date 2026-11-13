# Work B independent R1 browser qualification

Target 34b6d25a0344f1fbe20cbc6795ec3e830edd795a
Base d6075aad4296d298f7e8bb68dcbc4ecccc067a12
Verdict PASS, bounded R1 connected Studio slice.

Independent local exact checkout passed 66 Python tests and 11 focused Node tests. Chromium was blocked by local socket policy. Execution was moved to a fresh KERNEL browser VM q4b0x14tzqgx421os8amtowf. The exact public GitHub commit archive was installed with npm ci and Playwright as a temporary test dependency. Product source was unchanged.

CHROMIUM_PATH=/usr/local/bin/chromium node --test tests/r1-playback.browser.cjs tests/prompt-generate.browser.cjs

All five browser tests passed. A second five-test run used a temporary external preload to print the existing playback proof objects for evidence capture. It did not modify source or assertions. Both source/test file SHA-256 sets matched the independent local exact checkout.

Source hashes
- tools/studio_server.py 96048d39ef5a6422e44c2bf507043930c19dc0aace01d35df57097db1075c06e
- app-ui.js a3408f6786bdb56784fa5947116547c279185b8be0d152b24d930d62d567e86e
- tests/r1-playback.browser.cjs 0c0150d6436cc7295d7f82158c91a6f87959ee7354af80f3fe98f3a8c4a8c3cf
- tests/prompt-generate.browser.cjs cf48fa1771860f9f476a6ffdcc23142d49e17145b14c79b9875f3a88011e7506

Browser proves Generate, durable revision, authoritative render and WAV retrieval, SHA match, decode, Play, failed-fetch disabled transport, offline adapter loading, fresh server and browser reopen with identical revision and WAV.
Python suite includes real two-principal HTTP authorization and pre-reconciliation orphan denial followed by exact recovered bytes.

Playback means successful browser media.play(), not human listening or speaker quality certification. R2/A-B, hosted user identity and release quality remain outside this gate.

## Browser execution log

```text
TAP version 13
# WORK_B_IDENTITY={"projectId":"6308702e97fc4500965501b4d88a6229","revisionId":"cc3fcb597aebbb618cae3257fc94832eaf22895022a79afd1c67ff6816b58fb8","artifactId":"81d23d6cd1d75a4798b6f66c3064268862e9919d50588f73155fb23a6d30046b","wavSha256":"81d23d6cd1d75a4798b6f66c3064268862e9919d50588f73155fb23a6d30046b","decodedWavValidity":true,"durationSec":50.5,"transportSelectedRevision":"cc3fcb597aebbb618cae3257fc94832eaf22895022a79afd1c67ff6816b58fb8"}
# Subtest: Studio loads ScoreCore, persists Generate, and reopens the exact revision
ok 1 - Studio loads ScoreCore, persists Generate, and reopens the exact revision
  ---
  duration_ms: 4175.726224
  type: 'test'
  ...
# Subtest: Installed Studio precaches the matching ScoreCore adapter
ok 2 - Installed Studio precaches the matching ScoreCore adapter
  ---
  duration_ms: 566.431958
  type: 'test'
  ...
# WORK_B_IDENTITY={"projectId":"9b0e7bc99c3b4ea18ef6bae6f5f96e51","revisionId":"0a0844901f8c03a945384492bd38b3fcba1dda950e0994c2f5745355d3f5d378","artifactId":"81d23d6cd1d75a4798b6f66c3064268862e9919d50588f73155fb23a6d30046b","wavSha256":"81d23d6cd1d75a4798b6f66c3064268862e9919d50588f73155fb23a6d30046b","decodedWavValidity":true,"durationSec":50.5,"transportSelectedRevision":"0a0844901f8c03a945384492bd38b3fcba1dda950e0994c2f5745355d3f5d378"}
# Subtest: Generate reaches verified revision-bound WAV before Play is enabled
ok 3 - Generate reaches verified revision-bound WAV before Play is enabled
  ---
  duration_ms: 4106.006823
  type: 'test'
  ...
# Subtest: audio retrieval failure never presents Generate as playable
ok 4 - audio retrieval failure never presents Generate as playable
  ---
  duration_ms: 3557.436481
  type: 'test'
  ...
# WORK_B_IDENTITY={"projectId":"4ad15ad36ab74a088d0c69af1ffd7b4a","revisionId":"dd67e2bdecc90194a4647eb67822a6a7848ad746ef56e4fbc5a4dac9ea277cce","artifactId":"81d23d6cd1d75a4798b6f66c3064268862e9919d50588f73155fb23a6d30046b","wavSha256":"81d23d6cd1d75a4798b6f66c3064268862e9919d50588f73155fb23a6d30046b","decodedWavValidity":true,"durationSec":50.5,"transportSelectedRevision":"dd67e2bdecc90194a4647eb67822a6a7848ad746ef56e4fbc5a4dac9ea277cce"}
# WORK_B_IDENTITY={"projectId":"4ad15ad36ab74a088d0c69af1ffd7b4a","revisionId":"dd67e2bdecc90194a4647eb67822a6a7848ad746ef56e4fbc5a4dac9ea277cce","artifactId":"81d23d6cd1d75a4798b6f66c3064268862e9919d50588f73155fb23a6d30046b","wavSha256":"81d23d6cd1d75a4798b6f66c3064268862e9919d50588f73155fb23a6d30046b","decodedWavValidity":true,"durationSec":50.5,"transportSelectedRevision":"dd67e2bdecc90194a4647eb67822a6a7848ad746ef56e4fbc5a4dac9ea277cce"}
# Subtest: fresh Studio process reopens exact R1 and refetches same authorized WAV
ok 5 - fresh Studio process reopens exact R1 and refetches same authorized WAV
  ---
  duration_ms: 4450.273708
  type: 'test'
  ...
1..5
# tests 5
# suites 0
# pass 5
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 12421.404953

```

# M044 Work C — Physical audio and recovery

November 10, 2026 · Sound Forge main `14e2fb9cc55c8ce2909803a66d509915a18eb625`

PR #10 merged at `27f954a2a3ce423717721d30e26c6a2cab485bba`. The current mainline server SHA-256 is `f2707c42cbce9b1958cf9bf64af95b1557005bfe40ec6f6ca113b0de9ea947a8`. PR #11 was open on the Bobby feature branch. PR #14 was open with Work C preparation. PR #16 was open and draft with a WAV bridge contract. Project sources Sara studio 6/7 were consulted as prior receipts. Governance main resolved to `f45ae27df34c9b53507bff653b59258f05eac020`. Floot had a DJ RezrXtion visualizer and no Studio project under that name. Hosted Studio behavior and a new sonic blueprint were unverified for this run.

| Gate | Verdict | Evidence |
|---|---|---|
| Audio validity | PASS | Three distinct real RIFF/WAVE files, complete PCM16 decode, 44,100 Hz, 2 channels, 463,050 frames per file, 10.5 seconds, no full-scale samples. |
| Musical edit correctness | PASS, bounded | Bass events at ticks 7680, 9600, 11520 and 13440 shifted by exactly −12 semitones. The integration probe compared the entire expected SongSpec and counted 220,494 changed PCM frames with zero outside the edit plus 4,410-frame allowance. Listening quality remains UNVERIFIED. |
| Playback authority | UNVERIFIED, connected app | Local engine normal-path R2 current and R1 history survived cold reopen. Browser A/B playback and hosted tenant isolation were unverified. Main’s GET allowlist contains only public app assets. |

| File | WAV SHA-256 | Sample peak dBFS | True peak dBTP | LUFS-I | Channel state |
|---|---|---:|---:|---:|---|
| R1 | `908f6f5745ff3afd794aea296c5b9a23245d0778e18a4f37cf82e0e089cda399` | −9.90 | −9.32 | −29.17 | Dual mono |
| R2 | `ee0bec084d0c745748ca9fd6b413844c0568133eaa3ac40ef0e660ca939b7fd4` | −9.96 | −9.36 | −29.59 | Dual mono |
| Late R1 | `a98d1da19494b08521a1d8f0f40b201e85cbffbc0db98f689e8dd881a7d0c94f` | −9.90 | −9.32 | −29.17 | Near-identical channels, intentional one-LSB marker |

DC offset absolute maximum was 0.000113 FS. PCM16 decoded to integer samples with complete frame counts. FFmpeg found no silence interval at or below −55 dBFS for at least 500 ms on the original streams. The longest exact-zero interval was 450 ms. FFmpeg loudnorm reports input measurements. The dual-mono result is a fixture limit for stereo qualification. This audit covers a short instrumental engineering fixture.

## Findings

| Severity | Finding and evidence | Owner | Impact and blocker | Next action |
|---|---|---|---|---|
| High | **FAIL** before pending ownership. SIGKILL after `project_artifact_fence()` returned at `tools/studio_server.py:398`, before the receipt write at line 407. WAV survives. A separate fresh process opens R1 with zero late bindings. R2 revision and output remain exact. | Bobby for repair, Work B and C for independent verification | Automatic recovery loses the association in this window. Full late-history crash recovery is blocked. | Persist durable ownership before the earliest recoverable output boundary in the supported render flow. Verify pre/post artifact and receipt crash points, including the upload-to-commit gap, and preserve R2 authority. |
| High | **PASS** after pending ownership, as a control. SIGKILL at the existing named seam on line 408 leaves one pending record. Fresh-process reopen binds the WAV exactly once to R1 and preserves R2. | Bobby and Work B | This is the passing boundary exercised by the shipped regression. | Retain the control when adding coverage for the earlier window. |
| High | **BLOCKED** connected playback on checked main. `StudioHandler.do_GET` exposes public assets and has no authenticated, revision-bound WAV retrieval handler. The local capability is process-local. PR #16 defines the proposed bridge. | Bobby and Work A, with Work B qualifying | Work C cannot certify browser playback authority against this main. | Connect and qualify the authorized accessor, then run exact R1/R2 browser A/B and the late-R1 publication test on desktop and mobile. |

## Reproduction

Python 3.12.14, Node v24.22.1, FFmpeg 7.1.5. Standard suite results were 46/46 Python, 8/8 Node, 19/19 local HTTP/render integration. Run from the pinned repo root.

```sh
npm ci --no-audit --no-fund
PYTHONPATH=tools python3 -m unittest discover -s tests -v
node --test tests/*.test.cjs
node tools/m044_probe.cjs /tmp/m044-proof
python3 tools/certify_mix.py /tmp/m044-proof/R2.wav
ffmpeg -i /tmp/m044-proof/R2.wav -af loudnorm=print_format=json -f null -
ffmpeg -i /tmp/m044-proof/R2.wav -af silencedetect=noise=-55dB:d=0.5 -f null -
```

Save the Python block below as `m044_crash_window.py` and run `PYTHONPATH=tools:tests python3 /path/to/m044_crash_window.py`. Current main returns 1 with zero early and one late binding. A repair moving the fence requires moving the instrumentation to the corresponding durable boundaries and updating the intermediate pending-record assertion.

```python
"""Run from repo root with PYTHONPATH=tools:tests python3 path/to/this_file."""
import json
import subprocess
import sys
from pathlib import Path

import studio_server as server
from test_m044_operations import OperationTests

KILL = """
import json, os, signal, sys
import studio_server as s
root, raw, stage = sys.argv[1:]
request = json.loads(raw)
if stage == 'before-pending':
    fence = s.project_artifact_fence
    def stop(root, digest):
        fence(root, digest)
        if digest == request['outputArtifactIds'][0]:
            os.kill(os.getpid(), signal.SIGKILL)
    s.project_artifact_fence = stop
else:
    def stop(boundary):
        if boundary == 'artifact_durable_before_historical_binding':
            os.kill(os.getpid(), signal.SIGKILL)
    s.project_boundary = stop
s.project_operation(root, request, commit=True)
"""

REOPEN = """
import json, sys
import studio_server as s
root, pid, rid = sys.argv[1:]
current = s.project_operation(root, {'projectId': pid})
old = s.project_operation(root, {'projectId': pid, 'revisionId': rid})
print(json.dumps({'current': current, 'historical': old}))
"""

results = []
for stage in ('before-pending', 'after-pending'):
    fixture = OperationTests()
    fixture.setUp()
    try:
        edited = server.project_operation(fixture.root, fixture.request, commit=True)
        # Use distinct valid PCM to ensure current output survives byte-for-byte.
        current_audio = fixture.wav()[:44] + bytes([3, 0, 4, 0]) * 32
        current_digest = server.persist_export(fixture.root, 'current.wav', 'test', current_audio)['sha256']
        edited_id = edited['revision']['revisionId']
        current = server.project_operation(fixture.root, {
            'projectId': fixture.pid, 'expectedCurrentRevisionId': edited_id,
            'songSpec': edited['songSpec'], 'sourceAssetDigests': [],
            'outputArtifactIds': [current_digest], 'operationId': 'current-render',
            'operationContext': {'kind': 'render', 'sourceRevisionId': edited_id},
        }, commit=True)
        request = fixture.late_request(fixture.wav())
        digest = request['outputArtifactIds'][0]
        r1 = fixture.r1['revision']['revisionId']
        root = str(fixture.root)
        terminated = subprocess.run([sys.executable, '-c', KILL, root, json.dumps(request), stage])
        assert terminated.returncode == -9, terminated.returncode
        pending_before_reopen = len(list(Path(root).rglob('pending-renders/*.json')))
        assert pending_before_reopen == (0 if stage == 'before-pending' else 1)
        assert server.artifact_bytes(fixture.root, digest) == fixture.wav()
        snapshot = json.loads(subprocess.check_output([sys.executable, '-c', REOPEN, root, fixture.pid, r1]))
        history = [binding['artifactId'] for binding in snapshot['historical'].get('historicalOutputBindings', [])]
        assert snapshot['current'] == current
        assert snapshot['historical']['revision'] == fixture.r1['revision']
        assert server.artifact_bytes(fixture.root, current_digest) == current_audio
        results.append({
            'stage': stage, 'process_exit': terminated.returncode, 'pending_at_kill': pending_before_reopen,
            'late_wav_survives': True, 'r1_history_bindings': len(history),
            'recovered_exactly_once': history == [digest], 'r2_revision_and_output_unchanged': True,
        })
    finally:
        fixture.tearDown()

print(json.dumps(results, indent=2))
raise SystemExit(0 if all(row['recovered_exactly_once'] for row in results) else 1)
```

## JUSTIN 101

- **What changed** — Work C independently measured fresh engine renders and isolated the two crash points on authenticated main.
- **What failed or was blocked** — Before-pending recovery lost R1 history. Connected browser playback awaits the authenticated WAV bridge.
- **What is proven** — Bounded physical WAV validity, exact scoped bass edit, normal-path cold reopen and after-pending crash recovery.
- **What remains unverified** — Hosted playback, cross-user authorization, listening quality, full-song behavior and power-loss recovery.
- **What Justin must do** — Nothing for this handoff.

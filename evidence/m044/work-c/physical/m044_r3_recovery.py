"""Qualify a pinned M044 checkout at the retained artifact-fence fault seams.

Run from the candidate root:
    PYTHONPATH=tools:tests python3 /absolute/path/m044_r3_recovery.py EXACT_SHA

Exit 0 means both recovery cases passed, 1 means a reproduced recovery
failure, and 2 means a precondition or fault seam could not be verified.
This probe covers process death in the project render-binding path.
"""
import hashlib
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

if len(sys.argv) != 2:
    sys.exit(2)
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
if head != sys.argv[1] or Path(server.__file__).resolve() != Path('tools/studio_server.py').resolve():
    print('UNVERIFIED: requested SHA or loaded server does not match checkout', file=sys.stderr)
    sys.exit(2)
status = subprocess.check_output(
    ['git', 'status', '--porcelain', '--untracked-files=no'], text=True
)
if status.strip():
    print('UNVERIFIED: candidate has modified tracked files', file=sys.stderr)
    sys.exit(2)

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
        if terminated.returncode != -9:
            print(json.dumps({'verdict': 'UNVERIFIED', 'sha': head,
                              'stage': stage, 'exit': terminated.returncode,
                              'reason': 'Fault seam did not terminate the child'}))
            sys.exit(2)
        pending_before_reopen = len(list(Path(root).rglob('pending-renders/*.json')))
        assert server.artifact_bytes(fixture.root, digest) == fixture.wav()
        # A second fresh process detects repeated reconciliation or duplicate binds.
        snapshots = [
            json.loads(subprocess.check_output([sys.executable, '-c', REOPEN, root, fixture.pid, r1]))
            for _ in range(2)
        ]
        histories = [
            [binding['artifactId'] for binding in snapshot['historical'].get('historicalOutputBindings', [])]
            for snapshot in snapshots
        ]
        results.append({
            'stage': stage,
            'process_exit': terminated.returncode,
            'pending_at_kill': pending_before_reopen,
            'late_wav_sha256': hashlib.sha256(fixture.wav()).hexdigest(),
            'r1_binding_counts': [history.count(digest) for history in histories],
            'recovered_exactly_once': all(history == [digest] for history in histories),
            'r1_revision_unchanged': all(
                snapshot['historical']['revision'] == fixture.r1['revision'] for snapshot in snapshots
            ),
            'r2_revision_and_output_unchanged': (
                all(snapshot['current'] == current for snapshot in snapshots)
                and server.artifact_bytes(fixture.root, current_digest) == current_audio
            ),
        })
    finally:
        fixture.tearDown()

passed = all(
    row['recovered_exactly_once']
    and row['r1_revision_unchanged']
    and row['r2_revision_and_output_unchanged']
    for row in results
)
print(json.dumps({'sha': head, 'verdict': 'PASS' if passed else 'FAIL', 'cases': results}, indent=2))
sys.exit(0 if passed else 1)

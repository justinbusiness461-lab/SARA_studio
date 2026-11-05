import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'tests'))
from test_m044_operations import OperationTests
import studio_server as server

case = OperationTests()
case.setUp()
try:
    r2 = server.project_operation(case.root, case.request, commit=True)
    request = case.late_request(case.wav())
    artifact = request['outputArtifactIds'][0]
    code = '''
import json, os, sys
import studio_server as server
original = server.project_artifact_fence
def kill_after_artifact_fence(root, digest):
    original(root, digest)
    if digest == sys.argv[3]:
        os._exit(73)
server.project_artifact_fence = kill_after_artifact_fence
server.project_operation(sys.argv[1], json.loads(sys.argv[2]), commit=True)
'''
    killed = subprocess.run([sys.executable, '-c', code, str(case.root), json.dumps(request), artifact])
    assert killed.returncode == 73
    # A separate process reopens disk authority without replaying the request.
    reopen = '''
import json, sys
import studio_server as server
print(json.dumps(server.project_operation(sys.argv[1], {'projectId': sys.argv[2], 'revisionId': sys.argv[3]})))
'''
    recovered = subprocess.run([sys.executable, '-c', reopen, str(case.root), case.pid,
                               case.r1['revision']['revisionId']], capture_output=True, text=True, check=True)
    history = json.loads(recovered.stdout)
    bindings = history.get('historicalOutputBindings', [])
    count = sum(binding['artifactId'] == artifact for binding in bindings)
    data = server.artifact_bytes(case.root, artifact)
    server.validate_render_audio(case.root, artifact)
    result = {
        'targetSha': '9f200d5e3b45494cca4f46728cc9e3e8a64766fc',
        'killPoint': 'after real project_artifact_fence returns, before pending-renders mkdir/write',
        'childExit': killed.returncode,
        'freshProcessReopen': True,
        'artifactDigest': artifact,
        'artifactHashValid': hashlib.sha256(data).hexdigest() == artifact,
        'artifactDecodeValid': True,
        'capturedRevisionId': case.r1['revision']['revisionId'],
        'historyOccurrences': count,
        'R2StillCurrent': history['manifest'] == r2['manifest'],
        'pendingRecords': len(list((case.root / 'projects' / case.pid / 'pending-renders').glob('*.json'))),
        'verdict': 'FAIL' if count != 1 else 'PASS',
    }
    Path('independent_pre_pending_result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
finally:
    case.tearDown()

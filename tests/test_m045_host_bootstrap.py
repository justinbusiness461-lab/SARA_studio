import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import studio_server as server
import test_m045_native_attempt as fixture_module

class NativeHostBootstrapTests(unittest.TestCase):
    def test_factory_commits_against_real_studio_revision_store(self):
        fixture=fixture_module.NativeAttemptTests()
        fixture.setUp()
        try:
            native=server.make_m045_native_owner(fixture.root)
            _,synth=fixture._owner()
            receipt=native.execute_attempt(**fixture._kwargs(
                idempotency_key="factory-native-1",synthesize_to_stage_fn=synth))
            self.assertEqual(receipt["state"],"COMMITTED")
            self.assertEqual(receipt["revision"]["outputArtifactIds"],[receipt["attempt"]["artifact_digest"]])
            recovered=server.make_m045_native_owner(fixture.root).reconcile_attempt(
                headers=fixture._kwargs()["headers"], project_id=fixture.pid,idempotency_key="factory-native-1")
            self.assertEqual(recovered["revision"]["revisionId"],receipt["revision"]["revisionId"])
        finally:
            fixture.tearDown()

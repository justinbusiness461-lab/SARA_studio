import pathlib, sys, tempfile, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))

class AceStepAdmissionTests(unittest.TestCase):

    def test_mock_remote_pcm_publishes_native_cas_and_recovers(self):
        import hashlib
        from unittest.mock import patch
        from m045_acestep_provider import AceStepProvider
        import test_m045_native_attempt as f
        fixture=f.NativeAttemptTests()
        fixture.setUp()
        try:
            class Response:
                headers={"Content-Type":"audio/wav","X-Model-Id":"ace-step-1.5",
                         "X-Checkpoint-SHA256":"a"*64,"X-Request-Id":"qualified-test-1"}
                def __enter__(self): return self
                def __exit__(self,*args): return False
                def read(self,limit): return fixture.bytes
            owner, _ = fixture._owner()
            synth = AceStepProvider(endpoint_url="https://approved.example/infer",checkpoint_dir="")
            with patch("m045_acestep_provider.urllib.request.urlopen",return_value=Response()):
                result = owner.execute_attempt(**fixture._kwargs(
                    model_id="ace-step-1.5",model_version="ace-step-1.5",
                    idempotency_key="ace-infer-1",params={"music_length_ms":3000},
                    synthesize_to_stage_fn=synth))
            self.assertEqual(result["state"],"COMMITTED")
            self.assertEqual(result["attempt"]["provenance"]["preservation_tier"],"P3")
            self.assertEqual(result["attempt"]["provenance"]["checkpoint_sha256"],"a"*64)
            digest=result["attempt"]["artifact_digest"]
            self.assertEqual(hashlib.sha256(fixture.bytes).hexdigest(),digest)
            self.assertEqual((fixture.root/"objects"/digest[:2]/digest).read_bytes(),fixture.bytes)
            recovered=fixture._owner()[0].reconcile_attempt(
                headers=fixture._kwargs()["headers"],project_id=fixture.pid,idempotency_key="ace-infer-1")
            self.assertEqual(recovered["revision"]["revisionId"],result["revision"]["revisionId"])
        finally:
            fixture.tearDown()
    def test_missing_checkpoint_and_endpoint_fails_closed(self):
        from m045_acestep_provider import AceStepProvider, ProviderUnavailable
        with self.assertRaises(ProviderUnavailable):
            AceStepProvider(endpoint_url="",checkpoint_dir="")(pathlib.Path(tempfile.gettempdir()),{}, "demo","",1,{"music_length_ms":3000})

    def test_local_checkpoint_without_qualified_runtime_fails_closed(self):
        from m045_acestep_provider import AceStepProvider, ProviderUnavailable
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ProviderUnavailable):
                AceStepProvider(endpoint_url="",checkpoint_dir=d)(pathlib.Path(d),{}, "demo","",1,{"music_length_ms":3000})

import hashlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from m045_acestep_provider import AceStepProvider, ProviderUnavailable
import test_m045_native_attempt as native_tests

class Response:
    def __init__(self, body, mime="application/json"):
        self.data = body if isinstance(body,bytes) else json.dumps(body).encode()
        self.headers = {"Content-Type":mime}
    def __enter__(self): return self
    def __exit__(self,*_): return False
    def read(self,size=-1):
        data=self.data if size<0 else self.data[:size]
        self.data=self.data[len(data):]
        return data

class OfficialAPIContractTests(unittest.TestCase):
    def test_release_query_download_and_canonical_revision(self):
        fx=native_tests.NativeAttemptTests();fx.setUp()
        try:
            seen=[]
            def transport(req, timeout=None):
                url=req.full_url
                if url.endswith("/release_task"):
                    body=json.loads(req.data)
                    self.assertEqual(body["audio_duration"], 12)
                    self.assertEqual(body["seed"], 42)
                    self.assertEqual(body["use_random_seed"],False)
                    self.assertEqual(body["audio_format"],"wav")
                    self.assertEqual(body["batch_size"],1)
                    self.assertEqual(body["model"],"acestep-v15-turbo")
                    self.assertEqual(body["bpm"],96)
                    self.assertEqual(body["key_scale"],"E minor")
                    self.assertEqual(body["time_signature"],"4")
                    seen.append("release")
                    return Response({"code":200,"data":{"task_id":"job-1","status":"queued"},"error":None})
                if url.endswith("/query_result"):
                    self.assertEqual(json.loads(req.data),{"task_id_list":["job-1"]})
                    seen.append("query")
                    payload=[{"file":"/v1/audio?path=%2Ftmp%2Fabc.wav","dit_model":"acestep-v15-turbo","seed_value":"42"}]
                    return Response({"code":200,"data":[{"task_id":"job-1","status":1,"result":json.dumps(payload)}],"error":None})
                self.assertEqual(url,"https://models.example/v1/audio?path=%2Ftmp%2Fabc.wav")
                seen.append("download")
                return Response(fx.bytes,"audio/wav")
            provider=AceStepProvider(endpoint_url="https://models.example",checkpoint_dir="",checkpoint_sha256="a"*64,poll_interval=0)
            owner,_=fx._owner()
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
                out=owner.execute_attempt(**fx._kwargs(
                    model_id="ace-step-1.5", model_version="ace-step-1.5",
                    idempotency_key="official-ace-1",seed=42,
                    song_spec={**fx.fixture.spec,"timebase":{**fx.fixture.spec["timebase"],"initial_bpm":96,"key":"E minor","meter":"4/4"}},
                    params={"music_length_ms":12000},synthesize_to_stage_fn=provider))
            self.assertEqual(out["state"],"COMMITTED")
            self.assertEqual(seen,["release","query","download"])
            self.assertEqual(out["attempt"]["provenance"]["checkpoint_identity_source"],"OPERATOR_CONFIGURED_UNVERIFIED")
            self.assertEqual(out["attempt"]["provenance"]["provider_request_id"],"job-1")
            reopened=fx._owner()[0].reconcile_attempt(headers=fx._kwargs()["headers"],project_id=fx.pid,idempotency_key="official-ace-1")
            self.assertEqual(reopened["attempt"]["artifact_digest"],out["attempt"]["artifact_digest"])
        finally: fx.tearDown()

    def test_missing_checkpoint_identity_blocks_before_remote_submission(self):
        with tempfile.TemporaryDirectory() as d:
            p=AceStepProvider(endpoint_url="https://models.example",checkpoint_dir="",checkpoint_sha256="")
            with patch("m045_acestep_provider.urllib.request.urlopen") as net:
                with self.assertRaises(ProviderUnavailable):
                    p(pathlib.Path(d),{}, "song","",1,{"music_length_ms":12000})
                net.assert_not_called()

    def test_foreign_audio_url_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=AceStepProvider(endpoint_url="https://models.example",checkpoint_dir="",checkpoint_sha256="a"*64,poll_interval=0)
            replies=[
                Response({"code":200,"data":{"task_id":"job-1"}}),
                Response({"code":200,"data":[{"task_id":"job-1","status":1,"result":json.dumps([{"file":"https://attacker.example/audio.wav"}])}]}),
            ]
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=replies) as net:
                with self.assertRaises(ValueError):
                    p(pathlib.Path(d),{},"song","",1,{"music_length_ms":12000})
                self.assertEqual(net.call_count,2)

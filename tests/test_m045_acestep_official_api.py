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

import studio_server as server
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

    def test_official_three_take_release_query_download_and_no_auto_promotion(self):
        fx=native_tests.NativeAttemptTests();fx.setUp()
        try:
            import io,wave
            variants=[]
            for v in (100,200,300):
                stream=io.BytesIO()
                with wave.open(stream,"wb") as wav:
                    wav.setframerate(44100);wav.setnchannels(2);wav.setsampwidth(2)
                    wav.writeframes(int(v).to_bytes(2,"little",signed=True)*2*100)
                variants.append(stream.getvalue())
            requests=[]
            def remote(req,timeout=None):
                url=req.full_url
                requests.append(url)
                if url.endswith("/release_task"):
                    data=json.loads(req.data)
                    self.assertEqual(data["batch_size"],3)
                    return Response({"code":200,"data":{"task_id":"three-remote"},"error":None})
                if url.endswith("/query_result"):
                    items=[{"file":f"/v1/audio?path=%2Ftmp%2Ftake{i}.wav","dit_model":"acestep-v15-turbo"} for i in range(3)]
                    return Response({"code":200,"data":[{"task_id":"three-remote","status":1,
                        "result":json.dumps(items)}],"error":None})
                for i in range(3):
                    if f"take{i}.wav" in url:return Response(variants[i],"audio/wav")
                raise AssertionError(url)
            provider=AceStepProvider(endpoint_url="https://models.example",
                checkpoint_dir="",checkpoint_sha256="a"*64,poll_interval=0)
            owner=server.make_m045_native_owner(fx.root)
            kwargs=fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
                idempotency_key="ace-three",batch_count=3,params={"music_length_ms":12000},
                synthesize_to_stage_fn=provider)
            before=server.project_operation(fx.root,{"projectId":fx.pid})["manifest"]["currentRevisionId"]
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=remote):
                result=owner.execute_attempt(**kwargs)
            self.assertEqual(result["state"],"AWAITING_TAKE_SELECTION")
            self.assertEqual(server.project_operation(fx.root,{"projectId":fx.pid})["manifest"]["currentRevisionId"],before)
            self.assertEqual(len({t["artifact_digest"] for t in result["attempt"]["takes"]}),3)
            self.assertEqual(len([url for url in requests if url.endswith("/release_task")]),1)
            for i in range(3):
                self.assertEqual(result["attempt"]["takes"][i]["provenance"]["provider_task_id"],"three-remote")
                self.assertEqual(owner.read_take_audio(headers=kwargs["headers"],project_id=fx.pid,
                    idempotency_key="ace-three",take_index=i)[:4],b"RIFF")
        finally:fx.tearDown()

    def test_three_take_interrupted_poll_cold_reconcile_reuses_original_upstream_task(self):
        fx=native_tests.NativeAttemptTests();fx.setUp()
        try:
            import io,wave,urllib.error
            variants=[]
            for v in (101,202,303):
                output=io.BytesIO()
                with wave.open(output,"wb") as wav:
                    wav.setframerate(44100);wav.setnchannels(2);wav.setsampwidth(2)
                    wav.writeframes(v.to_bytes(2,"little",signed=True)*2*120)
                variants.append(output.getvalue())
            calls=[]
            first=True
            def transport(req,timeout=None):
                nonlocal first
                url=req.full_url
                calls.append(url)
                if url.endswith("/release_task"):
                    return Response({"code":200,"data":{"task_id":"multi-recover-task"},"error":None})
                if url.endswith("/query_result"):
                    if first:
                        first=False
                        raise urllib.error.URLError("simulated poll failure")
                    names=[{"file":f"/v1/audio?path=%2Ftmp%2Fwave{i}.wav"} for i in range(3)]
                    return Response({"code":200,"data":[{"task_id":"multi-recover-task",
                        "status":1,"result":json.dumps(names)}],"error":None})
                for i in range(3):
                    if f"wave{i}.wav" in url:return Response(variants[i],"audio/wav")
                raise AssertionError(url)
            provider=AceStepProvider(endpoint_url="https://models.example",checkpoint_dir="",
                checkpoint_sha256="a"*64,poll_interval=0)
            owner=server.make_m045_native_owner(fx.root)
            kw=fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
                idempotency_key="multi-recover",batch_count=3,
                params={"music_length_ms":12000},synthesize_to_stage_fn=provider)
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
                with self.assertRaises(Exception):
                    owner.execute_attempt(**kw)
                recovered=server.make_m045_native_owner(fx.root).reconcile_attempt(
                    headers=kw["headers"],project_id=fx.pid,idempotency_key="multi-recover",
                    synthesize_to_stage_fn=provider)
            self.assertEqual(recovered["state"],"AWAITING_TAKE_SELECTION")
            self.assertEqual(len(recovered["attempt"]["takes"]),3)
            self.assertEqual(sum(p.endswith("/release_task") for p in calls),1)
            self.assertEqual(server.project_operation(fx.root,{"projectId":fx.pid})["manifest"]["currentRevisionId"],fx.r1["revision"]["revisionId"])
        finally: fx.tearDown()

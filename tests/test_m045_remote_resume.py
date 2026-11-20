import json
import pathlib
import sys
import unittest
import urllib.error
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from m045_acestep_provider import AceStepProvider
import test_m045_native_attempt as native

class Response:
    def __init__(self,value):
        self.data=value if isinstance(value,bytes) else json.dumps({"code":200,"error":None,"data":value}).encode()
        self.headers={"Content-Type":"application/json"}
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def read(self,limit=-1):
        v=self.data if limit<0 else self.data[:limit]
        self.data=self.data[len(v):]
        return v

class ResumeTests(unittest.TestCase):
    def test_poll_failure_reconciles_without_second_release_task(self):
        fx=native.NativeAttemptTests();fx.setUp()
        try:
            provider=AceStepProvider(endpoint_url="https://host.example",checkpoint_dir="",checkpoint_sha256="a"*64,poll_interval=0)
            requests=[]
            first=True
            def transport(req,timeout=None):
                nonlocal first
                url=req.full_url
                requests.append(url)
                if url.endswith("/release_task"):
                    return Response({"task_id":"task-A"})
                if url.endswith("/query_result"):
                    if first:
                        first=False
                        raise urllib.error.URLError("lost connection")
                    return Response([{"task_id":"task-A","status":1,"result":json.dumps([{"file":"/v1/audio?path=%2Ftmp%2Fa.wav","dit_model":"acestep-v15-turbo"}])}])
                return Response(fx.bytes)
            owner,_=fx._owner()
            kw=fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",idempotency_key="resume-once",params={"music_length_ms":12000},synthesize_to_stage_fn=provider)
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
                with self.assertRaises(Exception):
                    owner.execute_attempt(**kw)
                recovered=fx._owner()[0].reconcile_attempt(headers=kw["headers"],project_id=fx.pid,idempotency_key="resume-once",synthesize_to_stage_fn=provider)
            self.assertEqual(recovered["state"],"COMMITTED")
            self.assertEqual(sum(u.endswith("/release_task") for u in requests),1)
            self.assertIsNotNone(recovered["revision"])
        finally:fx.tearDown()

    def test_uncertain_submission_without_task_id_refuses_duplicate(self):
        fx=native.NativeAttemptTests();fx.setUp()
        try:
            provider=AceStepProvider(endpoint_url="https://host.example",checkpoint_dir="",
                                     checkpoint_sha256="a"*64,poll_interval=0)
            calls=[]
            def transport(req,timeout=None):
                calls.append(req.full_url)
                raise urllib.error.URLError("connection reset before response")
            owner,_=fx._owner()
            kw=fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
                          idempotency_key="uncertain-submission",params={"music_length_ms":12000},
                          synthesize_to_stage_fn=provider)
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
                with self.assertRaises(Exception):
                    owner.execute_attempt(**kw)
                state=fx._owner()[0].reconcile_attempt(
                    headers=kw["headers"],project_id=fx.pid,idempotency_key=kw["idempotency_key"],
                    synthesize_to_stage_fn=provider)
                self.assertEqual(state["state"],"SUBMISSION_UNCERTAIN")
                with self.assertRaises(Exception):
                    fx._owner()[0].execute_attempt(**kw)
            self.assertEqual(sum(u.endswith("/release_task") for u in calls),1)
        finally:fx.tearDown()

    def test_tampered_task_id_rejected_without_network(self):
        fx=native.NativeAttemptTests();fx.setUp()
        try:
            provider=AceStepProvider(endpoint_url="https://host.example",checkpoint_dir="",
                                     checkpoint_sha256="a"*64,poll_interval=0)
            def transport(req,timeout=None):
                if req.full_url.endswith("/release_task"):return Response({"task_id":"original-A"})
                raise urllib.error.URLError("poll interrupted")
            owner,_=fx._owner()
            kw=fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
                          idempotency_key="tamper-attempt",params={"music_length_ms":12000},
                          synthesize_to_stage_fn=provider)
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
                with self.assertRaises(Exception):owner.execute_attempt(**kw)
            rec=owner.reconcile_attempt(headers=kw["headers"],project_id=fx.pid,idempotency_key=kw["idempotency_key"])
            self.assertEqual(rec["state"],"POLL_INTERRUPTED")
            stage=owner._attempt_dir(fx.pid)/(rec["attempt"]["attempt_id"]+".stage")
            task_file=stage/"upstream-task.json"
            tampered=json.loads(task_file.read_text())
            tampered["task_id"]="forged-B"
            task_file.write_text(json.dumps(tampered))
            with patch("m045_acestep_provider.urllib.request.urlopen") as remote:
                with self.assertRaisesRegex(Exception,"tampered"):
                    fx._owner()[0].reconcile_attempt(headers=kw["headers"],project_id=fx.pid,
                        idempotency_key=kw["idempotency_key"],synthesize_to_stage_fn=provider)
                remote.assert_not_called()
        finally:fx.tearDown()

    def test_divergent_payload_and_unauthorized_recovery_denied(self):
        fx=native.NativeAttemptTests();fx.setUp()
        try:
            provider=AceStepProvider(endpoint_url="https://host.example",checkpoint_dir="",
                                     checkpoint_sha256="a"*64,poll_interval=0)
            def transport(req,timeout=None):
                if req.full_url.endswith("/release_task"):return Response({"task_id":"stable-A"})
                raise urllib.error.URLError("interrupted")
            owner,_=fx._owner()
            kw=fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
                          idempotency_key="no-divergent",params={"music_length_ms":12000},
                          synthesize_to_stage_fn=provider)
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
                with self.assertRaises(Exception): owner.execute_attempt(**kw)
            with patch("m045_acestep_provider.urllib.request.urlopen") as remote:
                with self.assertRaisesRegex(Exception,"idempotency key payload conflict"):
                    owner.execute_attempt(**{**kw,"prompt":"different song"})
                with self.assertRaises(Exception):
                    fx._owner()[0].reconcile_attempt(headers={"Authorization":"Bearer invalid"},
                        project_id=fx.pid,idempotency_key=kw["idempotency_key"],
                        synthesize_to_stage_fn=provider)
                remote.assert_not_called()
        finally:fx.tearDown()

    def test_crash_after_task_record_before_first_poll_recovers(self):
        fx=native.NativeAttemptTests();fx.setUp()
        try:
            from m045_generation_attempt import native_atomic_write_bytes
            provider=AceStepProvider(endpoint_url="https://host.example",checkpoint_dir="",
                                     checkpoint_sha256="a"*64,poll_interval=0)
            requests=[]
            def transport(req,timeout=None):
                requests.append(req.full_url)
                if req.full_url.endswith("/release_task"): return Response({"task_id":"durable-task"})
                if req.full_url.endswith("/query_result"):
                    if sum(x.endswith("/query_result") for x in requests)==1:
                        raise urllib.error.URLError("process stopped after saved ID")
                    return Response([{"task_id":"durable-task","status":1,
                                     "result":json.dumps([{"file":"/v1/audio?path=%2Ftmp%2Frecover.wav"}])}])
                return Response(fx.bytes)
            owner,_=fx._owner()
            kw=fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
                          idempotency_key="crash-after-accept",params={"music_length_ms":12000},
                          synthesize_to_stage_fn=provider)
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
                with self.assertRaises(Exception): owner.execute_attempt(**kw)
                path=owner._attempt_path(fx.pid,kw["idempotency_key"])
                attempt=json.loads(path.read_text())
                # Simulate kill after task file durability but before native owner
                # recorded its accepted status.
                attempt["state"]="PREPARING"
                attempt.pop("remote_task",None)
                native_atomic_write_bytes(path,json.dumps(attempt).encode())
                result=fx._owner()[0].reconcile_attempt(headers=kw["headers"],project_id=fx.pid,
                    idempotency_key=kw["idempotency_key"],synthesize_to_stage_fn=provider)
            self.assertEqual(result["state"],"COMMITTED")
            self.assertEqual(sum(url.endswith("/release_task") for url in requests),1)
        finally: fx.tearDown()

    def test_failure_after_audio_download_before_cas_resumes_original_task(self):
        fx=native.NativeAttemptTests();fx.setUp()
        try:
            import m045_acestep_provider as ace
            provider=AceStepProvider(endpoint_url="https://host.example",checkpoint_dir="",
                                     checkpoint_sha256="a"*64,poll_interval=0)
            urls=[]
            def transport(req,timeout=None):
                urls.append(req.full_url)
                if req.full_url.endswith("/release_task"): return Response({"task_id":"download-accepted"})
                if req.full_url.endswith("/query_result"):
                    return Response([{"task_id":"download-accepted","status":1,
                                     "result":json.dumps([{"file":"/v1/audio?path=%2Ftmp%2Fdownload.wav"}])}])
                return Response(fx.bytes)
            original=ace.native_atomic_write_bytes
            fault={"fired":False}
            def interrupted_write(path,data):
                if pathlib.Path(path).name=="output.wav" and not fault["fired"]:
                    fault["fired"]=True
                    raise OSError("simulated crash after download")
                return original(path,data)
            owner,_=fx._owner()
            kw=fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
                          idempotency_key="download-interruption",params={"music_length_ms":12000},
                          synthesize_to_stage_fn=provider)
            with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
                with patch("m045_acestep_provider.native_atomic_write_bytes",side_effect=interrupted_write):
                    with self.assertRaisesRegex(OSError,"simulated crash"):
                        owner.execute_attempt(**kw)
                recovered=fx._owner()[0].reconcile_attempt(headers=kw["headers"],project_id=fx.pid,
                    idempotency_key=kw["idempotency_key"],synthesize_to_stage_fn=provider)
            self.assertEqual(recovered["state"],"COMMITTED")
            self.assertEqual(sum(url.endswith("/release_task") for url in urls),1)
        finally:fx.tearDown()

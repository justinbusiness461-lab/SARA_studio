import hashlib
import io
import json
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import studio_server as studio
import test_m045_native_attempt as fixtures
from m045_acestep_provider import AceStepProvider

class Reply:
    def __init__(self,data):
        self.data=data if isinstance(data,bytes) else json.dumps({"code":200,"data":data,"error":None}).encode()
        self.headers={"Content-Type":"application/json"}
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n=-1):
        result=self.data if n<0 else self.data[:n]
        self.data=self.data[len(result):]
        return result

class ReferenceConditioningTests(unittest.TestCase):
    def setUp(self):
        self.fx=fixtures.NativeAttemptTests()
        self.fx.setUp()
        self.provider=AceStepProvider(endpoint_url="https://models.example",checkpoint_dir="",checkpoint_sha256="a"*64,poll_interval=0)
        self.digest=hashlib.sha256(self.fx.bytes).hexdigest()
    def tearDown(self):
        self.fx.tearDown()
    def kwargs(self,**extra):
        return self.fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
            idempotency_key="reference-1",reference_artifact_digest=self.digest,
            audio_cover_strength=0.35,params={"music_length_ms":12000},
            synthesize_to_stage_fn=self.provider,**extra)
    def test_unbound_digest_fails_before_remote_submit(self):
        owner=studio.make_m045_native_owner(self.fx.root)
        # CAS existence is not authorization: valid bytes without project membership.
        studio._publish_cas_exact(self.fx.root,self.digest,self.fx.bytes)
        with patch("m045_acestep_provider.urllib.request.urlopen") as network:
            with self.assertRaises(Exception):
                owner.execute_attempt(**self.kwargs())
            network.assert_not_called()
    def test_accepted_reference_is_sent_as_official_multipart(self):
        owner=studio.make_m045_native_owner(self.fx.root)
        studio._publish_cas_exact(self.fx.root,self.digest,self.fx.bytes)
        base=studio.project_operation(self.fx.root,{
            "projectId":self.fx.pid,
            "expectedCurrentRevisionId":self.fx.r1["revision"]["revisionId"],
            "songSpec":self.fx.fixture.spec,
            "sourceAssetDigests":[self.digest],
            "outputArtifactIds":[]},commit=True)
        urls=[]
        def transport(req,timeout=None):
            urls.append(req.full_url)
            if req.full_url.endswith("/release_task"):
                body=req.data
                self.assertIn(b'name="reference_audio"; filename="reference.wav"',body)
                self.assertIn(self.fx.bytes,body)
                self.assertIn(b'name="audio_cover_strength"',body)
                self.assertIn(b'0.35',body)
                self.assertNotIn(b'name="src_audio"',body)
                return Reply({"task_id":"reference-accepted"})
            if req.full_url.endswith("/query_result"):
                return Reply([{"task_id":"reference-accepted","status":1,
                    "result":json.dumps([{"file":"/v1/audio?path=%2Ftmp%2Fref.wav"}])}])
            return Reply(self.fx.bytes)
        kwargs=self.kwargs()
        kwargs.update(base_revision_id=base["revision"]["revisionId"],
                      expected_current_revision_id=base["revision"]["revisionId"])
        with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
            result=owner.execute_attempt(**kwargs)
        self.assertEqual(result["state"],"COMMITTED")
        self.assertEqual(result["attempt"]["provenance"]["reference_artifact_digest"],self.digest)
        self.assertEqual(urls.count("https://models.example/release_task"),1)

    def test_invalid_batch_count_is_rejected_without_submission(self):
        owner=studio.make_m045_native_owner(self.fx.root)
        with patch("m045_acestep_provider.urllib.request.urlopen") as network:
            for count in (0,5,True,"3"):
                with self.assertRaisesRegex(ValueError,"batch_count"):
                    owner.execute_attempt(**{**self.kwargs(),"batch_count":count})
            # Valid batch count is now admitted, but source authorization is
            # still enforced before any remote call.
            with self.assertRaisesRegex(Exception,"reference audio is not bound"):
                owner.execute_attempt(**{**self.kwargs(),"batch_count":3})
            network.assert_not_called()

    def test_unknown_reference_strength_and_unqualified_lego_fail_closed(self):
        owner=studio.make_m045_native_owner(self.fx.root)
        with patch("m045_acestep_provider.urllib.request.urlopen") as network:
            with self.assertRaisesRegex(ValueError,"audio_cover_strength"):
                owner.execute_attempt(**{**self.kwargs(),"audio_cover_strength":1.5})
            with self.assertRaisesRegex(Exception,"Change ONLY This"):
                owner.execute_attempt(**{**self.fx._kwargs(model_id="ace-step-1.5",
                    model_version="ace-step-1.5",synthesize_to_stage_fn=self.provider),
                    "params":{"edit_mode":"add_layer","layer_gain_db":-4}})
            network.assert_not_called()

    def test_legacy_request_fingerprint_is_unchanged_for_unconditioned_attempts(self):
        from m045_generation_attempt import _request_digest, _json_bytes
        kw=self.fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
            idempotency_key="legacy-fingerprint-1",params={"music_length_ms":12000},
            synthesize_to_stage_fn=self.provider)
        original={key:kw[key] for key in (
            "project_id","base_revision_id","expected_current_revision_id",
            "idempotency_key","model_id","model_version","seed","song_spec","prompt")}
        original.update({"lyrics":None,"params":kw["params"]})
        expected=hashlib.sha256(_json_bytes(original)).hexdigest()
        self.assertEqual(_request_digest(kw),expected)

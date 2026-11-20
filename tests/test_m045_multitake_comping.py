import io
import hashlib
import pathlib
import sys
import unittest
import wave
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import studio_server as server
import test_m045_native_attempt as base

def tone(value):
    b=io.BytesIO()
    with wave.open(b,"wb") as w:
        w.setframerate(44100);w.setnchannels(2);w.setsampwidth(2)
        w.writeframes(value.to_bytes(2,"little",signed=True)*2*120)
    return b.getvalue()

class MultiTakeTests(unittest.TestCase):
    def setUp(self):
        self.fx=base.NativeAttemptTests();self.fx.setUp()
        self.takes=[tone(1000),tone(1500),tone(2000)]
        def generate(stage,spec,prompt,lyrics,seed,params):
            self.assertEqual(params["_m045_batch_count"],3)
            files=[]
            for i,b in enumerate(self.takes):
                p=pathlib.Path(stage)/f"take-{i}.wav";p.write_bytes(b);files.append(p)
            return files
        generate.supports_multitake=True
        generate.model_id="ace-step-1.5";generate.model_version="ace-step-1.5"
        self.generate=generate
        self.owner=server.make_m045_native_owner(self.fx.root)
        self.kwargs=self.fx._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
                 idempotency_key="three-takes",batch_count=3,
                 synthesize_to_stage_fn=generate,params={"music_length_ms":12000})
    def tearDown(self):self.fx.tearDown()
    def test_three_takes_wait_for_artist_current_is_unchanged(self):
        r=self.owner.execute_attempt(**self.kwargs)
        self.assertEqual(r["state"],"AWAITING_TAKE_SELECTION")
        self.assertEqual([t["take_index"] for t in r["attempt"]["takes"]],[0,1,2])
        self.assertEqual(len({t["artifact_digest"] for t in r["attempt"]["takes"]}),3)
        self.assertEqual(server.project_operation(self.fx.root,{"projectId":self.fx.pid})["manifest"]["currentRevisionId"],self.fx.r1["revision"]["revisionId"])
        for i,t in enumerate(r["attempt"]["takes"]):
            self.assertEqual(t["artifact_digest"],hashlib.sha256(self.takes[i]).hexdigest())
            self.assertEqual(self.owner.read_take_audio(headers=self.kwargs["headers"],project_id=self.fx.pid,idempotency_key="three-takes",take_index=i),self.takes[i])
    def test_artist_selection_two_revisions_stale_denied_and_cold_reopen(self):
        self.owner.execute_attempt(**self.kwargs)
        origin=self.fx.r1["revision"]["revisionId"]
        chosen=self.owner.select_take(headers=self.kwargs["headers"],project_id=self.fx.pid,
            idempotency_key="three-takes",take_index=1,expected_current_revision_id=origin)
        r2=chosen["revision"]["revisionId"]
        self.assertNotEqual(r2,origin)
        with self.assertRaisesRegex(server.ProjectConflict,"stale"):
            self.owner.select_take(headers=self.kwargs["headers"],project_id=self.fx.pid,
               idempotency_key="three-takes",take_index=2,expected_current_revision_id=origin)
        another=server.make_m045_native_owner(self.fx.root)
        selected=another.select_take(headers=self.kwargs["headers"],project_id=self.fx.pid,
            idempotency_key="three-takes",take_index=2,expected_current_revision_id=r2)
        r3=selected["revision"]["revisionId"]
        self.assertNotEqual(r3,r2)
        self.assertEqual(server.project_operation(self.fx.root,{"projectId":self.fx.pid})["manifest"]["currentRevisionId"],r3)
        self.assertEqual(another.read_take_audio(headers=self.kwargs["headers"],project_id=self.fx.pid,idempotency_key="three-takes",take_index=0),self.takes[0])
        self.assertEqual(server.project_audio_bytes(self.fx.root,{"projectId":self.fx.pid,"revisionId":r2,
            "artifactId":hashlib.sha256(self.takes[1]).hexdigest()}),self.takes[1])
        self.assertEqual(server.project_audio_bytes(self.fx.root,{"projectId":self.fx.pid,"revisionId":r3,
            "artifactId":hashlib.sha256(self.takes[2]).hexdigest()}),self.takes[2])
    def test_unauthorized_take_audio_denied(self):
        self.owner.execute_attempt(**self.kwargs)
        with self.assertRaises(Exception):
            self.owner.read_take_audio(headers={"Authorization":"Bearer bogus"},project_id=self.fx.pid,idempotency_key="three-takes",take_index=0)

    def test_case_insensitive_authorization_header_from_http_transport(self):
        self.owner.execute_attempt(**self.kwargs)
        lower={"authorization":self.kwargs["headers"]["Authorization"]}
        self.assertEqual(self.owner.read_take_audio(headers=lower,project_id=self.fx.pid,
            idempotency_key="three-takes",take_index=1),self.takes[1])
        with self.assertRaises(Exception):
            self.owner.read_take_audio(headers={"authorization":"Bearer invalid"},project_id=self.fx.pid,
                idempotency_key="three-takes",take_index=1)

    def test_unrelated_revision_cannot_silently_rebase_generated_takes(self):
        self.owner.execute_attempt(**self.kwargs)
        origin=self.fx.r1["revision"]["revisionId"]
        unrelated=server.project_operation(self.fx.root,{"projectId":self.fx.pid,
            "expectedCurrentRevisionId":origin,"songSpec":self.fx.fixture.spec,
            "sourceAssetDigests":[],"outputArtifactIds":[]},commit=True)
        foreign_head=unrelated["revision"]["revisionId"]
        with self.assertRaisesRegex(server.ProjectConflict,"rebase"):
            self.owner.select_take(headers=self.kwargs["headers"],project_id=self.fx.pid,
                idempotency_key="three-takes",take_index=1,
                expected_current_revision_id=foreign_head)
        self.assertEqual(server.project_operation(self.fx.root,{"projectId":self.fx.pid})["manifest"]["currentRevisionId"],foreign_head)

    def test_cas_publication_has_durable_owner_intent_before_write(self):
        self.owner.publish_cas_object=self._publish_and_crash
        with self.assertRaisesRegex(OSError,"simulated CAS fault"):
            self.owner.execute_attempt(**self.kwargs)
        file=self.owner._attempt_path(self.fx.pid,"three-takes")
        attempt=__import__("json").loads(file.read_text())
        self.assertEqual(attempt["publication_intents"][0]["take_index"],0)
        self.assertEqual(attempt["publication_intents"][0]["artifact_digest"],
                         hashlib.sha256(self.takes[0]).hexdigest())
        self.assertEqual(server.artifact_bytes(self.fx.root,hashlib.sha256(self.takes[0]).hexdigest()),self.takes[0])

    def _publish_and_crash(self,data):
        digest=hashlib.sha256(data).hexdigest()
        server._publish_cas_exact(self.fx.root,digest,data)
        raise OSError("simulated CAS fault")

    def test_mismatched_take_frame_counts_are_rejected(self):
        import io,wave
        def different(stage,spec,prompt,lyrics,seed,params):
            paths=[]
            for index,length in enumerate((200,200,201)):
                b=io.BytesIO()
                with wave.open(b,"wb") as output:
                    output.setnchannels(2);output.setsampwidth(2);output.setframerate(44100)
                    output.writeframes((index+1).to_bytes(2,"little",signed=True)*2*length)
                path=pathlib.Path(stage)/f"take-{index}.wav"
                path.write_bytes(b.getvalue());paths.append(path)
            return paths
        different.supports_multitake=True
        different.model_id="ace-step-1.5";different.model_version="ace-step-1.5"
        with self.assertRaisesRegex(ValueError,"sample length"):
            self.owner.execute_attempt(**{**self.kwargs,
                "idempotency_key":"mismatch-duration","synthesize_to_stage_fn":different})

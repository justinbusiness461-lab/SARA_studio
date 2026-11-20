"""M045 repaint contract: lawful source binding, native isolation, and official multipart."""
import hashlib
import io
import json
import pathlib
import sys
import unittest
import wave
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import studio_server as studio
import test_m045_native_attempt as native
from m045_acestep_provider import AceStepProvider
from m045_repaint import read_pcm16_wav

def make_wav(frames, sample):
    buf=io.BytesIO()
    with wave.open(buf,"wb") as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
        w.writeframes(sample*frames)
    return buf.getvalue()
class Reply:
    def __init__(self,content):
        self.buf=content if isinstance(content,bytes) else json.dumps({"code":200,"error":None,"data":content}).encode()
        self.headers={"Content-Type":"application/json"}
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def read(self,n=-1):
        b=self.buf if n<0 else self.buf[:n]
        self.buf=self.buf[len(b):]
        return b

class NativeRepaintTests(unittest.TestCase):
    def setUp(self):
        self.f=native.NativeAttemptTests()
        self.f.setUp()
        self.src=make_wav(441000,b"\x01\x00\x02\x00")
        self.candidate=make_wav(441000,b"\x09\x00\x08\x00")
        digest=hashlib.sha256(self.src).hexdigest()
        studio._publish_cas_exact(self.f.root,digest,self.src)
        self.source=studio.project_operation(self.f.root,{"projectId":self.f.pid,
            "expectedCurrentRevisionId":self.f.r1["revision"]["revisionId"],
            "songSpec":self.f.fixture.spec,"sourceAssetDigests":[],
            "outputArtifactIds":[digest]},commit=True)
        self.base=self.source["revision"]["revisionId"]
        self.provider=AceStepProvider(endpoint_url="https://models.example",
                 checkpoint_dir="",checkpoint_sha256="a"*64,poll_interval=0)
    def tearDown(self):self.f.tearDown()
    def args(self,key="repaint-A"):
        return self.f._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
            base_revision_id=self.base, expected_current_revision_id=self.base,
            idempotency_key=key,synthesize_to_stage_fn=self.provider,
            params={"edit_mode":"repaint","start_bar":2,"end_bar":3,
                    "target_track_id":"bass","music_length_ms":10000})
    def test_repaint_requires_lawful_source_audio_before_remote_call(self):
        f=native.NativeAttemptTests();f.setUp()
        try:
            owner=studio.make_m045_native_owner(f.root)
            with patch("m045_acestep_provider.urllib.request.urlopen") as remote:
                with self.assertRaisesRegex(studio.ProjectConflict,"base audio"):
                    owner.execute_attempt(**f._kwargs(model_id="ace-step-1.5",
                        model_version="ace-step-1.5",params=self.args()["params"],
                        synthesize_to_stage_fn=self.provider))
                remote.assert_not_called()
        finally:f.tearDown()
    def test_sonic_lock_denies_repaint_before_remote_call(self):
        locked={**self.f.fixture.spec,"tracks":[{**track,"sonic_lock":True}
                   for track in self.f.fixture.spec["tracks"]]}
        lock=studio.project_operation(self.f.root,{"projectId":self.f.pid,
           "expectedCurrentRevisionId":self.base,"songSpec":locked,
           "sourceAssetDigests":[],"outputArtifactIds":[self.source["revision"]["outputArtifactIds"][0]]},
           commit=True)
        with patch("m045_acestep_provider.urllib.request.urlopen") as remote:
            with self.assertRaisesRegex(studio.ProjectConflict,"Sonic Lock"):
                studio.make_m045_native_owner(self.f.root).execute_attempt(**{
                  **self.args(), "base_revision_id":lock["revision"]["revisionId"],
                  "expected_current_revision_id":lock["revision"]["revisionId"],
                  "song_spec":locked})
            remote.assert_not_called()
    def test_locked_section_intersection_denies_repaint_before_remote_call(self):
        locked={**self.f.fixture.spec,"structure":{"sections":[
            {**sec,"sonic_lock":True} if sec["id"]=="s1" else sec
            for sec in self.f.fixture.spec["structure"]["sections"]]}}
        r=studio.project_operation(self.f.root,{"projectId":self.f.pid,
            "expectedCurrentRevisionId":self.base,"songSpec":locked,
            "sourceAssetDigests":[],"outputArtifactIds":[self.source["revision"]["outputArtifactIds"][0]]},
            commit=True)
        with patch("m045_acestep_provider.urllib.request.urlopen") as remote:
            with self.assertRaisesRegex(studio.ProjectConflict,"Sonic Lock"):
                studio.make_m045_native_owner(self.f.root).execute_attempt(**{
                    **self.args(), "song_spec":locked,
                    "base_revision_id":r["revision"]["revisionId"],
                    "expected_current_revision_id":r["revision"]["revisionId"]})
            remote.assert_not_called()

    def test_official_multipart_repaint_splices_exact_outside_samples_and_recovers(self):
        calls=[]
        def transport(request,timeout=None):
            url=request.full_url
            calls.append(url)
            if url.endswith("/release_task"):
                content=request.data
                self.assertIn(b'name="src_audio"; filename="source.wav"',content)
                self.assertIn(b'name="task_type"',content)
                self.assertIn(b'repaint',content)
                self.assertIn(b'name="chunk_mask_mode"',content)
                self.assertIn(b'explicit',content)
                self.assertIn(b'name="repainting_start"',content)
                self.assertIn(b'2.5',content)
                self.assertIn(b'name="repainting_end"',content)
                self.assertIn(b'5.0',content)
                self.assertIn(self.src,content)
                return Reply({"task_id":"repaint-accepted-1"})
            if url.endswith("/query_result"):
                return Reply([{"task_id":"repaint-accepted-1","status":1,
                   "result":json.dumps([{"file":"/v1/audio?path=%2Ftmp%2Frepaint.wav"}])}])
            return Reply(self.candidate)
        owner=studio.make_m045_native_owner(self.f.root)
        with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
            result=owner.execute_attempt(**self.args())
        self.assertEqual(result["state"],"COMMITTED")
        self.assertEqual(result["attempt"]["provenance"]["preservation_tier"],"P1")
        self.assertEqual(result["attempt"]["provenance"]["fade_samples"],220)
        self.assertEqual(result["attempt"]["provenance"]["fade_curve"],
                         "RAISED_COSINE_WITHIN_EDIT_ONLY")
        digest=result["attempt"]["artifact_digest"]
        r3=result["revision"]["revisionId"]
        self.assertEqual(studio.project_operation(self.f.root,{"projectId":self.f.pid})["manifest"]["currentRevisionId"],r3)
        audio=studio.project_audio_bytes(self.f.root,{"projectId":self.f.pid,"revisionId":r3,"artifactId":digest})
        source_pcm,_=read_pcm16_wav(self.src)
        output_pcm,_=read_pcm16_wav(audio)
        a,b=110250,220500
        self.assertEqual(output_pcm[:a*4],source_pcm[:a*4])
        self.assertEqual(output_pcm[b*4:],source_pcm[b*4:])
        self.assertNotEqual(output_pcm[a*4:b*4],source_pcm[a*4:b*4])
        self.assertEqual(studio.project_audio_bytes(self.f.root,{"projectId":self.f.pid,
             "revisionId":self.base,"artifactId":hashlib.sha256(self.src).hexdigest()}),self.src)
        cold=studio.make_m045_native_owner(self.f.root).reconcile_attempt(
             headers=self.args()["headers"],project_id=self.f.pid,idempotency_key="repaint-A")
        self.assertEqual(cold["revision"]["revisionId"],r3)
        self.assertEqual(sum(u.endswith("/release_task") for u in calls),1)

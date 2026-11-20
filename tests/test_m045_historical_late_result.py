import pathlib,sys,unittest,urllib.error,json,hashlib,wave,io
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import studio_server as server
import test_m045_native_attempt as native
from m045_acestep_provider import AceStepProvider
class Resp:
 def __init__(self,data):
  self.payload=data if isinstance(data,bytes) else json.dumps({"code":200,"error":None,"data":data}).encode()
  self.headers={"Content-Type":"application/json"}
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def read(self,n=-1):
  r=self.payload if n<0 else self.payload[:n];self.payload=self.payload[len(r):];return r
class HistoricalLateResultTests(unittest.TestCase):
 def test_late_ace_generation_preserves_newer_current_revision(self):
  f=native.NativeAttemptTests();f.setUp()
  try:
   provider=AceStepProvider(endpoint_url="https://host.example",checkpoint_dir="",
      checkpoint_sha256="a"*64,poll_interval=0)
   initial=0
   def fake(req,timeout=None):
    nonlocal initial
    if req.full_url.endswith("/release_task"):return Resp({"task_id":"late-original-1"})
    if req.full_url.endswith("/query_result"):
     initial+=1
     if initial==1:raise urllib.error.URLError("poll interrupted")
     return Resp([{"task_id":"late-original-1","status":1,
        "result":json.dumps([{"file":"/v1/audio?path=%2Ftmp%2Flate.wav"}])}])
    return Resp(f.bytes)
   owner=server.make_m045_native_owner(f.root)
   kw=f._kwargs(model_id="ace-step-1.5",model_version="ace-step-1.5",
       idempotency_key="late-history-1",params={"music_length_ms":12000},
       synthesize_to_stage_fn=provider)
   with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=fake):
    with self.assertRaises(Exception):owner.execute_attempt(**kw)
    r2=server.project_operation(f.root,{"projectId":f.pid,
      "expectedCurrentRevisionId":f.r1["revision"]["revisionId"],
      "songSpec":f.fixture.spec,"sourceAssetDigests":[],
      "outputArtifactIds":[]},commit=True)
    r3id=r2["revision"]["revisionId"]
    recovered=server.make_m045_native_owner(f.root).reconcile_attempt(headers=kw["headers"],project_id=f.pid,
       idempotency_key=kw["idempotency_key"],synthesize_to_stage_fn=provider)
   self.assertEqual(recovered["state"],"ASSOCIATED_HISTORICAL")
   self.assertEqual(recovered["revision"]["revisionId"], f.r1["revision"]["revisionId"])
   historical_audio = server.project_audio_bytes(f.root, {
       "projectId": f.pid, "revisionId": f.r1["revision"]["revisionId"],
       "artifactId": recovered["attempt"]["artifact_digest"]})
   self.assertEqual(hashlib.sha256(historical_audio).hexdigest(),
                    recovered["attempt"]["artifact_digest"])
   with wave.open(io.BytesIO(historical_audio), "rb") as audio:
    self.assertEqual(audio.getframerate(),44100)
    self.assertEqual(audio.getnchannels(),2)
    self.assertEqual(audio.getsampwidth(),2)
   current=server.project_operation(f.root,{"projectId":f.pid})["manifest"]["currentRevisionId"]
   self.assertEqual(current,r3id)
   reopened=server.make_m045_native_owner(f.root).reconcile_attempt(headers=kw['headers'], project_id=f.pid, idempotency_key=kw['idempotency_key'])
   self.assertEqual(reopened['state'], 'ASSOCIATED_HISTORICAL')
   self.assertEqual(reopened['attempt']['artifact_digest'], recovered['attempt']['artifact_digest'])
   owner2 = server.make_m045_native_owner(f.root)
   # All associations come from the existing historical-render authority.
   history = f.root / "projects" / f.pid / "historical-renders"
   receipts = list(history.glob("m045:*.json"))
   self.assertEqual(len(receipts), 1)
   self.assertEqual(json.loads(receipts[0].read_text())["revisionId"],
                    f.r1["revision"]["revisionId"])
   self.assertEqual(len(owner2.list_project_revisions(f.pid)), 2)
   self.assertEqual(server.project_operation(f.root, {"projectId": f.pid})["manifest"]["currentRevisionId"], r3id)
  finally:f.tearDown()

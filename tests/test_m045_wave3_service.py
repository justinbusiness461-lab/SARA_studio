"""Wave003 TDD: lawful revision-bound analysis and preview are not CAS publications."""
import base64, hashlib, io, json, socketserver, struct, sys, threading, unittest, urllib.error, urllib.request, wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import studio_server as studio
import test_m044_operations as fixtures
from m045_fm_preview_synth import render_fm_preview_wav

class Wave3HTTPTests(unittest.TestCase):
 def setUp(self):
  self.fx=fixtures.OperationTests();self.fx.setUp()
  self.root=self.fx.root;self.pid=self.fx.pid
  self.wav=render_fm_preview_wav(notes=[{"midi_note":36,"start_tick":0,"duration_ticks":480,"velocity":110}],bpm=96,total_bars=1)
  self.digest=hashlib.sha256(self.wav).hexdigest()
  studio._publish_cas_exact(self.root,self.digest,self.wav)
  self.saved=studio.project_operation(self.root,{
   "projectId":self.pid,"expectedCurrentRevisionId":self.fx.r1["revision"]["revisionId"],
   "songSpec":self.fx.spec,"sourceAssetDigests":[], "outputArtifactIds":[self.digest]},commit=True)
  self.rid=self.saved["revision"]["revisionId"]
  self.before=studio.project_operation(self.root,{"projectId":self.pid})["manifest"]["currentRevisionId"]
  self.original_root,self.original_port=studio.EXPORT_ROOT,studio.PORT
  self.server=socketserver.TCPServer(("127.0.0.1",0),studio.StudioHandler)
  studio.EXPORT_ROOT=self.root;studio.PORT=self.server.server_address[1]
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.session=studio.issue_studio_session(studio.LOCAL_PRINCIPAL_ID)
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
  studio.EXPORT_ROOT=self.original_root;studio.PORT=self.original_port
  self.fx.tearDown()
 def request(self,path,body,*,session=None,capability=True):
  headers={"Content-Type":"application/json","Origin":f"http://127.0.0.1:{studio.PORT}"}
  if capability:headers["X-Studio-Capability"]=studio.CAPABILITY
  if session is not None:headers["X-Studio-Session"]=session
  req=urllib.request.Request(f"http://127.0.0.1:{studio.PORT}{path}",data=json.dumps(body).encode(),headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=20) as response:return response.status,json.loads(response.read())
  except urllib.error.HTTPError as e:
   return e.code,json.loads(e.read())
 def test_authorized_transcribe_is_p3_candidate_not_revision_promotion(self):
  code,body=self.request("/api/m045/transcribe-midi",
   {"projectId":self.pid,"revisionId":self.rid,"artifactId":self.digest},session=self.session)
  self.assertEqual(code,200,body)
  self.assertEqual(body["preservationTier"],"P3_RECONSTRUCTION")
  self.assertEqual(body["sourceArtifactId"],self.digest)
  self.assertEqual(body["ppq"],960)
  self.assertTrue(body["notesDetected"]>=1)
  self.assertIn("<score-partwise",body["musicXml"])
  self.assertEqual(base64.b64decode(body["midiType1Base64"])[:4],b"MThd")
  self.assertEqual(studio.project_operation(self.root,{"projectId":self.pid})["manifest"]["currentRevisionId"],self.before)
 def test_reject_missing_foreign_session_and_unbound_artifact_with_http403(self):
  body={"projectId":self.pid,"revisionId":self.rid,"artifactId":self.digest}
  self.assertEqual(self.request("/api/m045/transcribe-midi",body)[0],403)
  self.assertEqual(self.request("/api/m045/transcribe-midi",body,session=self.session,capability=False)[0],403)
  foreign=studio.issue_studio_session("foreign-principal")
  self.assertEqual(self.request("/api/m045/transcribe-midi",body,session=foreign)[0],403)
  unbound=hashlib.sha256(b"orphan").hexdigest()
  studio._publish_cas_exact(self.root,unbound,b"orphan")
  self.assertEqual(self.request("/api/m045/transcribe-midi",{**body,"artifactId":unbound},session=self.session)[0],403)
 def test_authorized_preview_uses_canonical_song_notes_and_does_not_publish(self):
  body={"projectId":self.pid,"revisionId":self.rid,"sectionId":"s0","trackId":"bass","patch":"fm_bass"}
  code,result=self.request("/api/m045/preview-synth",body,session=self.session)
  self.assertEqual(code,200,result)
  self.assertEqual(result["sourceRevisionId"],self.rid)
  self.assertEqual(result["audioStatus"],"PREVIEW_NOT_PUBLISHED")
  pcm=base64.b64decode(result["wavBase64"])
  with wave.open(io.BytesIO(pcm),"rb") as w:
   self.assertEqual((w.getnchannels(),w.getframerate(),w.getsampwidth()),(2,44100,2))
   self.assertGreater(w.getnframes(),100)
  self.assertEqual(hashlib.sha256(pcm).hexdigest(),result["previewSha256"])
  self.assertEqual(studio.project_operation(self.root,{"projectId":self.pid})["manifest"]["currentRevisionId"],self.before)
 def test_preview_denies_foreign_actor_and_unsupported_client_notes(self):
  body={"projectId":self.pid,"revisionId":self.rid,"sectionId":"s0","trackId":"bass"}
  self.assertEqual(self.request("/api/m045/preview-synth",body)[0],403)
  foreign=studio.issue_studio_session("foreign-principal")
  self.assertEqual(self.request("/api/m045/preview-synth",body,session=foreign)[0],403)
  self.assertEqual(self.request("/api/m045/preview-synth",{**body,"notes":[{"midi_note":127}]},session=self.session)[0],400)
  self.assertEqual(self.request("/api/m045/transcribe-midi",{"projectId":self.pid,"revisionId":self.rid,"artifactId":self.digest,"promoteToP0":True},session=self.session)[0],400)

if __name__=="__main__":unittest.main()

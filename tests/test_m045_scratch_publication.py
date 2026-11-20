"""Studio-owned publication of bounded scratch output with source-revision membership."""
import hashlib,io,struct,sys,unittest,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import studio_server as studio
from test_m045_dj_event_authority import ScratchAuthorityTests
from m045_scratch_dsp import waveform_pcm

def wav(count,amplitude):
 b=io.BytesIO()
 with wave.open(b,"wb") as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
  w.writeframes(struct.pack("<hh",amplitude,-amplitude)*count)
 return b.getvalue()

class ScratchPublicationTests(unittest.TestCase):
 def setUp(self):
  self.fx=ScratchAuthorityTests();self.fx.setUp()
  self.root=self.fx.fx.root
  self.pid=self.fx.fx.pid
  self.spec=self.fx.spec()
  self.master=wav(88200,0)
  self.sample=wav(12000,7500)
  self.master_id=hashlib.sha256(self.master).hexdigest()
  self.sample_id=hashlib.sha256(self.sample).hexdigest()
  studio._publish_cas_exact(self.root,self.master_id,self.master)
  studio._publish_cas_exact(self.root,self.sample_id,self.sample)
  self.saved=studio.project_operation(self.root,{
    "projectId":self.pid,"expectedCurrentRevisionId":self.fx.fx.r1["revision"]["revisionId"],
    "songSpec":self.spec,"sourceAssetDigests":[self.sample_id],
    "outputArtifactIds":[self.master_id]},commit=True)
  self.rid=self.saved["revision"]["revisionId"]
  self.eid=self.spec["tracks"][-1]["events"][0]["event_id"]
 def tearDown(self):self.fx.tearDown()
 def params(self,**changes):
  data={"projectId":self.pid,"revisionId":self.rid,
        "baseArtifactId":self.master_id,"sampleAssetDigests":{self.eid:self.sample_id}}
  data.update(changes)
  return data
 def test_authenticated_revision_source_yields_lawful_pcm16_output_and_preserves_other_samples(self):
  rendered=studio.render_authorized_scratch_operation(self.root,self.params())
  self.assertEqual(rendered["sourceRevisionId"],self.rid)
  digest=rendered["artifactId"]
  self.assertNotEqual(digest,self.master_id)
  data=studio.project_audio_bytes(self.root,{"projectId":self.pid,"revisionId":rendered["revisionId"],"artifactId":digest})
  b,_=waveform_pcm(self.master);p,_=waveform_pcm(data)
  marker=self.spec["tracks"][-1]["events"][0]
  bpm=self.spec["timebase"]["initial_bpm"]
  n=(2*480*60*44100+bpm*960)//(2*bpm*960)
  a=marker["sample_index"]
  self.assertEqual(b[:a*4],p[:a*4])
  self.assertEqual(b[(a+n)*4:],p[(a+n)*4:])
  self.assertNotEqual(b[a*4:(a+n)*4],p[a*4:(a+n)*4])
  again=studio.render_authorized_scratch_operation(self.root,self.params())
  self.assertEqual(again["artifactId"],digest)
 def test_unbound_source_and_wrong_base_artifact_fail_without_publication(self):
  bad_id=hashlib.sha256(wav(100,44)).hexdigest()
  studio._publish_cas_exact(self.root,bad_id,wav(100,44))
  with self.assertRaises(studio.ProjectConflict):
   studio.render_authorized_scratch_operation(self.root,self.params(sampleAssetDigests={self.eid:bad_id}))
  with self.assertRaises(studio.ProjectConflict):
   studio.render_authorized_scratch_operation(self.root,self.params(baseArtifactId=self.sample_id))
 def test_wrong_project_principal_denied(self):
  with self.assertRaises(Exception):
   studio.render_authorized_scratch_operation(self.root,self.params(),principal_id="not-project-owner")

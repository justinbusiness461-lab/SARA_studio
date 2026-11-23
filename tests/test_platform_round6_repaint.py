"""R6 RED-first selective repaint under authenticated single-use Chat approval."""
import copy,hashlib,io,json,struct,unittest,wave
from pathlib import Path
import studio_server as studio
from test_platform_identity_and_catalog import PlatformHTTP
from m045_repaint import read_pcm16_wav,bar_sample_window

def wav(frames,level):
 buf=io.BytesIO()
 with wave.open(buf,"wb") as f:
  f.setnchannels(2);f.setsampwidth(2);f.setframerate(44100)
  f.writeframes(struct.pack("<hh",level,-level)*frames)
 return buf.getvalue()

class QualifiedP2TestRepaint:
 supports_repaint=True
 model_id="repaint-test"
 model_version="test-v1"
 def __call__(self,stage,spec,prompt,lyrics,seed,params):
  source=(Path(stage)/"repaint-source.wav").read_bytes()
  frames=read_pcm16_wav(source)[1]
  (Path(stage)/"provider-receipt.json").write_text(json.dumps({
      "source_type":"EXTERNAL_COMMERCIAL_PROVIDER","rights_status":"PROVIDER_TERMS_UNVERIFIED",
      "preservation_tier":"P2","model_id":self.model_id,"model_version":self.model_version}))
  result=Path(stage)/"output.wav"
  result.write_bytes(wav(frames,6000))
  return result

class ApprovedRepaintHTTP(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.a=self.fx.signup();self.cookie,_=self.fx.login()
  initial=self.fx.project(self.a["principalId"])
  old=studio.project_operation(self.fx.root,{"projectId":initial["projectId"]},principal_id=self.a["principalId"])
  spec=copy.deepcopy(old["songSpec"])
  spec["timebase"].update({"sample_rate":44100,"meter":"4/4","ticks_per_quarter_note":960})
  data=wav(441000,1200)
  digest=hashlib.sha256(data).hexdigest()
  studio._publish_cas_exact(self.fx.root,digest,data)
  newer=studio.project_operation(self.fx.root,{"projectId":initial["projectId"],
      "expectedCurrentRevisionId":initial["revisionId"],"songSpec":spec,
      "outputArtifactIds":[digest]},commit=True,principal_id=self.a["principalId"])
  self.base_audio=data
  self.ctx={"projectId":initial["projectId"],"revisionId":newer["revision"]["revisionId"],
      "artifactId":digest,"selectedTrackId":"lead","selectedBars":[2]}
  self.old_provider=studio.M045_SYNTHESIZE_TO_STAGE
  self.addCleanup(setattr,studio,"M045_SYNTHESIZE_TO_STAGE",self.old_provider)
 def ask(self):
  return self.fx.api("/api/m045/chat",{"instruction":"Repaint the lead darker in bar two",
    "context":self.ctx},cookie=self.cookie)
 def approve(self,challenge):
  return self.fx.api("/api/m045/chat/approve",{
     "approval_challenge_id":challenge,"expected_current_revision_id":self.ctx["revisionId"]},cookie=self.cookie)
 def current(self):
  return studio.project_operation(self.fx.root,{"projectId":self.ctx["projectId"]},principal_id=self.a["principalId"])
 def test_absent_host_provider_must_not_fake_a_repaint_or_publish_audio(self):
  studio.M045_SYNTHESIZE_TO_STAGE=None
  s,_,offer=self.ask()
  self.assertEqual(s,200,offer)
  self.assertEqual(offer["state"],"APPROVAL_REQUIRED")
  challenge=offer["approval_challenge_id"]
  self.assertEqual(self.approve(challenge)[0],503)
  self.assertEqual(self.approve(challenge)[0],403)
  self.assertEqual(self.current()["revision"]["revisionId"],self.ctx["revisionId"])
 def test_approved_p1_exact_pcm_outside_region_and_replay_denied(self):
  studio.M045_SYNTHESIZE_TO_STAGE={"repaint-test":QualifiedP2TestRepaint()}
  s,_,offer=self.ask();self.assertEqual((s,offer["state"]),(200,"APPROVAL_REQUIRED"),offer)
  challenge=offer["approval_challenge_id"]
  s,_,out=self.approve(challenge)
  self.assertEqual(s,200,out)
  self.assertTrue(out["revisionCommitted"])
  self.assertEqual(out["operationResult"]["preservationTier"],"P1")
  current=self.current()
  self.assertNotEqual(current["revision"]["revisionId"],self.ctx["revisionId"])
  rendered=studio.project_audio_bytes(self.fx.root,{"projectId":self.ctx["projectId"],
       "revisionId":current["revision"]["revisionId"],
       "artifactId":out["operationResult"]["artifactId"]},principal_id=self.a["principalId"])
  old,n=read_pcm16_wav(self.base_audio)
  new,n2=read_pcm16_wav(rendered)
  start,end=bar_sample_window(current["songSpec"],2,3,n)
  self.assertEqual(n,n2)
  self.assertEqual(new[:start*4],old[:start*4])
  self.assertEqual(new[end*4:],old[end*4:])
  self.assertNotEqual(new[start*4:end*4],old[start*4:end*4])
  self.assertEqual(studio.project_audio_bytes(self.fx.root,{"projectId":self.ctx["projectId"],
      "revisionId":self.ctx["revisionId"],"artifactId":self.ctx["artifactId"]},
      principal_id=self.a["principalId"]),self.base_audio)
  self.assertEqual(self.approve(challenge)[0],403)
 def test_locked_track_and_stale_source_fail_closed_without_new_approval_effect(self):
  studio.M045_SYNTHESIZE_TO_STAGE={"repaint-test":QualifiedP2TestRepaint()}
  ch=self.ask()[2]["approval_challenge_id"]
  old=self.current();spec=copy.deepcopy(old["songSpec"])
  spec["tracks"][0]["sonic_lock"]=True
  latest=studio.project_operation(self.fx.root,{"projectId":self.ctx["projectId"],
     "expectedCurrentRevisionId":self.ctx["revisionId"],"songSpec":spec,
     "outputArtifactIds":[self.ctx["artifactId"]]},commit=True,principal_id=self.a["principalId"])
  self.assertEqual(self.approve(ch)[0],409)
  self.assertEqual(self.current()["revision"]["revisionId"],latest["revision"]["revisionId"])
  self.ctx["revisionId"]=latest["revision"]["revisionId"]
  ch=self.ask()[2]["approval_challenge_id"]
  self.assertIn(self.approve(ch)[0],(403,409))
  self.assertEqual(self.current()["revision"]["revisionId"],self.ctx["revisionId"])
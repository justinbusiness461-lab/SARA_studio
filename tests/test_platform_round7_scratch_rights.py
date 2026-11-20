"""R7-A RED: rights-bound physical scratch WAV via authenticated Studio owner."""
import copy,hashlib,io,struct,unittest,wave,json,subprocess,tempfile
from test_platform_identity_and_catalog import PlatformHTTP
import studio_server as studio
from m045_scratch_dsp import waveform_pcm

def wav(frames,amp):
 b=io.BytesIO()
 with wave.open(b,"wb") as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
  w.writeframes(struct.pack("<hh",amp,-amp)*frames)
 return b.getvalue()

class RightsBoundScratchHTTP(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.owner=self.fx.signup()
  self.cookie,_=self.fx.login()
  initial=self.fx.project(self.owner["principalId"])
  current=studio.project_operation(self.fx.root,{"projectId":initial["projectId"]},
                                       principal_id=self.owner["principalId"])
  spec=copy.deepcopy(current["songSpec"])
  spec["timebase"].update({"meter":"4/4","sample_rate":44100,"ticks_per_quarter_note":960})
  spec["tracks"].append({"track_id":"dj_scratch","name":"Scratch Surgeon","type":"DJ",
    "muted":False,"sonic_lock":False,"volume_db":0,"pan":0,"events":[{
      "type":"DJ_SCRATCH_MARKER","event_id":"dj:intro:0:A","tick":0,
      "duration_ticks":480,"deck":"A","technique":"chirp","sample_index":0,
      "audio_status":"UNRENDERED_SOURCE_ASSET_REQUIRED"}]})
  self.sample=wav(6000,2200);self.sample_id=hashlib.sha256(self.sample).hexdigest()
  studio._publish_cas_exact(self.fx.root,self.sample_id,self.sample)
  revised=studio.project_operation(self.fx.root,{
    "projectId":initial["projectId"],"expectedCurrentRevisionId":initial["revisionId"],
    "songSpec":spec,"sourceAssetDigests":[self.sample_id],
    "outputArtifactIds":[initial["artifactId"]]},commit=True,principal_id=self.owner["principalId"])
  self.ref={k:v for k,v in initial.items() if k in ("projectId","artifactId","sourceAudio")}
  self.ref["revisionId"]=revised["revision"]["revisionId"]
  self.eid="dj:intro:0:A"
  self.request={"projectId":initial["projectId"],"revisionId":self.ref["revisionId"],
    "baseArtifactId":initial["artifactId"],
    "sampleAssetDigests":{self.eid:self.sample_id}}
  self.old_policy=getattr(studio,"PLATFORM_SCRATCH_RIGHTS_POLICY",None)
  self.addCleanup(setattr,studio,"PLATFORM_SCRATCH_RIGHTS_POLICY",self.old_policy)
 def render(self,**changes):
  return self.fx.api("/api/m045/scratch/render",{**self.request,**changes},cookie=self.cookie)
 def configure_rights(self,decision):
  studio.configure_platform_scratch_sample_rights(lambda principal,pid,rid,event,digest:
    decision if (principal,pid,rid,event,digest)==
    (self.owner["principalId"],self.ref["projectId"],self.ref["revisionId"],self.eid,self.sample_id)
    else None)
 def test_missing_host_policy_and_spoofed_rights_fail_closed(self):
  self.assertEqual(self.render()[0],503)
  self.assertEqual(self.render(rightsStatus="ARTIST_ORIGINAL")[0],400)
  self.assertEqual(studio.project_operation(self.fx.root,{"projectId":self.ref["projectId"]},
    principal_id=self.owner["principalId"])["revision"]["revisionId"],self.ref["revisionId"])
 def test_host_denial_then_verified_rights_produces_exact_pcm_wav_revision(self):
  self.configure_rights(None)
  self.assertEqual(self.render()[0],403)
  self.configure_rights("ARTIST_ORIGINAL")
  code,_,result=self.render();self.assertEqual(code,200,result)
  self.assertEqual(result["sampleRightsStatus"],"ARTIST_ORIGINAL")
  self.assertFalse(result["creativeApproved"])
  self.assertEqual(result["preservationTier"],"P1")
  selected=studio.project_operation(self.fx.root,{"projectId":self.ref["projectId"]},
    principal_id=self.owner["principalId"])
  self.assertEqual(selected["revision"]["revisionId"],result["revisionId"])
  output=studio.project_audio_bytes(self.fx.root,{"projectId":self.ref["projectId"],
    "revisionId":result["revisionId"],"artifactId":result["artifactId"]},
     principal_id=self.owner["principalId"])
  old,frames=waveform_pcm(self.ref["sourceAudio"])
  new,n=waveform_pcm(output)
  self.assertEqual(n,frames)
  window=(2*480*60*44100+120*960)//(2*120*960)
  self.assertNotEqual(new[:window*4],old[:window*4])
  self.assertEqual(new[window*4:],old[window*4:])
  # Independent physical container inspection and PCM16 decoder,
  # separate from Studio WAV parser and Scratch Surgeon DSP.
  with tempfile.TemporaryDirectory() as td:
   path=str(__import__("pathlib").Path(td)/"scratch-bound.wav")
   __import__("pathlib").Path(path).write_bytes(output)
   probe=subprocess.run(["ffprobe","-v","error","-select_streams","a:0",
       "-show_entries","stream=codec_name,sample_rate,channels",
       "-of","json",path],capture_output=True,text=True,check=True,timeout=15)
   meta=json.loads(probe.stdout)["streams"][0]
   self.assertEqual((meta["codec_name"],meta["sample_rate"],meta["channels"]),
       ("pcm_s16le","44100",2))
   decoded=subprocess.run(["ffmpeg","-v","error","-i",path,
       "-f","s16le","-acodec","pcm_s16le","-ar","44100","-ac","2","pipe:1"],
       capture_output=True,check=True,timeout=15).stdout
   self.assertEqual(decoded,new)
  self.assertEqual(studio.project_audio_bytes(self.fx.root,{"projectId":self.ref["projectId"],
      "revisionId":self.ref["revisionId"],"artifactId":self.ref["artifactId"]},
      principal_id=self.owner["principalId"]),self.ref["sourceAudio"])
 def test_unbound_sample_and_foreign_principal_never_earn_rights(self):
  self.configure_rights("ARTIST_ORIGINAL")
  self.assertIn(self.render(sampleAssetDigests={self.eid:"f"*64})[0],(403,409))
  self.fx.signup("other_artist","long secure different password!")
  foreign,_=self.fx.login("other_artist","long secure different password!")
  self.assertEqual(self.fx.api("/api/m045/scratch/render",self.request,cookie=foreign)[0],403)
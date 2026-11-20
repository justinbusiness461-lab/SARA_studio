"""R7-B RED: exact dry-stem mix recipe reconstruction bound to Studio history."""
import copy,hashlib,struct,subprocess,sys,unittest,tempfile,json
import studio_server as studio
from test_platform_identity_and_catalog import PlatformHTTP
from m045_stem_reconstruction import reconstruct_master

class OwnedMixRecipe(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.owner=self.fx.signup();self.cookie,_=self.fx.login()
  initial=self.fx.project(self.owner["principalId"])
  self.stems=[
    b"".join(struct.pack("<dd",0.2 if i%2==0 else 0.1,0.08) for i in range(1200)),
    b"".join(struct.pack("<dd",0.01,-0.03) for i in range(1200))]
  self.stems.sort(key=lambda x:hashlib.sha256(x).hexdigest())
  self.ids=[hashlib.sha256(x).hexdigest() for x in self.stems]
  for sha,data in zip(self.ids,self.stems):
   studio._publish_cas_exact(self.fx.root,sha,data)
  selected=studio.project_operation(self.fx.root,{"projectId":initial["projectId"]},principal_id=self.owner["principalId"])
  saved=studio.project_operation(self.fx.root,{"projectId":initial["projectId"],
     "expectedCurrentRevisionId":initial["revisionId"],"songSpec":copy.deepcopy(selected["songSpec"]),
     "sourceAssetDigests":self.ids,
     "outputArtifactIds":[initial["artifactId"]]},commit=True,principal_id=self.owner["principalId"])
  self.rid=saved["revision"]["revisionId"]
  self.pid=initial["projectId"]
  self.recipe={"schema_version":"sara.mix.recipe.v1",
     "source_project_revision_id":self.rid,
     "production_timeline_digest":saved["revision"]["productionTimelineDigest"],
     "stem_artifact_ids":self.ids,
     "bus_waveshaper":"tanh","fade_ms":5.0,"target_peak":0.84,
     "sample_rate":44100,"channels":2,"sample_count":1200,
     "pcm_quantizer":"signed16_round_nearest_ties_even",
     "encoder":"canonical_pcm16_wav_44"}
  self.request={"projectId":self.pid,"expectedCurrentRevisionId":self.rid,"mixRecipe":self.recipe}
 def read(self):
  return studio.project_operation(self.fx.root,{"projectId":self.pid},principal_id=self.owner["principalId"])
 def test_exact_authorized_recipe_produces_revision_bound_wav_and_cold_reconstruction(self):
  from m045_stem_reconstruction_owner import authorized_reconstruct_mix
  result=authorized_reconstruct_mix(self.fx.root,self.request,self.owner["principalId"])
  self.assertEqual(result["state"],"RENDERED_BOUND")
  self.assertFalse(result["releaseCleared"])
  selected=self.read()
  self.assertEqual(selected["revision"]["revisionId"],result["revisionId"])
  output=studio.project_audio_bytes(self.fx.root,{"projectId":self.pid,
      "revisionId":result["revisionId"],"artifactId":result["artifactId"]},
      principal_id=self.owner["principalId"])
  self.assertEqual(output,reconstruct_master(self.stems,self.recipe))
  self.assertEqual(hashlib.sha256(output).hexdigest(),result["artifactId"])
  with tempfile.TemporaryDirectory() as td:
   from pathlib import Path
   path=str(Path(td)/"dry-stem.wav");Path(path).write_bytes(output)
   ffprobe=subprocess.run(["ffprobe","-v","error","-select_streams","a:0",
     "-show_entries","stream=codec_name,sample_rate,channels",
     "-of","json",path],capture_output=True,text=True,check=True,timeout=15)
   meta=json.loads(ffprobe.stdout)["streams"][0]
   self.assertEqual((meta["codec_name"],meta["sample_rate"],meta["channels"]),
      ("pcm_s16le","44100",2))
   decoded=subprocess.run(["ffmpeg","-v","error","-i",path,
     "-f","s16le","-acodec","pcm_s16le","-ar","44100","-ac","2","pipe:1"],
     capture_output=True,check=True,timeout=15).stdout
   self.assertEqual(decoded,output[44:])
  self.assertEqual(self.read()["revision"]["sourceAssetDigests"],sorted(self.ids))
  old=studio.project_operation(self.fx.root,{"projectId":self.pid,"revisionId":self.rid},
      principal_id=self.owner["principalId"])
  self.assertEqual(old["revision"]["revisionId"],self.rid)
 def test_wrong_recipe_timeline_and_foreign_principal_denied_before_publication(self):
  from m045_stem_reconstruction_owner import authorized_reconstruct_mix
  wrong={**self.request,"mixRecipe":{**self.recipe,"production_timeline_digest":"f"*64}}
  with self.assertRaises(studio.ProjectConflict):
   authorized_reconstruct_mix(self.fx.root,wrong,self.owner["principalId"])
  wrong={**self.request,"mixRecipe":{**self.recipe,"stem_artifact_ids":list(reversed(self.ids))}}
  with self.assertRaises(Exception):
   authorized_reconstruct_mix(self.fx.root,wrong,self.owner["principalId"])
  with self.assertRaises(Exception):
   authorized_reconstruct_mix(self.fx.root,self.request,"other-principal")
  self.assertEqual(self.read()["revision"]["revisionId"],self.rid)
 def test_locked_tracks_reject_rendering_from_reinterpretation(self):
  from m045_stem_reconstruction_owner import authorized_reconstruct_mix
  selected=self.read();spec=copy.deepcopy(selected["songSpec"])
  spec["tracks"][0]["sonic_lock"]=True
  new=studio.project_operation(self.fx.root,{"projectId":self.pid,
      "expectedCurrentRevisionId":self.rid,"songSpec":spec,
      "sourceAssetDigests":self.ids,"outputArtifactIds":selected["revision"]["outputArtifactIds"]},
      commit=True,principal_id=self.owner["principalId"])
  self.recipe["source_project_revision_id"]=new["revision"]["revisionId"]
  self.recipe["production_timeline_digest"]=new["revision"]["productionTimelineDigest"]
  self.request["expectedCurrentRevisionId"]=new["revision"]["revisionId"]
  with self.assertRaises(studio.ProjectConflict):
   authorized_reconstruct_mix(self.fx.root,self.request,self.owner["principalId"])
  self.assertEqual(self.read()["revision"]["revisionId"],new["revision"]["revisionId"])
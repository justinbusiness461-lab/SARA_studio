"""R6 RED-first approved, exact, unrendered DJ Scratch Surgeon event."""
import copy,unittest
import studio_server as studio
from test_platform_identity_and_catalog import PlatformHTTP

class ApprovedDJEventHTTP(unittest.TestCase):
 def setUp(self):
  self.fx=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.a=self.fx.signup();self.cookie,_=self.fx.login()
  initial=self.fx.project(self.a["principalId"])
  chosen=studio.project_operation(self.fx.root,{"projectId":initial["projectId"]},principal_id=self.a["principalId"])
  spec=copy.deepcopy(chosen["songSpec"])
  spec["timebase"].update({"sample_rate":44100,"meter":"4/4","ticks_per_quarter_note":960})
  spec["structure"]["sections"][0]["end_tick"]=7680
  spec["tracks"].append({"track_id":"dj_scratch","name":"Scratch Surgeon","type":"DJ","muted":False,"sonic_lock":False,"volume_db":0,"pan":0,"events":[]})
  saved=studio.project_operation(self.fx.root,{"projectId":initial["projectId"],
     "expectedCurrentRevisionId":initial["revisionId"],"songSpec":spec,
     "outputArtifactIds":[initial["artifactId"]]},commit=True,principal_id=self.a["principalId"])
  self.ctx={"projectId":initial["projectId"],"revisionId":saved["revision"]["revisionId"],
    "artifactId":initial["artifactId"],"selectedTrackId":"dj_scratch",
    "selectedBars":[1],"sectionId":"intro","stepIndex":2,"technique":"chirp","deck":"A"}
 def selected(self):
  return studio.project_operation(self.fx.root,{"projectId":self.ctx["projectId"]},principal_id=self.a["principalId"])
 def ask(self):
  return self.fx.api("/api/m045/chat",{"instruction":"Add scratch chirp","context":self.ctx},cookie=self.cookie)
 def approve(self,challenge,cookie=None):
  return self.fx.api("/api/m045/chat/approve",{
     "approval_challenge_id":challenge,
     "expected_current_revision_id":self.ctx["revisionId"]},cookie=cookie or self.cookie)
 def test_valid_approval_commits_exact_symbolic_marker_and_preserves_audio(self):
  old=self.selected()
  code,_,offer=self.ask()
  self.assertEqual(code,200,offer);self.assertEqual(offer["state"],"APPROVAL_REQUIRED")
  challenge=offer["approval_challenge_id"]
  code,_,out=self.approve(challenge)
  self.assertEqual(code,200,out);self.assertTrue(out["revisionCommitted"])
  self.assertEqual(out["operationResult"]["audioStatus"],"UNRENDERED_SOURCE_ASSET_REQUIRED")
  current=self.selected()
  self.assertNotEqual(current["revision"]["revisionId"],self.ctx["revisionId"])
  old_tracks=copy.deepcopy(old["songSpec"]["tracks"])
  new_tracks=copy.deepcopy(current["songSpec"]["tracks"])
  self.assertEqual(old_tracks[0],new_tracks[0])
  self.assertEqual(new_tracks[-1]["events"][0]["type"],"DJ_SCRATCH_MARKER")
  self.assertEqual(new_tracks[-1]["events"][0]["technique"],"chirp")
  self.assertEqual(current["revision"]["outputArtifactIds"],old["revision"]["outputArtifactIds"])
  self.assertEqual(current["revision"]["sourceAssetDigests"],old["revision"]["sourceAssetDigests"])
  self.assertEqual(self.approve(challenge)[0],403)
 def test_locked_section_rejects_approved_scratch_without_child_revision(self):
  current=self.selected();spec=copy.deepcopy(current["songSpec"])
  spec["structure"]["sections"][0]["sonic_lock"]=True
  new=studio.project_operation(self.fx.root,{"projectId":self.ctx["projectId"],
       "expectedCurrentRevisionId":self.ctx["revisionId"],"songSpec":spec,
       "outputArtifactIds":current["revision"]["outputArtifactIds"]},
       commit=True,principal_id=self.a["principalId"])
  self.ctx["revisionId"]=new["revision"]["revisionId"]
  offer=self.ask()[2]
  self.assertEqual(offer["state"],"APPROVAL_REQUIRED")
  self.assertIn(self.approve(offer["approval_challenge_id"])[0],(403,409))
  self.assertEqual(self.selected()["revision"]["revisionId"],self.ctx["revisionId"])
 def test_stale_revision_and_foreign_principal_denied(self):
  challenge=self.ask()[2]["approval_challenge_id"]
  self.fx.signup("second_artist","another strong password!")
  foreign,_=self.fx.login("second_artist","another strong password!")
  self.assertEqual(self.approve(challenge,foreign)[0],403)
  latest=self.selected()
  newer=studio.project_operation(self.fx.root,{"projectId":self.ctx["projectId"],
     "expectedCurrentRevisionId":self.ctx["revisionId"],"songSpec":latest["songSpec"]},
      commit=True,principal_id=self.a["principalId"])
  self.assertEqual(self.approve(challenge)[0],409)
  self.assertEqual(self.selected()["revision"]["revisionId"],newer["revision"]["revisionId"])
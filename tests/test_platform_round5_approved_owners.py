"""Round5 RED-first owner-bound Chat approval tests."""
import copy
import hashlib
import unittest
import studio_server as studio
from m045_soundtrack_grant import HostSigningKeyRing,verify_issued_grant_signature

class Round5ApprovedOwners(unittest.TestCase):
 def setUp(self):
  from test_platform_identity_and_catalog import PlatformHTTP
  self.fx=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.old_ring=studio.M045_GRANT_SIGNING_RING
  self.old_policy=studio.M045_GRANT_RIGHTS_POLICY
  self.addCleanup(self.reset_ring)
  self.owner=self.fx.signup()
  self.cookie,_=self.fx.login()
  self.ref=self.fx.project(self.owner["principalId"])
  self.ctx={k:self.ref[k] for k in ("projectId","revisionId","artifactId")}
 def reset_ring(self):
  studio.M045_GRANT_SIGNING_RING=self.old_ring
  studio.M045_GRANT_RIGHTS_POLICY=self.old_policy
 def issue(self,instruction,ctx=None):
  return self.fx.api("/api/m045/chat",
   {"instruction":instruction,"context":self.ctx if ctx is None else ctx},cookie=self.cookie)
 def approve(self,ch,cookie=None):
  return self.fx.api("/api/m045/chat/approve",{
    "approval_challenge_id":ch,
    "expected_current_revision_id":self.ref["revisionId"]},cookie=cookie or self.cookie)
 def selected(self):
  return studio.project_operation(self.fx.root,{"projectId":self.ctx["projectId"]},
   principal_id=self.owner["principalId"])
 def test_lock_approval_commits_exact_single_bit_revision_and_replay_denied(self):
  ctx={**self.ctx,"selectedTrackId":"lead"}
  before=self.selected()
  s,_,offer=self.issue("Toggle Sonic Lock",ctx)
  self.assertEqual(s,200,offer)
  self.assertEqual(offer["state"],"APPROVAL_REQUIRED")
  challenge=offer["approval_challenge_id"]
  s,_,actual=self.approve(challenge)
  self.assertEqual(s,200,actual)
  self.assertTrue(actual["revisionCommitted"])
  after=self.selected()
  self.assertNotEqual(after["manifest"]["currentRevisionId"],self.ctx["revisionId"])
  old=copy.deepcopy(before["songSpec"]);new=copy.deepcopy(after["songSpec"])
  old["tracks"][0]["sonic_lock"]=True
  self.assertEqual(old,new)
  self.assertEqual(after["revision"]["outputArtifactIds"],before["revision"]["outputArtifactIds"])
  self.assertEqual(after["revision"]["sourceAssetDigests"],before["revision"]["sourceAssetDigests"])
  self.assertEqual(self.approve(challenge)[0],403)
 def test_lock_wrong_principal_and_stale_source_fail_closed(self):
  ctx={**self.ctx,"selectedTrackId":"lead"}
  token=self.issue("Toggle Sonic Lock",ctx)[2]["approval_challenge_id"]
  self.fx.signup("other_artist","other strong password")
  other,_=self.fx.login("other_artist","other strong password")
  self.assertEqual(self.approve(token,cookie=other)[0],403)
  newer=studio.project_operation(self.fx.root,{"projectId":self.ctx["projectId"],
    "expectedCurrentRevisionId":self.ctx["revisionId"],"songSpec":self.selected()["songSpec"]},
    commit=True,principal_id=self.owner["principalId"])
  self.assertEqual(self.approve(token)[0],409)
  self.assertEqual(self.selected()["manifest"]["currentRevisionId"],newer["revision"]["revisionId"])
 def test_grant_requires_host_keyring_and_exact_cinema_scope(self):
  ctx={**self.ctx,"cinemaProjectId":"film-rezrxtion-001","sectionId":"intro","fps":"24/1"}
  s,_,offer=self.issue("Create music video grant",ctx)
  self.assertEqual(s,200,offer)
  self.assertEqual(offer["state"],"APPROVAL_REQUIRED")
  self.assertEqual(self.approve(offer["approval_challenge_id"])[0],503)
  self.assertEqual(self.approve(offer["approval_challenge_id"])[0],403)
 def test_grant_approved_host_signed_source_bound_and_not_committed(self):
  ring=HostSigningKeyRing("studio-test-key",{"studio-test-key":b"X"*32},frozenset())
  studio.configure_m045_soundtrack_grant(ring,lambda pid,rid,aid,principal:
    "ARTIST_OWNED" if (pid,rid,aid,principal)==
    (self.ctx["projectId"],self.ctx["revisionId"],self.ctx["artifactId"],
     self.owner["principalId"]) else None)
  ctx={**self.ctx,"cinemaProjectId":"film-rezrxtion-001","sectionId":"intro","fps":"24/1"}
  offer=self.issue("Create music video grant",ctx)[2]
  code,_,result=self.approve(offer["approval_challenge_id"])
  self.assertEqual(code,200,result)
  self.assertFalse(result["revisionCommitted"])
  grant=result["operationResult"]
  self.assertEqual(grant["source_project_revision_id"],self.ctx["revisionId"])
  self.assertEqual(grant["accepted_audio_artifact_id"],self.ctx["artifactId"])
  self.assertEqual(grant["cinema_project_id"],"film-rezrxtion-001")
  self.assertTrue(verify_issued_grant_signature(grant,ring))
  self.assertEqual(self.selected()["manifest"]["currentRevisionId"],self.ctx["revisionId"])
  self.assertEqual(self.approve(offer["approval_challenge_id"])[0],403)

if __name__=="__main__":unittest.main()

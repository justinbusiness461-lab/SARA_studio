"""RED-first authenticated, single-use Studio Chat approval security tests."""
import concurrent.futures,hashlib,json,time,unittest
import studio_server as studio

class ApprovalHTTP(unittest.TestCase):
 def setUp(self):
  from test_platform_identity_and_catalog import PlatformHTTP
  self.fixture=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
  self.root=self.fixture.root;self.api=self.fixture.api
  self.owner=self.fixture.signup();self.cookie,_=self.fixture.login()
  self.source=self.fixture.project(self.owner["principalId"])
  self.ref={key:self.source[key] for key in ("projectId","revisionId","artifactId")}
 def issue(self,ref=None,instruction="Master this song to -14 LUFS",cookie=None):
  return self.api("/api/m045/chat",
   {"instruction":instruction,"context":self.ref if ref is None else ref},
   cookie=self.cookie if cookie is None else cookie)
 def approve(self,challenge_id,expected=None,cookie=None,extra=None):
  body={"approval_challenge_id":challenge_id,
        "expected_current_revision_id":self.ref["revisionId"] if expected is None else expected}
  if extra:body.update(extra)
  return self.api("/api/m045/chat/approve",body,cookie=self.cookie if cookie is None else cookie)
 def test_distinct_creative_instructions_bind_distinct_operation_digests(self):
  ctx={**self.ref,"selectedTrackId":"lead","selectedBars":[1]}
  a=self.issue(ref=ctx,instruction="Repaint the lead darker")[2]
  b=self.issue(ref=ctx,instruction="Repaint the lead brighter")[2]
  self.assertEqual(a["action"],"REPAINT")
  self.assertEqual(b["action"],"REPAINT")
  self.assertNotEqual(a["operation_digest"],b["operation_digest"],
    "An approval of darker music must not also approve a brighter edit")
 def test_approval_required_mints_random_server_challenge_bound_to_exact_source(self):
  status,_,data=self.issue()
  self.assertEqual(status,200,data)
  self.assertEqual(data["state"],"APPROVAL_REQUIRED")
  self.assertRegex(data["approval_challenge_id"],r"^appr-[0-9a-f]{64}$")
  self.assertEqual(data["sourceRevisionId"],self.ref["revisionId"])
  self.assertEqual(len(data["operation_digest"]),64)
  self.assertFalse(data["revisionCommitted"])
 def test_approve_master_executes_canonical_owner_and_readback_once(self):
  challenge=self.issue()[2]["approval_challenge_id"]
  code,_,result=self.approve(challenge)
  self.assertEqual(code,200,result)
  self.assertEqual(result["status"],"SUCCESS")
  self.assertTrue(result["revisionCommitted"])
  master=result["operationResult"]
  self.assertEqual(master["sourceRevisionId"],self.ref["revisionId"])
  self.assertEqual(master["rightsStatus"],"UNVERIFIED_HELD")
  actual=studio.project_audio_bytes(self.root,
    {"projectId":self.ref["projectId"],"revisionId":master["revisionId"],
     "artifactId":master["artifactId"]},principal_id=self.owner["principalId"])
  self.assertEqual(hashlib.sha256(actual).hexdigest(),master["artifactId"])
  self.assertEqual(self.approve(challenge)[0],403)
 def test_forged_and_missing_session_denied(self):
  self.assertEqual(self.approve("appr-"+"0"*64)[0],403)
  challenge=self.issue()[2]["approval_challenge_id"]
  self.assertEqual(self.api("/api/m045/chat/approve",{
   "approval_challenge_id":challenge,"expected_current_revision_id":self.ref["revisionId"]})[0],403)
  self.assertEqual(self.approve(challenge,extra={"confirmed":True})[0],400)
 def test_foreign_principal_and_different_expected_revision_denied(self):
  other=self.fixture.signup("second_user","safe strong other password!")
  cookie,_=self.fixture.login("second_user","safe strong other password!")
  challenge=self.issue()[2]["approval_challenge_id"]
  self.assertEqual(self.approve(challenge,cookie=cookie)[0],403)
  self.assertEqual(self.approve(challenge,expected="f"*64)[0],409)
 def test_expired_challenge_fail_closed(self):
  from platform_identity import PlatformStore
  challenge=self.issue()[2]["approval_challenge_id"]
  store=PlatformStore(self.root)
  with store._db() as db:
   db.execute("UPDATE chat_approvals SET expires_at=0 WHERE challenge_id=?",(challenge,))
  self.assertEqual(self.approve(challenge)[0],403)
 def test_stale_manifest_blocks_challenge_and_preserves_new_revision(self):
  challenge=self.issue()[2]["approval_challenge_id"]
  current=studio.project_operation(self.root,{"projectId":self.ref["projectId"]},
       principal_id=self.owner["principalId"])
  nextrev=studio.project_operation(self.root,{
    "projectId":self.ref["projectId"],
    "expectedCurrentRevisionId":self.ref["revisionId"],
    "songSpec":current["songSpec"]},commit=True,principal_id=self.owner["principalId"])
  latest=nextrev["revision"]["revisionId"]
  self.assertNotEqual(latest,self.ref["revisionId"])
  self.assertEqual(self.approve(challenge)[0],409)
  still=studio.project_operation(self.root,{"projectId":self.ref["projectId"]},principal_id=self.owner["principalId"])
  self.assertEqual(still["manifest"]["currentRevisionId"],latest)
 def test_approved_master_true_peak_violation_409_no_revision_claim_or_retry(self):
  from unittest.mock import patch
  challenge=self.issue()[2]["approval_challenge_id"]
  with patch("m045_wave4_service.authorized_master",
      side_effect=ValueError("INDEPENDENT_TRUE_PEAK_CEILING_FAILED")):
   status,_,result=self.approve(challenge)
  self.assertEqual(status,409,result)
  self.assertEqual(result["error"],"MASTER_TRUE_PEAK_CEILING_NOT_VERIFIED")
  self.assertEqual(self.approve(challenge)[0],403)
  self.assertEqual(studio.project_operation(self.root,{"projectId":self.ref["projectId"]},
    principal_id=self.owner["principalId"])["manifest"]["currentRevisionId"],
    self.ref["revisionId"])
 def test_concurrent_approval_has_one_winner_and_no_double_publication(self):
  challenge=self.issue()[2]["approval_challenge_id"]
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   statuses=list(pool.map(lambda _:self.approve(challenge)[0],range(2)))
  self.assertEqual(sorted(statuses),[200,403])
 def test_publication_requires_separate_host_rights_and_exact_confirmation(self):
  challenge=self.issue(instruction="Publish this song")[2]["approval_challenge_id"]
  self.assertEqual(self.approve(challenge)[0],403)
  studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:
   "ARTIST_OWNED" if (pid,rid,aid,principal)==
      (self.ref["projectId"],self.ref["revisionId"],self.ref["artifactId"],
       self.owner["principalId"]) else None)
  challenge=self.issue(instruction="Publish this song")[2]["approval_challenge_id"]
  status,_,result=self.approve(challenge)
  self.assertEqual(status,200,result)
  self.assertEqual(result["action"],"PUBLISH")
  self.assertTrue(result["operationResult"]["publicationId"])
  self.assertEqual(len(self.api("/api/explore")[2]["songs"]),1)
  self.assertEqual(self.approve(challenge)[0],403)
 def test_midi_approval_remains_p3_unpublished_and_source_intact(self):
  challenge=self.issue(instruction="Transcribe this audio to MIDI")[2]["approval_challenge_id"]
  status,_,result=self.approve(challenge)
  self.assertEqual(status,200,result)
  self.assertFalse(result["revisionCommitted"])
  self.assertEqual(result["action"],"TRANSCRIBE_MIDI")
  self.assertEqual(studio.project_operation(self.root,{"projectId":self.ref["projectId"]},
    principal_id=self.owner["principalId"])["manifest"]["currentRevisionId"],
    self.ref["revisionId"])
 def test_unsupported_approved_action_never_fabricates_committed_revision(self):
  context={**self.ref,"selectedTrackId":"lead","selectedBars":[1]}
  code,_,proposal=self.issue(ref=context,instruction="Repaint the lead darker")
  self.assertEqual(code,200,proposal)
  challenge=proposal["approval_challenge_id"]
  code,_,result=self.approve(challenge)
  self.assertIn(code,(409,503),result)
  self.assertNotEqual(result.get("revisionCommitted"),True)
  self.assertEqual(studio.project_operation(self.root,{"projectId":self.ref["projectId"]},
     principal_id=self.owner["principalId"])["manifest"]["currentRevisionId"],self.ref["revisionId"])

if __name__=="__main__":unittest.main()


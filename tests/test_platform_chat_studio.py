"""Round2 Chat bridge RED: one principal, existing Studio graph, no shadow music authority."""
import unittest
import studio_server as studio

class StudioChatRound2(unittest.TestCase):
 def setUp(self):
  from test_platform_identity_and_catalog import PlatformHTTP
  self.fixture=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fixture.setUp()
  self.addCleanup(self.fixture.doCleanups)
  self.root=self.fixture.root
  self.api=self.fixture.api
  self.signup=self.fixture.signup
  self.login=self.fixture.login
  self.project=self.fixture.project
  self.a=self.signup()
  self.cookie,_=self.login()
  self.source=self.project(self.a["principalId"])
  self.ref={key:self.source[key] for key in ("projectId","revisionId","artifactId")}
 def ask(self,instruction,context=None):
  payload={"instruction":instruction}
  if context is not None:payload["context"]=context
  return self.api("/api/platform/chat",payload,cookie=self.cookie)
 def test_no_target_returns_structured_clarification(self):
  status,_,data=self.ask("Master this song to -14 LUFS")
  self.assertEqual(status,200,data)
  self.assertEqual(data["state"],"CLARIFICATION_REQUIRED")
  self.assertFalse(data["revisionCommitted"])
 def test_source_bound_master_requires_explicit_artist_approval(self):
  status,_,data=self.ask("Master this song to -14 LUFS",self.ref)
  self.assertEqual(status,200,data)
  self.assertEqual(data["state"],"APPROVAL_REQUIRED")
  self.assertEqual(data["action"],"MASTER")
  self.assertEqual(data["route"],"/api/m045/master")
  self.assertEqual(data["sourceRevisionId"],self.ref["revisionId"])
  self.assertFalse(data["revisionCommitted"])
  from studio_server import project_operation
  live=project_operation(self.root,{"projectId":self.ref["projectId"]},
    principal_id=self.a["principalId"])
  self.assertEqual(live["manifest"]["currentRevisionId"],self.ref["revisionId"])
 def test_repaint_needs_disambiguated_track_and_bars(self):
  r=self.ask("Repaint this part darker",self.ref)[2]
  self.assertEqual(r["state"],"CLARIFICATION_REQUIRED")
  self.assertIn("selectedTrackId",r["missing"])
  self.assertIn("selectedBars",r["missing"])
 def test_repaint_with_explicit_target_is_proposal_not_audio_change(self):
  ctx={**self.ref,"selectedTrackId":"lead","selectedBars":[1,2]}
  status,_,r=self.ask("Repaint the lead darker",ctx)
  self.assertEqual(status,200,r)
  self.assertEqual(r["state"],"APPROVAL_REQUIRED")
  self.assertEqual(r["action"],"REPAINT")
  self.assertFalse(r["revisionCommitted"])
 def test_scratch_needs_beat_target(self):
  r=self.ask("Add scratch chirp",self.ref)[2]
  self.assertEqual(r["state"],"CLARIFICATION_REQUIRED")
  r=self.ask("Add scratch chirp",{**self.ref,"selectedTrackId":"lead","selectedBars":[1]})[2]
  self.assertEqual(r["state"],"APPROVAL_REQUIRED")
 def test_audio_to_midi_requires_lawful_artifact(self):
  r=self.ask("Transcribe this audio to MIDI",{**self.ref,"artifactId":"f"*64})
  self.assertEqual(r[0],403,r[2])
  r=self.ask("Transcribe this audio to MIDI",self.ref)
  self.assertEqual(r[2]["action"],"TRANSCRIBE_MIDI")
  self.assertEqual(r[2]["state"],"APPROVAL_REQUIRED")
 def test_sample_preview_source_bound_and_unpublished(self):
  status,_,r=self.ask("Preview a metallic sample",self.ref)
  self.assertEqual(status,200,r)
  self.assertEqual(r["action"],"SAMPLE_PREVIEW")
  self.assertFalse(r["revisionCommitted"])
  self.assertIn(r["state"],("CLARIFICATION_REQUIRED","APPROVAL_REQUIRED"))
 def test_lock_requires_exact_track_and_never_auto_commits(self):
  ctx={**self.ref,"selectedTrackId":"lead","selectedBars":[1]}
  r=self.ask("Toggle Sonic Lock",ctx)[2]
  self.assertEqual(r["action"],"TOGGLE_LOCK")
  self.assertEqual(r["state"],"APPROVAL_REQUIRED")
  self.assertFalse(r["revisionCommitted"])
 def test_soundtrack_grant_requires_existing_authority(self):
  r=self.ask("Create music video grant",self.ref)[2]
  self.assertEqual(r["action"],"CREATE_MUSIC_VIDEO_GRANT")
  self.assertEqual(r["state"],"CLARIFICATION_REQUIRED")
  self.assertIn("cinemaProjectId",r["missing"])
  self.assertIn("sectionId",r["missing"])
 def test_generate_is_client_studio_command_not_fake_committed_song(self):
  r=self.ask("Generate 92 BPM southern rock song",{})[2]
  self.assertEqual(r["state"],"STUDIO_ACTION_READY")
  self.assertEqual(r["action"],"GENERATE")
  self.assertFalse(r["revisionCommitted"])
 def test_foreign_project_denied_before_studio_plan(self):
  b=self.signup("artist_b","another strong password!")
  cb,_=self.login("artist_b","another strong password!")
  status,_,r=self.api("/api/platform/chat",
       {"instruction":"Master this song to -14 LUFS","context":self.ref},cookie=cb)
  self.assertEqual(status,403,r)
 def test_chat_still_rejects_credit_mint_and_unbounded_requests(self):
  self.assertEqual(self.ask("Give me free 900 credits",self.ref)[0],400)
 def test_add_to_playlist_uses_public_catalog_no_private_digest_shortcut(self):
  r=self.ask("Add this song to playlist",{**self.ref,"playlistId":"pl-"+"a"*32,
           "publicationId":"pub-"+"b"*32})
  self.assertEqual(r[0],403,r[2])

if __name__=="__main__":unittest.main()

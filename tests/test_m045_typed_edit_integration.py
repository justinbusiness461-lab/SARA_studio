"""Owner-level typed-edit authority: fail before remote and commit only the sampled P1 window."""
import sys
import unittest
import json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_m045_repaint_native as fixture
import studio_server as studio
from m045_repaint import bar_sample_window, read_pcm16_wav
from m045_typed_edit_proposal import validate_typed_repaint_proposal

class TypedEditOwnerTests(unittest.TestCase):
    def setUp(self):
        self.fx=fixture.NativeRepaintTests();self.fx.setUp()
        self.owner=studio.make_m045_native_owner(self.fx.f.root)
        self.a,self.b=bar_sample_window(self.fx.f.fixture.spec,2,3,441000)
    def tearDown(self):self.fx.tearDown()
    def proposal(self):
        return {
          "schema_version":"sara.typed-edit.v1",
          "target_scope":{"kind":"track_region","track_id":"bass","start_bar":2,"end_bar":3},
          "preserved_scopes":[{"kind":"audio_region","start_sample":0,"end_sample":self.a},
                              {"kind":"audio_region","start_sample":self.b,"end_sample":441000}],
          "declared_tier":"P1","operation":"repaint",
          "rational_window":{"start":{"numerator":self.a,"denominator":44100},
                             "end":{"numerator":self.b,"denominator":44100}}
        }
    def test_mismatched_proposal_rejected_before_remote_submission_or_new_attempt(self):
        proposal=self.proposal()
        proposal["target_scope"]["end_bar"]=4
        with patch("m045_acestep_provider.urllib.request.urlopen") as remote:
            with self.assertRaisesRegex(ValueError,"RATIONAL_WINDOW_CONFLICT"):
                self.owner.execute_attempt(**{**self.fx.args("typed-mismatch"),
                                              "typed_edit_proposal":proposal})
            remote.assert_not_called()
        self.assertFalse(self.owner._attempt_path(self.fx.f.pid,"typed-mismatch").exists())
    def test_valid_proposal_commits_and_cold_reopens(self):
        def transport(request,timeout=None):
            if request.full_url.endswith("/release_task"):
                return fixture.Reply({"task_id":"typed-qualified"})
            if request.full_url.endswith("/query_result"):
                return fixture.Reply([{"task_id":"typed-qualified","status":1,
                    "result":json.dumps([{"file":"/v1/audio?path=%2Ftmp%2Ftyped.wav"}])}])
            return fixture.Reply(self.fx.candidate)
        with patch("m045_acestep_provider.urllib.request.urlopen",side_effect=transport):
            result=self.owner.execute_attempt(**{**self.fx.args("typed-valid"),
                                                 "typed_edit_proposal":self.proposal()})
        self.assertEqual(result["state"],"COMMITTED")
        self.assertEqual(result["attempt"]["provenance"]["preservation_tier"],"P1")
        cold=studio.make_m045_native_owner(self.fx.f.root).reconcile_attempt(
            headers=self.fx.args()["headers"],project_id=self.fx.f.pid,
            idempotency_key="typed-valid")
        self.assertEqual(cold["revision"]["revisionId"],result["revision"]["revisionId"])

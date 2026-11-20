import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from m045_typed_edit_proposal import validate_typed_repaint_proposal
from m045_repaint import bar_sample_window
import test_m045_native_attempt as fixtures
import studio_server as studio

class TypedEditProposalTests(unittest.TestCase):
    def setUp(self):
        self.fx=fixtures.NativeAttemptTests();self.fx.setUp()
        self.spec=self.fx.fixture.spec
        self.frames=44100*10
        self.start,self.end=bar_sample_window(self.spec,2,3,self.frames)
    def tearDown(self): self.fx.tearDown()
    def proposal(self,**changes):
        start,end=self.start,self.end
        p={
            "schema_version":"sara.typed-edit.v1",
            "target_scope":{"kind":"track_region","track_id":"bass","start_bar":2,"end_bar":3},
            "preserved_scopes":[
                {"kind":"audio_region","start_sample":0,"end_sample":start},
                {"kind":"audio_region","start_sample":end,"end_sample":self.frames}],
            "declared_tier":"P1",
            "operation":"repaint",
            "rational_window":{"start":{"numerator":start,"denominator":44100},
                               "end":{"numerator":end,"denominator":44100}}
        }
        p.update(changes)
        return p
    def test_valid_repaint_exact_complement_passes_without_promising_track_isolation(self):
        result=validate_typed_repaint_proposal(self.proposal(),self.spec,
              self.frames,(self.start,self.end),"bass")
        self.assertEqual(result["declared_tier"],"P1")
        self.assertEqual(result["validated_sample_window"],[self.start,self.end])
    def test_wrong_rational_time_and_client_floats_rejected(self):
        p=self.proposal()
        p["rational_window"]["start"]["numerator"]+=1
        with self.assertRaisesRegex(ValueError,"RATIONAL_WINDOW"):
            validate_typed_repaint_proposal(p,self.spec,self.frames,(self.start,self.end),"bass")
        p=self.proposal()
        p["rational_window"]["end"]["numerator"]=float(self.end)
        with self.assertRaises(ValueError):
            validate_typed_repaint_proposal(p,self.spec,self.frames,(self.start,self.end),"bass")
    def test_protected_track_and_locked_section_reject(self):
        spec={**self.spec,"tracks":[{**t,"sonic_lock":True} if t["track_id"]=="bass" else t for t in self.spec["tracks"]]}
        with self.assertRaisesRegex(ValueError,"SONIC_LOCK"):
            validate_typed_repaint_proposal(self.proposal(),spec,self.frames,(self.start,self.end),"bass")
        spec={**self.spec,"structure":{"sections":[{**s,"sonic_lock":True} for s in self.spec["structure"]["sections"]]}}
        with self.assertRaisesRegex(ValueError,"SONIC_LOCK"):
            validate_typed_repaint_proposal(self.proposal(),spec,self.frames,(self.start,self.end),"bass")
    def test_false_p0_and_track_level_preservation_rejected(self):
        with self.assertRaisesRegex(ValueError,"TIER_UNQUALIFIED"):
            validate_typed_repaint_proposal(self.proposal(declared_tier="P0"),self.spec,self.frames,(self.start,self.end),"bass")
        p=self.proposal()
        p["preserved_scopes"]=[{"kind":"track","track_id":"drums"}]
        with self.assertRaisesRegex(ValueError,"PRESERVATION_SCOPE"):
            validate_typed_repaint_proposal(p,self.spec,self.frames,(self.start,self.end),"bass")
    def test_malformed_extra_key_and_incomplete_complement_rejected(self):
        with self.assertRaises(ValueError):
            validate_typed_repaint_proposal(self.proposal(magic=True),self.spec,self.frames,(self.start,self.end),"bass")
        p=self.proposal();p["preserved_scopes"]=p["preserved_scopes"][:1]
        with self.assertRaisesRegex(ValueError,"PRESERVATION_SCOPE"):
            validate_typed_repaint_proposal(p,self.spec,self.frames,(self.start,self.end),"bass")

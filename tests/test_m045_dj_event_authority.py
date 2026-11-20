"""Studio-owned validation of symbolic Scratch Surgeon event identity."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import studio_server as studio
import test_m045_native_attempt as fixture

class ScratchAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fx=fixture.NativeAttemptTests();self.fx.setUp()
    def tearDown(self):self.fx.tearDown()
    def marker(self,spec,sec=None):
        section=sec or spec["structure"]["sections"][0]
        tick=section["start_tick"]+480
        sample=(tick*60*44100*2 + 94*960)//(2*94*960)
        # actual fixture BPM read from saved SongSpec, not a guessed constant.
        bpm=spec["timebase"]["initial_bpm"]
        sample=(2*tick*60*44100+bpm*960)//(2*bpm*960)
        return {"type":"DJ_SCRATCH_MARKER","event_id":f"dj:{section['id']}:{tick}:A",
                "tick":tick,"duration_ticks":480,"deck":"A","technique":"chirp",
                "sample_index":sample,"audio_status":"UNRENDERED_SOURCE_ASSET_REQUIRED"}
    def spec(self):
        from copy import deepcopy
        s=deepcopy(self.fx.fixture.spec)
        s["tracks"].append({"track_id":"dj_scratch","name":"Scratch Surgeon","type":"DJ",
            "muted":False,"sonic_lock":False,"volume_db":0,"pan":0,
            "events":[self.marker(s)]})
        return s
    def save(self,s,base=None):
        return studio.project_operation(self.fx.root,{"projectId":self.fx.pid,
            "expectedCurrentRevisionId":base or self.fx.r1["revision"]["revisionId"],
            "songSpec":s,"sourceAssetDigests":[],"outputArtifactIds":[]},commit=True)
    def test_valid_marker_commits_with_exact_sample_index(self):
        result=self.save(self.spec())
        self.assertEqual(result["songSpec"]["tracks"][-1]["events"][0]["sample_index"],
                         self.marker(self.spec())["sample_index"])
    def test_forged_sample_clock_or_technique_rejected(self):
        for field,value in [("sample_index",1),("technique","unknown"),("event_id","fake")]:
            s=self.spec();s["tracks"][-1]["events"][0][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.save(s)
    def test_locked_dj_track_cannot_be_bypassed_by_direct_project_commit(self):
        original=self.spec(); original["tracks"][-1]["sonic_lock"]=True
        committed=self.save(original)
        from copy import deepcopy
        edited=deepcopy(original);edited["tracks"][-1]["sonic_lock"]=False
        edited["tracks"][-1]["events"]=[]
        with self.assertRaises(studio.ProjectConflict):
            self.save(edited,committed["revision"]["revisionId"])
    def test_locked_section_cannot_accept_new_dj_marker_via_direct_commit(self):
        spec=self.spec();spec["tracks"][-1]["events"]=[]
        spec["structure"]["sections"][0]["sonic_lock"]=True
        committed=self.save(spec)
        from copy import deepcopy
        edited=deepcopy(spec);edited["tracks"][-1]["events"].append(self.marker(spec))
        with self.assertRaises(studio.ProjectConflict):
            self.save(edited,committed["revision"]["revisionId"])

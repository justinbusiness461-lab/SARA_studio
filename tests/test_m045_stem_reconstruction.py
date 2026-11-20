import hashlib,struct,sys,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from m045_stem_reconstruction import export_two_tier_stems, reconstruct_master

class StemReconstructionTests(unittest.TestCase):
 def setUp(self):
  self.length=500
  self.stems=[
   b"".join(struct.pack("<dd",0.18 if i%3==0 else 0.02,0.07) for i in range(self.length)),
   b"".join(struct.pack("<dd",-0.05,0.04 if i%5==0 else -0.01) for i in range(self.length))]
  self.recipe={"schema_version":"sara.mix.recipe.v1","source_project_revision_id":"b"*64,
   "production_timeline_digest":"c"*64,
   "stem_artifact_ids":[hashlib.sha256(x).hexdigest() for x in self.stems],
   "bus_waveshaper":"tanh","fade_ms":2.0,"target_peak":0.85,
   "sample_rate":44100,"channels":2,"sample_count":self.length,
   "pcm_quantizer":"signed16_round_nearest_ties_even","encoder":"canonical_pcm16_wav_44"}
 def test_exact_master_reconstruction_and_creative_truth(self):
  export=export_two_tier_stems(self.stems,self.recipe)
  self.assertEqual(export["production_master"]["sha256"],hashlib.sha256(export["production_master"]["wav"]).hexdigest())
  self.assertEqual(export["production_master"]["wav"],reconstruct_master(self.stems,export["mix_recipe"]))
  self.assertFalse(export["creative_stems"]["exact_reconstruction_certified"])
  self.assertTrue(export["reconstruction_stems"]["exact_reconstruction_certified"])
  self.assertEqual(export["mix_recipe"]["stem_artifact_ids"],self.recipe["stem_artifact_ids"])
 def test_fresh_process_regenerates_exact_same_whole_wav_sha256(self):
  import base64,subprocess,tempfile
  fixture=export_two_tier_stems(self.stems,self.recipe)
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/"fixture.json"
   path.write_text(json.dumps({"stems":[base64.b64encode(x).decode() for x in self.stems],
    "recipe":fixture["mix_recipe"]},sort_keys=True))
   script="""import base64,hashlib,json,sys
from m045_stem_reconstruction import reconstruct_master
payload=json.load(open(sys.argv[1]))
stems=[base64.b64decode(x,validate=True) for x in payload['stems']]
print(hashlib.sha256(reconstruct_master(stems,payload['recipe'])).hexdigest())
"""
   result=subprocess.run([sys.executable,"-c",script,str(path)],env={
    "PYTHONPATH":str(Path(__file__).resolve().parents[1]/"tools")},
    text=True,capture_output=True,check=True,timeout=10)
   self.assertEqual(result.stdout.strip(),fixture["production_master"]["sha256"])
 def test_order_tamper_and_wrong_revision_are_rejected(self):
  export=export_two_tier_stems(self.stems,self.recipe)
  altered={**self.recipe,"stem_artifact_ids":list(reversed(self.recipe["stem_artifact_ids"]))}
  with self.assertRaises(ValueError):
   reconstruct_master(self.stems,altered)
  altered={**self.recipe,"source_project_revision_id":"not a revision"}
  with self.assertRaises(ValueError):
   reconstruct_master(self.stems,altered)
 def test_float64_nans_and_stem_misalignment_fail_closed(self):
  for bad in [struct.pack("<dd",float("nan"),0.0)+self.stems[0][16:],self.stems[0][:-8]]:
   with self.assertRaises(ValueError):
    reconstruct_master([bad,self.stems[1]],self.recipe)
